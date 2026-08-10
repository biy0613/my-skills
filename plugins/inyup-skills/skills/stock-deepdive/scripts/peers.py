#!/usr/bin/env python3
"""피어그룹 밸류에이션 비교표.

7문 1번(컨센서스와 나의 변별점)을 쓰기 전에 항상 먼저 돌린다.
"시장이 이 종목에 매기는 배수가 동종 대비 어디인가"를 모르면 변별점을 쓸 수 없다.

  python peers.py --target DUOL --peers COUR,SPOT,MTCH,PINS
  python peers.py --target 192820 --peers 161890,251970,352480     # 국장(6자리는 .KS/.KQ 자동 탐색)

배수만으로 싸다/비싸다를 말하지 않는다 — 성장률·마진을 같은 표에 놓고 봐야 의미가 생긴다.
"""

import argparse
import re
import sys

import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIELDS = [
    ("shortName", "이름"),
    ("currentPrice", "주가"),
    ("marketCap", "시총"),
    ("trailingPE", "PER(T)"),
    ("forwardPE", "PER(F)"),
    ("trailingPegRatio", "PEG"),
    ("priceToSalesTrailing12Months", "P/S"),
    ("enterpriseToEbitda", "EV/EBITDA"),
    ("revenueGrowth", "매출YoY"),
    ("grossMargins", "GM"),
    ("operatingMargins", "OPM"),
    ("52WeekChange", "52주"),
]

PCT = ("매출YoY", "GM", "OPM", "52주")
# 적자 기업의 음수 배수는 "싸다"가 아니라 무의미다. 중앙값에 섞으면 조용히 왜곡된다.
POSITIVE_ONLY = ("PER(T)", "PER(F)", "PEG", "EV/EBITDA")


def resolve(raw):
    """6자리 숫자면 .KS → .KQ 순으로 탐색. 그 외는 그대로 조회.

    함정: 틀린 접미사(코스닥 종목에 .KS)를 줘도 yfinance 는 빈 응답이 아니라
    검색 잔여물이 든 dict 를 돌려준다 — shortName 에 "251970.KS,0P0001HYSO,8"
    같은 문자열이 들어온다. shortName 존재 여부로 성공을 판정하면 코스닥 종목이
    조용히 누락된다. **marketCap 이 있는지로만 판정한다.**
    """
    t = raw.strip().upper()
    candidates = [t + s for s in (".KS", ".KQ")] if re.fullmatch(r"\d{6}", t) else [t]
    first_err = None
    for cand in candidates:
        try:
            info = yf.Ticker(cand).info
        except Exception as e:  # noqa: BLE001
            first_err = first_err or type(e).__name__
            continue
        if info.get("marketCap"):
            return cand, info
    return candidates[0], {"shortName": f"조회실패({first_err or '데이터없음'})"}


def fetch(raw):
    ticker, info = resolve(raw)
    # 시총·주가는 '거래 통화'(currency)로, 매출·이익은 '재무제표 통화'(financialCurrency)로 온다.
    # On Holding 처럼 둘이 다른 종목이 있어 구분해 둔다 — 섞으면 멀쩡한 비교에 헛경고가 뜬다.
    row = {
        "티커": ticker,
        "_통화": info.get("currency"),
        "_재무통화": info.get("financialCurrency") or info.get("currency"),
    }
    for key, label in FIELDS:
        v = info.get(key)
        row[label] = v * 100 if (v is not None and label in PCT) else v
    return row


def fmt(label, v, unit=1e9):
    if v is None:
        return "n/a"
    if label == "이름":
        return str(v)[:22]
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)[:12]
    if label in PCT:
        return f"{v:+.1f}%"
    if label == "시총":
        return f"{v / unit:,.1f}"
    return f"{v:,.2f}"


def median(vals, positive_only=False):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if positive_only:
        vals = [v for v in vals if v > 0]
    vals = sorted(vals)
    if not vals:
        return None, 0
    n = len(vals)
    return (vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2), n


def main():
    ap = argparse.ArgumentParser(description="피어그룹 밸류에이션 비교")
    ap.add_argument("--target", required=True, help="기준 종목 티커(미장 심볼 또는 국장 6자리)")
    ap.add_argument("--peers", required=True, help="쉼표로 구분한 피어 티커")
    ap.add_argument("--csv", help="CSV로도 저장할 경로")
    args = ap.parse_args()

    raws = [args.target] + [p for p in args.peers.split(",") if p.strip()]
    rows = [fetch(r) for r in raws]

    currencies = {r["_통화"] for r in rows if r["_통화"]}
    krw = "KRW" in currencies
    unit, unit_label = (1e12, "조KRW") if krw else (1e9, "십억")
    if len(currencies) > 1:
        print(f"⚠ 거래 통화가 섞여 있다({', '.join(sorted(currencies))}) — 시총 열은 비교하지 말 것.\n")
    fx_mismatch = [r["티커"] for r in rows if r["_통화"] and r["_재무통화"] != r["_통화"]]
    if fx_mismatch:
        print(f"※ 재무제표 통화가 거래 통화와 다른 종목: {', '.join(fx_mismatch)}")
        print("   배수(PER·EV/EBITDA·마진)는 무관하지만, P/S 는 환산 여부를 확인하고 인용할 것.\n")

    labels = ["티커"] + [lab for _, lab in FIELDS]
    widths = {
        lab: max(len(lab), max((len(fmt(lab, r.get(lab), unit)) for r in rows), default=0))
        for lab in labels
    }
    widths["티커"] = max(widths["티커"], max(len(r["티커"]) for r in rows))

    print(f"피어 비교 · 시총 단위 {unit_label}")
    print(" | ".join(lab.ljust(widths[lab]) for lab in labels))
    print("-+-".join("-" * widths[lab] for lab in labels))
    for i, r in enumerate(rows):
        cells = [r["티커"].ljust(widths["티커"])]
        cells += [fmt(lab, r.get(lab), unit).rjust(widths[lab]) for lab in labels[1:]]
        print(" | ".join(cells) + ("   ← 기준" if i == 0 else ""))

    print()
    peers = rows[1:]
    for lab in ("PER(T)", "PER(F)", "P/S", "EV/EBITDA", "매출YoY", "GM", "OPM"):
        pos = lab in POSITIVE_ONLY
        m, n = median((r.get(lab) for r in peers), positive_only=pos)
        t = rows[0].get(lab)
        line = f"  피어 중앙값 {lab:<10} {fmt(lab, m, unit):>9}  (n={n}/{len(peers)})   기준 {fmt(lab, t, unit):>9}"
        if isinstance(m, (int, float)) and isinstance(t, (int, float)) and m and t > 0:
            line += f"   ({t / m:.2f}배)" if lab.startswith(("PER", "P/S", "EV")) else ""
        print(line)

    print("\n  ※ PER·PEG·EV/EBITDA 중앙값은 양수만으로 계산한다 — 적자 기업의 음수 배수는 무의미하다.")
    print("     n은 중앙값에 실제로 들어간 피어 수다. n이 2 이하면 중앙값을 인용하지 말 것.")

    if krw:
        print("\n  ※※ 국장 경고 — 이 소스는 국내 종목에 대해 다음을 주지 않는다:")
        print("      · trailingPE / trailingEps / forwardEps 는 항상 n/a 로 온다.")
        print("        **흑자 기업이 적자로 보이는 것이 아니다. 데이터 부재다.** 이 둘을 혼동하지 말 것.")
        print("      · GM·OPM 은 값이 오지만 국내 공시 기준과 다를 수 있다 — 교차검증 없이 인용 금지.")
        print("      → 국장 PER(T)와 마진은 stock-finder-foreign 스킬의 검증된 경로")
        print("        (네이버 integration 의 cnsPer, FnGuide wcomp)로 따로 채운다.")

    print("\n  배수만으로 판단하지 말 것. 내부 분석용 · 투자 권유 아님.")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=labels, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  저장: {args.csv}")


if __name__ == "__main__":
    sys.exit(main())
