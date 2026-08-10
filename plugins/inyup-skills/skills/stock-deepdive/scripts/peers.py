#!/usr/bin/env python3
"""피어그룹 밸류에이션 비교표 (미장).

1번 문항에서 "시장이 이 종목에 매기는 배수가 동종 대비 어디인가"를 확인할 때 쓴다.
배수만으로 싸다/비싸다를 말하지 않는다 — 성장률·마진을 같은 표에 놓고 봐야 의미가 생긴다.

  python peers.py --target DUOL --peers COUR,UDMY,SPOT,MTCH,PINS
  python peers.py --target LULU --peers NKE,ONON,DECK,ANF,GAP --csv out.csv

주의: trailingPE는 일회성 손익(세금 환입·자산 매각)에 오염되기 쉽다. forwardPE와 반드시 같이 본다.
      적자 기업은 PER이 None으로 나오며, 이때 P/S와 EV/EBITDA로 대신 본다.
"""

import argparse
import sys

import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIELDS = [
    ("shortName", "이름"),
    ("currentPrice", "주가"),
    ("marketCap", "시총$B"),
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


def fetch(ticker):
    try:
        info = yf.Ticker(ticker).info
    except Exception as e:  # noqa: BLE001
        return {"티커": ticker, "이름": f"조회실패({type(e).__name__})"}
    row = {"티커": ticker}
    for key, label in FIELDS:
        v = info.get(key)
        if v is None:
            row[label] = None
        elif key == "marketCap":
            row[label] = v / 1e9
        elif key in ("revenueGrowth", "grossMargins", "operatingMargins", "52WeekChange"):
            row[label] = v * 100
        else:
            row[label] = v
    return row


def fmt(label, v):
    if v is None:
        return "n/a"
    if label == "이름":
        return str(v)[:22]
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)[:12]
    if label in ("매출YoY", "GM", "OPM", "52주"):
        return f"{v:+.1f}%"
    if label == "시총$B":
        return f"{v:,.1f}"
    return f"{v:,.2f}"


# 적자 기업의 음수 배수는 "싸다"가 아니라 무의미다. 중앙값에 섞으면 조용히 왜곡된다.
POSITIVE_ONLY = ("PER(T)", "PER(F)", "PEG", "EV/EBITDA")


def median(vals, positive_only=False):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if positive_only:
        vals = [v for v in vals if v > 0]
    vals = sorted(vals)
    if not vals:
        return None, 0
    n = len(vals)
    m = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return m, n


def main():
    ap = argparse.ArgumentParser(description="피어그룹 밸류에이션 비교")
    ap.add_argument("--target", required=True, help="기준 종목 티커")
    ap.add_argument("--peers", required=True, help="쉼표로 구분한 피어 티커")
    ap.add_argument("--csv", help="CSV로도 저장할 경로")
    args = ap.parse_args()

    tickers = [args.target.upper()] + [t.strip().upper() for t in args.peers.split(",") if t.strip()]
    rows = [fetch(t) for t in tickers]

    labels = ["티커"] + [lab for _, lab in FIELDS]
    widths = {
        lab: max(len(lab), max((len(fmt(lab, r.get(lab))) for r in rows), default=0))
        for lab in labels
    }
    widths["티커"] = max(widths["티커"], max(len(r["티커"]) for r in rows))

    print(" | ".join(lab.ljust(widths[lab]) for lab in labels))
    print("-+-".join("-" * widths[lab] for lab in labels))
    for i, r in enumerate(rows):
        cells = [r["티커"].ljust(widths["티커"])]
        cells += [fmt(lab, r.get(lab)).rjust(widths[lab]) for lab in labels[1:]]
        print(" | ".join(cells) + ("   ← 기준" if i == 0 else ""))

    print()
    peers = rows[1:]
    for lab in ("PER(T)", "PER(F)", "P/S", "EV/EBITDA", "매출YoY", "GM", "OPM"):
        pos = lab in POSITIVE_ONLY
        m, n = median((r.get(lab) for r in peers), positive_only=pos)
        t = rows[0].get(lab)
        line = f"  피어 중앙값 {lab:<10} {fmt(lab, m):>10}  (n={n}/{len(peers)})   기준 {fmt(lab, t):>10}"
        if isinstance(m, (int, float)) and isinstance(t, (int, float)) and m and t > 0:
            line += f"   ({t / m:.2f}배)" if lab.startswith(("PER", "P/S", "EV")) else ""
        print(line)

    print("\n  ※ PER·PEG·EV/EBITDA 중앙값은 양수 값만으로 계산한다 — 적자 기업의 음수 배수는 무의미하다.")
    print("     n은 중앙값 계산에 실제로 들어간 피어 수다. n이 작으면 중앙값을 믿지 말 것.")
    n_na = sum(1 for r in peers if not isinstance(r.get("PER(T)"), (int, float)) or (r.get("PER(T)") or 0) <= 0)
    if n_na:
        print(f"     피어 {len(peers)}곳 중 {n_na}곳은 흑자 기준 trailing PER이 없다 — 흑자 기업 쪽으로 치우친 표본이다.")
    print("\n  배수만으로 판단하지 말 것. 내부 분석용 · 투자 권유 아님.")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=labels)
            w.writeheader()
            w.writerows(rows)
        print(f"  저장: {args.csv}")


if __name__ == "__main__":
    sys.exit(main())
