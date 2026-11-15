# -*- coding: utf-8 -*-
"""
가격대 점검 (홍진채 방식) — 보유·주문고려 종목이 '매우 싸다 / 싸다 / 보통 / 비싸다' 중 어디인가.

출처: 교양이를 부탁해 2026-11-13 홍진채 대표 (youtube LFIQlH6vlUc 03:17~08:23).
  "PER 4배라 싸다"는 분모(이익)가 이례적으로 높아 왜곡된다. 대신
  ① 이례적 이익 구간(3년)의 이익을 더하고 ② 그 뒤 정상 이익 × 평균 배수를 더한 뒤 ③ 3년치 할인한다.

계산식 (주당):
  적정가 = (E1 + E2 + E3 + 정상이익 × 배수) / 1.1^3        E1=내년, E2=내후년, E3=E2(그대로)
  비율   = 적정가 / 종가
  분류   = ≥1.5 매우 싸다 · 1.15~1.5 싸다 · 0.85~1.15 보통 · <0.85 비싸다
  (영상의 코스피 계산 5,500조/4,500조=1.22 가 '싸다', 3,000조=1.83 '매우 싸다', 8,000~9,000조=0.6~0.7 '비싸다' 가 되게 맞춘 눈금)

가정 (이 파일 위쪽 상수로 고친다):
  메모리        정상이익 = E1 × 12.5% (영상: 전자·닉스 800조 → 100조), 배수 10
  AI 투자 연동   정상이익 = E2 × 50%, 배수 = 기본(한국·중국 10, 미국 20)   ← 성장률PER지도 tags.json '경기순환'
  그 외         정상이익 = E2, 배수 = 기본 × (E2/E1 증가율 >25% 1.5 · 10~25% 1.25 · 그 미만 1.0)  ← 영상에 없는 가산
  범위(경기순환·메모리): 호황 지속 = 정상이익 100% / 조기 종료 = 3년차도 정상이익

입력 (읽기만 한다 — 엑셀·프로젝트 파일에 쓰지 않는다):
  종목       포트폴리오기록.xlsx [보유종목] 상태=보유 + 주문고려.xlsx [요약] (보유로 이관·관심 해제 제외)
  이익 전망   종목분석툴/_도구/성장률PER지도/history/<최신>.csv (달력연도 EPS, 미장은 Yahoo 수준 보정 완료)
             거기 없는 미장 종목은 Nasdaq 연간 전망 + Yahoo 로 직접 받는다. 국장은 per_map.py 를 먼저 돌린다.
  종가       국장 = 다음 금융 정규장 tradePrice · 미장 = yfinance 직전 거래일 종가

사용:
  python pricezone.py                 # 전체
  python pricezone.py --extra MU,TSM  # 목록 밖 종목 추가 (미장 티커 또는 국장 6자리)
  python pricezone.py --ref           # 삼성전자·SK하이닉스를 참고로 함께
"""
import sys, os, csv, glob, json, argparse, datetime as dt

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DEFAULT = r"C:\Users\biy06\OneDrive\바탕 화면\클로드실습\주식"
DISC = 1.1 ** 3
MEM = {"005930", "000660", "005935", "MU"}
MEM_NORMAL = 0.125          # 정상 이익 = 내년 이익의 12.5%
CYC_NORMAL = 0.5            # AI 투자 연동: 정상 이익 = 내후년 이익의 50%
CYC_EXTRA = {"DELL", "SMCI", "ANET", "VRT", "CRWV", "TSM"}   # tags.json '경기순환'에 없지만 AI 투자에 연동된 곳
CHINA = {"BIDU", "BABA", "PDD", "JD", "TCEHY", "NTES"}
BASE_KR, BASE_US = 10, 20
TIERS = [(0.25, 1.5), (0.10, 1.25)]     # (증가율 초과, 배수 가산)
CUTS = [(1.5, "매우 싸다"), (1.15, "싸다"), (0.85, "보통"), (-1e9, "비싸다")]
STALE_DAYS = 7
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def fl(x):
    try:
        v = float(x)
        return v if v == v else None
    except Exception:
        return None


def universe(root, extra, ref):
    import openpyxl
    sys.path.insert(0, root)
    import _경로 as P
    out, skipped = {}, []

    def add(name, code, mkt, grp):
        mkt = (mkt or "").upper()
        if mkt in ("KOSPI", "KOSDAQ"):
            key = str(code).strip().zfill(6)
        elif mkt in ("NASDAQ", "NYSE"):
            key = str(code).strip().upper()
        else:
            skipped.append(f"{name}(시장 {mkt or '-'})"); return
        out.setdefault(key, dict(key=key, name=str(name), grp=grp))

    rows = list(openpyxl.load_workbook(P.PORTFOLIO_XLSX, read_only=True, data_only=True)["보유종목"].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and "상태" in r and "티커" in r)
    h = {v: i for i, v in enumerate(rows[hi]) if v}
    for r in rows[hi + 1:]:
        if r[h["상태"]] == "보유":
            add(r[h["종목명"]], r[h["티커"]], r[h["시장"]], "보유")
    rows = list(openpyxl.load_workbook(P.ORDER_XLSX, read_only=True, data_only=True)["요약"].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and "종목명" in r and "판정" in r)
    h = {v: i for i, v in enumerate(rows[hi]) if v}
    for r in rows[hi + 1:]:
        if not r[h["종목명"]] or r[h["판정"]] in ("보유로 이관", "관심 해제"):
            continue
        add(r[h["종목명"]], r[h["코드"]], r[h["시장"]], "주문")
    for k in extra:
        k = k.strip().upper()
        if k:
            out.setdefault(k, dict(key=k, name=k, grp="추가"))
    if ref:
        for k, n in (("000660", "SK하이닉스"), ("005930", "삼성전자")):
            out.setdefault(k, dict(key=k, name=n, grp="참고"))
    return out, skipped, P


def load_consensus(P):
    d = os.path.join(P.ANALYSIS_DIR, "_도구", "성장률PER지도")
    files = sorted(f for f in glob.glob(os.path.join(d, "history", "2*.csv")))
    if not files:
        return {}, None, set(), None
    f = files[-1]
    stamp = os.path.basename(f)[:8]
    rows = {r["key"]: r for r in csv.DictReader(open(f, encoding="utf-8-sig"))}
    cyc = set()
    try:
        cyc = set(json.load(open(os.path.join(d, "tags.json"), encoding="utf-8"))["경기순환"]["목록"])
    except Exception:
        pass
    # 그 CSV 의 eps_a·eps_b 가 어느 해인지: per_map 의 T = (실행일 + 18개월)의 연도, eps_a = T-1, eps_b = T
    run = dt.datetime.strptime(stamp, "%Y%m%d")
    T = run.year + (run.month - 1 + 18) // 12
    return rows, stamp, cyc, T


def us_direct(t, y1):
    """성장률PER지도 기록에 없는 미장 종목 — Nasdaq 연간 전망을 Yahoo 수준으로 맞춘다. → (E0, E1, E2, 메모)"""
    import requests
    nq, note = {}, []
    try:
        j = requests.get(f"https://api.nasdaq.com/api/analyst/{t}/earnings-forecast",
                         headers={**UA, "Accept": "application/json"}, timeout=20).json()
        for x in j["data"]["yearlyForecast"]["rows"]:
            nq[dt.datetime.strptime(x["fiscalEnd"], "%b %Y").year] = fl(x["consensusEPSForecast"])
    except Exception as e:
        return None, None, None, f"Nasdaq 전망 실패({str(e)[:40]})"
    yh = {}
    try:
        import yfinance as yf
        ee = yf.Ticker(t).earnings_estimate
        for k in ("0y", "+1y"):
            yh[k] = fl(ee.loc[k, "avg"])
    except Exception:
        note.append("Yahoo 없음")
    e0, e1, e2 = nq.get(y1 - 1), nq.get(y1), nq.get(y1 + 1)
    if yh.get("+1y") and e1 and e1 > 0:
        r = yh["+1y"] / e1
        e0 = yh.get("0y") or e0
        e1 = yh["+1y"]
        e2 = e2 * r if e2 else None
        if abs(r - 1) > 0.1:
            note.append(f"Yahoo 수준 보정 ×{r:.2f}")
    note.append("직접 조회(결산월 미보정)")
    return e0, e1, e2, " · ".join(note)


def kr_close(code):
    import requests
    r = requests.get(f"https://finance.daum.net/api/quote/A{code}/days?symbolCode=A{code}&page=1&perPage=3&pagination=true",
                     headers={**UA, "Referer": f"https://finance.daum.net/quotes/A{code}"}, timeout=15)
    d = r.json()["data"][0]
    return float(d["tradePrice"]), d["date"][:10]


def us_closes(tickers):
    if not tickers:
        return {}
    import yfinance as yf, pandas as pd
    df = yf.download(tickers, period="10d", interval="1d", auto_adjust=False, progress=False, threads=True)["Close"]
    et = pd.Timestamp.now(tz="America/New_York")
    out = {}
    for t in tickers:
        try:
            s = (df[t] if len(tickers) > 1 else df.squeeze()).dropna()
            i = -1
            if s.index[-1].strftime("%Y-%m-%d") == et.strftime("%Y-%m-%d") and et.hour * 60 + et.minute < 16 * 60 + 15 and len(s) > 1:
                i = -2                      # 미국 장중 값은 종가가 아니다
            out[t] = (float(s.iloc[i]), s.index[i].strftime("%Y-%m-%d"))
        except Exception:
            pass
    return out


def cls(x):
    return next(n for c, n in CUTS if x >= c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT_DEFAULT)
    ap.add_argument("--extra", default="")
    ap.add_argument("--ref", action="store_true")
    a = ap.parse_args()

    uni, skipped, P = universe(a.root, a.extra.split(","), a.ref)
    cons, stamp, cyc, T = load_consensus(P)
    if T is None:
        T = dt.date.today().year + (dt.date.today().month - 1 + 18) // 12
    y1 = T - 1
    warn = []
    if stamp is None:
        warn.append("성장률PER지도 기록이 없습니다 — `python 종목분석툴/_도구/성장률PER지도/per_map.py` 를 먼저 돌리세요.")
    else:
        age = (dt.date.today() - dt.datetime.strptime(stamp, "%Y%m%d").date()).days
        if age > STALE_DAYS:
            warn.append(f"이익 전망이 {age}일 전({stamp}) 것입니다 — per_map.py 를 다시 돌린 뒤 재실행하세요.")

    us = [k for k in uni if not k.isdigit()]
    uspx = us_closes(us)
    res, na = [], []
    for k, u in uni.items():
        try:
            p, pd_ = kr_close(k) if k.isdigit() else uspx.get(k, (None, None))
        except Exception:
            p, pd_ = None, None
        r = cons.get(k)
        note = []
        if r:
            e0, e1, e2 = fl(r["eps_0"]), fl(r["eps_a"]), fl(r["eps_b"])
        elif not k.isdigit():
            e0, e1, e2, n = us_direct(k, y1); note.append(n)
        else:
            e0 = e1 = e2 = None
        if p is None:
            na.append(f"{u['name']}(종가 없음)"); continue
        if e1 is None:
            na.append(f"{u['name']}(이익 전망 없음)"); continue
        if e2 is None:
            g = min(max((e1 / e0 - 1) if (e0 and e0 > 0) else 0, 0), 0.2)
            e2 = e1 * (1 + g); note.append(f"{T}E 외삽 — 신뢰 낮음")
        if e1 <= 0 or e2 <= 0 or e2 / p < 0.01:
            na.append(f"{u['name']}(이익이 거의 없어 이 방법이 안 맞음 — {y1}E {e1:,.2f} · {T}E {e2:,.2f})"); continue
        g1 = e2 / e1 - 1
        base = BASE_KR if (k.isdigit() or k in CHINA) else BASE_US
        hi = lo = None
        if k in MEM:
            kind, M, N = "메모리", 10, MEM_NORMAL * e1
        elif k in cyc or k in CYC_EXTRA:
            kind, M, N = "AI연동", base, CYC_NORMAL * e2
        else:
            kind = "일반"
            M = base * next((m for c, m in TIERS if g1 > c or (c == 0.10 and g1 >= c)), 1.0)
            N = e2
        ratio = (e1 + e2 + e2 + N * M) / DISC / p
        if kind != "일반":
            hi = (e1 + e2 + e2 + e2 * M) / DISC / p
            lo = (e1 + e2 + N + N * M) / DISC / p
        need = (p * DISC - (e1 + 2 * e2)) / e2
        res.append(dict(u, p=p, pd=pd_, per=p / e1, g=g1, M=M, kind=kind, ratio=ratio, hi=hi, lo=lo, need=need,
                        note=" · ".join(x for x in note if x)))

    dates = sorted({r["pd"] for r in res})
    print(f"# 가격대 점검 (홍진채 방식) — 종가 {dates[0]}~{dates[-1]} · 이익 전망 {stamp or '직접 조회'} · {y1}E·{T}E 기준")
    for w in warn:
        print(f"> ⚠️ {w}")
    print(f"\n적정가 = ({y1}E + {T}E×2 + 정상이익×배수) ÷ 1.1³ · 비율 = 적정가÷종가 · ≥1.5 매우 싸다 / 1.15~ 싸다 / 0.85~ 보통 / 그 아래 비싸다")
    for grp in ("보유", "주문", "추가", "참고"):
        rows = sorted((r for r in res if r["grp"] == grp), key=lambda r: -r["ratio"])
        if not rows:
            continue
        print(f"\n## {grp}\n| 종목 | 종가 | {y1}E PER | 비율 | 분류 | 범위(조기종료~호황지속) | 요구배수 | 메모 |\n|---|--:|--:|--:|---|---|--:|---|")
        for r in rows:
            rng = f"{r['lo']:.2f}~{r['hi']:.2f}" if r["hi"] else ""
            memo = " · ".join(x for x in (r["kind"] if r["kind"] != "일반" else "", f"배수 {r['M']:g}", r["note"]) if x)
            print(f"| {r['name']} | {r['p']:,.2f} | {r['per']:.1f} | {r['ratio']:.2f} | {cls(r['ratio'])} | {rng} | {r['need']:.1f} | {memo} |")
    if na or skipped:
        print("\n## 계산 불가\n- " + "\n- ".join(na + [s + " — ETF·기타 시장" for s in skipped]))
    print("\n요구배수 = 지금 주가가 성립하려면 3년 뒤 이후 가치가 " + f"{T}E 이익의 몇 배여야 하는가 (음수면 3년 이익 합이 이미 주가보다 큼)")
    print("내부 분석용 · 투자 권유 아님")


if __name__ == "__main__":
    main()
