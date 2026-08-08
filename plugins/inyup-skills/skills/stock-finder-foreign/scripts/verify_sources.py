# -*- coding: utf-8 -*-
"""
소스 건전성 점검 — 본 실행 전에 반드시 먼저 돌린다.

웹 엔드포인트는 예고 없이 바뀐다. 이 스크립트는 스크리너가 의존하는 모든 소스를
1종목으로 호출해 정상 여부를 표로 보여준다. 조용히 틀린 값을 주는 알려진 함정
(FnGuide SVD_Main 캐시 버그, 네이버 price API 거래량 불일치, VAL 시점 매핑)도
함께 검사한다.

usage: python verify_sources.py [--code 000990]
"""
import sys, io, os, re, json, argparse, warnings
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
NV = {**UA, "Referer": "https://m.stock.naver.com/"}

results = []
def rec(name, ok, detail):
    results.append((name, ok, detail))
    mark = "OK  " if ok is True else ("WARN" if ok is None else "FAIL")
    print(f"  [{mark}] {name}: {detail}")


def check_fdr():
    try:
        import FinanceDataReader as fdr
    except ImportError:
        rec("FinanceDataReader", False, "미설치 — pip install finance-datareader")
        return None, None
    try:
        kl = fdr.StockListing('KRX')
        need = {'Code', 'Name', 'Market', 'Dept', 'Marcap', 'Stocks', 'MarketId', 'Close', 'Volume'}
        missing = need - set(kl.columns)
        if missing:
            rec("fdr.StockListing('KRX')", False, f"컬럼 누락 {missing}")
        else:
            depts = kl['Dept'].astype(str)
            flags = sum(depts.str.contains(k).any() for k in ['관리종목', 'SPAC', '투자주의환기'])
            rec("fdr.StockListing('KRX')", True,
                f"{len(kl)}행 · Dept 제외플래그 {flags}/3종 검출")
    except Exception as e:
        rec("fdr.StockListing('KRX')", False, repr(e)[:90])
        return None, None
    try:
        d = fdr.DataReader('005930', '2026-01-01')
        bd = str(d.index[-1].date())
        rec("fdr.DataReader (기준일 확정)", True, f"최종 거래일 {bd} · {len(d)}행")
        return bd, d
    except Exception as e:
        rec("fdr.DataReader", False, repr(e)[:90])
        return None, None


def check_naver_trend(code):
    try:
        r = requests.get(f"https://m.stock.naver.com/api/stock/{code}/trend",
                         params={"pageSize": 20, "page": 1}, headers=NV, timeout=20)
        j = r.json()
        need = {"bizdate", "foreignerPureBuyQuant", "foreignerHoldRatio",
                "closePrice", "accumulatedTradingVolume"}
        missing = need - set(j[0].keys())
        if missing:
            rec("네이버 trend API", False, f"필드 누락 {missing}")
            return None
        # page 파라미터가 무시되는지 확인 — 무시되면 lookback>20에 이 경로를 쓸 수 없다
        j2 = requests.get(f"https://m.stock.naver.com/api/stock/{code}/trend",
                          params={"pageSize": 20, "page": 2}, headers=NV, timeout=20).json()
        paged = bool(j2) and j2[0]["bizdate"] != j[0]["bizdate"]
        rec("네이버 trend API", True,
            f"{len(j)}행 · 최신 {j[0]['bizdate']} · 보유율 {j[0]['foreignerHoldRatio']} · "
            f"페이지네이션 {'동작' if paged else '무시됨(20거래일 한도)'}")
        if not paged:
            check_frgn_html(code)
        return j
    except Exception as e:
        rec("네이버 trend API", False, repr(e)[:90])
        return None


def check_frgn_html(code):
    """lookback>20 일 때 쓰는 HTML 페이지네이션 경로."""
    import pandas as pd
    try:
        seen = []
        for p in (1, 2):
            r = requests.get("https://finance.naver.com/item/frgn.naver",
                             params={"code": code, "page": p}, headers=UA, timeout=25)
            r.encoding = 'euc-kr'
            t = pd.read_html(io.StringIO(r.text), match="날짜")[-1].dropna(how="all")
            t = t[t.iloc[:, 0].astype(str).str.match(r"\d{4}\.\d{2}\.\d{2}")]
            seen.append((len(t), str(t.iloc[0, 0]), str(t.iloc[-1, 0])) if len(t) else (0, "-", "-"))
        ok = seen[1][0] > 0 and seen[1][1] != seen[0][1]
        rec("네이버 frgn.naver (긴 이력)", ok,
            f"p1 {seen[0][0]}행 {seen[0][1]}~{seen[0][2]} · p2 {seen[1][0]}행 {seen[1][1]}~{seen[1][2]}")
    except Exception as e:
        rec("네이버 frgn.naver (긴 이력)", False, repr(e)[:90])


def check_naver_integration(code):
    try:
        j = requests.get(f"https://m.stock.naver.com/api/stock/{code}/integration",
                         headers=NV, timeout=20).json()
        ti = {x['code']: x['value'] for x in j.get('totalInfos', [])}
        if 'cnsPer' not in ti:
            rec("네이버 integration API", None, "cnsPer 없음 — 커버리지 없는 종목일 수 있음")
            return ti
        rec("네이버 integration API", True,
            f"cnsPer {ti.get('cnsPer')} · per {ti.get('per')} · 외인 {ti.get('foreignRate')}")
        return ti
    except Exception as e:
        rec("네이버 integration API", False, repr(e)[:90])
        return {}


def check_fnguide_finance(code):
    """FnGuide 신버전 재무 JSON (구 SVD_Finance.asp 는 2026-08 폐쇄)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from screener import fetch_fn, pick_quarter_tables
        fn = fetch_fn(code)
        if not fn:
            rec("FnGuide SVD_Finance", False, "getFinIncome 응답 없음 (경로 변경 또는 차단)")
            return None
        q_is, q_cf = pick_quarter_tables(fn)
        if q_is is None or q_cf is None:
            rec("FnGuide SVD_Finance", False,
                f"분기 테이블 판정 실패 "
                f"(손익 {'O' if q_is is not None else 'X'} / 현금흐름 {'O' if q_cf is not None else 'X'})")
            return None
        qcols = [c for c in q_is.columns if re.match(r"^\d{4}/\d{2}$", str(c))]
        # 연간 응답을 잘못 쓰면 '3년+1분기'가 합산돼 3배 부풀려진다 → 간격 재확인
        v = [int(str(c)[:4]) * 12 + int(str(c)[5:7]) for c in qcols]
        gaps = {v[i + 1] - v[i] for i in range(len(v) - 1)}
        # numpy.bool_ 은 `is True` 판정을 통과하지 못해 rec()가 FAIL로 찍는다 → bool() 필수
        has_op = bool(q_is["항목"].astype(str).str.startswith("영업이익").any())
        has_cf = bool(q_cf["항목"].astype(str).str.replace(" ", "").str.startswith("영업활동").any())
        ok = bool(gaps == {3} and "전년동기" in q_is.columns and has_op and has_cf)
        rec("FnGuide SVD_Finance", ok,
            f"분기 {qcols} · 간격 {gaps} · 전년동기 {'전년동기' in q_is.columns} · "
            f"영업이익 {has_op} · 영업활동현금흐름 {has_cf}")
        return fn
    except Exception as e:
        rec("FnGuide SVD_Finance", False, repr(e)[:90])
        return None


def check_fnguide_main_trap(code):
    """구버전 SVD_Main의 '종목 무관 삼성전자 반환' 함정이 신버전에도 남아 있다.

    신버전은 파라미터명이 cmp_cd 인데, gicode/code 처럼 틀린 이름을 주면 오류가 아니라
    **삼성전자 데이터가 조용히 반환된다.** 전 종목 루프에서 이걸 만나면 모든 종목이
    삼성전자 실적으로 채워지므로, 매번 이 함정이 살아 있는지 확인한다.
    """
    try:
        r = requests.get("https://wcomp.fnguide.com/CompanyInfo/Finance",
                         params={"gicode": "A" + code}, headers=UA, timeout=30)
        r.encoding = 'utf-8'
        m = re.search(r"<title>([^(<]+)\((\d{6})\)", r.text)
        got, gotcd = (m.group(1).strip(), m.group(2)) if m else ("?", "?")
        r2 = requests.get("https://wcomp.fnguide.com/CompanyInfo/Finance",
                          params={"cmp_cd": code}, headers=UA, timeout=30)
        r2.encoding = 'utf-8'
        m2 = re.search(r"<title>([^(<]+)\((\d{6})\)", r2.text)
        ok = bool(m2) and m2.group(2) == code
        rec("[함정] FnGuide 파라미터명", ok,
            f"cmp_cd={code} → {m2.group(1).strip() if m2 else '?'}({m2.group(2) if m2 else '?'}) · "
            f"틀린 이름(gicode) → {got}({gotcd}) — cmp_cd 외의 이름은 조용히 삼성전자를 준다")
    except Exception as e:
        rec("[함정] FnGuide 파라미터명", None, repr(e)[:70])


def check_wise(code):
    B = "https://navercomp.wisereport.co.kr/company/ajax/c1050001_data.aspx"
    H = {**UA, "X-Requested-With": "XMLHttpRequest",
         "Referer": f"https://navercomp.wisereport.co.kr/v1/company/c1050001.aspx?cmp_cd={code}"}
    fy = rev = None
    try:
        j = requests.get(B, params={"flag": "2", "cmp_cd": code, "finGubun": "MAIN",
                                    "frq": "0", "sec_cd": ""}, headers=H, timeout=25).json()
        fy = j.get("JsonData") or []
        est = [x["YYMM"] for x in fy if "(E)" in x["YYMM"]]
        rec("WISEreport flag=2 (FY 컨센서스)", len(est) >= 2,
            f"{len(fy)}기간 · 추정 {est}")
    except Exception as e:
        rec("WISEreport flag=2", False, repr(e)[:90])
    try:
        yy = next((x["YYMM"][:4] for x in (fy or []) if "(E)" in x["YYMM"]), "2026")
        j = requests.get(B, params={"flag": "4", "cmp_cd": code, "finGubun": "MAIN", "frq": "0",
                                    "yymm": f"{yy}12", "sec_cd": ""}, headers=H, timeout=25).json()
        rev = j.get("JsonData") or []
        names = [x["ACC_NM"] for x in rev]
        has_op = any("영업이익" in n for n in names)
        rec("WISEreport flag=4 (컨센 변동추이)", has_op,
            f"{len(rev)}항목 · 영업이익 {has_op} · VAL1~VAL5 {'있음' if rev and 'VAL5' in rev[0] else '없음'}")
    except Exception as e:
        rec("WISEreport flag=4", False, repr(e)[:90])
    return fy, rev


def check_val_mapping(code, rev):
    """PER×EPS 역산가를 해당 종목의 실제 종가와 대조해 VAL1=현재 매핑을 확인."""
    if not rev:
        rec("[함정] VAL 시점 매핑", None, "선행 검사 실패로 건너뜀")
        return
    try:
        import FinanceDataReader as fdr
        px = fdr.DataReader(code, "2026-01-01")     # 삼성전자가 아니라 대상 종목
        rows = {x["ACC_NM"]: x for x in rev}
        per = next((v for k, v in rows.items() if k.startswith("PER")), None)
        eps = next((v for k, v in rows.items() if k.startswith("EPS")), None)
        if not per or not eps:
            rec("[함정] VAL 시점 매핑", None, "PER/EPS 행 없음")
            return
        implied1 = per["VAL1"] * eps["VAL1"]
        actual1 = float(px['Close'].iloc[-1])
        err = abs(implied1 / actual1 - 1) * 100
        ok = err < 2.0
        rec("[함정] VAL 시점 매핑", ok,
            f"VAL1 역산가 {implied1:,.0f} vs 실제 종가 {actual1:,.0f} (오차 {err:.2f}%) "
            f"→ {'VAL1=현재 확인, VAL4=3개월전 사용 가능' if ok else 'VAL 매핑 재검증 필요'}")
    except Exception as e:
        rec("[함정] VAL 시점 매핑", None, repr(e)[:70])


def check_price_trap(code, trend):
    """네이버 price API는 대체거래소를 포함해 KRX 기준과 다르다."""
    if not trend:
        rec("[함정] 네이버 price API", None, "선행 검사 실패로 건너뜀")
        return
    try:
        j = requests.get(f"https://m.stock.naver.com/api/stock/{code}/price",
                         params={"pageSize": 5, "page": 1}, headers=NV, timeout=20).json()
        pv = int(str(j[0]["accumulatedTradingVolume"]).replace(",", ""))
        tv = int(str(trend[0]["accumulatedTradingVolume"]).replace(",", ""))
        gap = (pv / tv - 1) * 100 if tv else 0
        rec("[함정] 네이버 price API", None,
            f"거래량 {pv:,} vs trend {tv:,} (괴리 {gap:+.1f}%) — "
            f"{'괴리 있음, price 사용 금지' if abs(gap) > 1 else '현재는 일치하나 trend 사용 권장'}")
    except Exception as e:
        rec("[함정] 네이버 price API", None, repr(e)[:70])


def check_dart():
    from bs4 import BeautifulSoup
    try:
        s = requests.Session()
        s.get("https://dart.fss.or.kr/dsab007/main.do", headers=UA, timeout=20)
        r = s.post("https://dart.fss.or.kr/dsab007/detailSearch.ax",
                   data={"currentPage": "1", "maxResults": "30", "sort": "date", "series": "desc",
                         "textCrpNm": "DB하이텍", "startDate": "20250101", "endDate": "20261231",
                         "finalReport": "recent"},
                   headers={**UA, "Referer": "https://dart.fss.or.kr/dsab007/main.do",
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                   timeout=25)
        rows = BeautifulSoup(r.text, "lxml").select("tbody tr")
        rec("DART 공시검색 (POST)", len(rows) > 0, f"{len(rows)}건 — GET은 빈 결과이므로 POST 유지")
    except Exception as e:
        rec("DART 공시검색", False, repr(e)[:90])


def check_pykrx():
    """pykrx는 차단 상태에서 stdout/stderr로 로그인 실패 메시지를 그대로 뱉는다.
    점검표를 어지럽히므로 import·호출 구간만 출력을 삼킨다."""
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            from pykrx import stock
    except ImportError:
        rec("pykrx (참고)", None, "미설치 — 이 스크리너는 pykrx 없이 동작한다")
        return
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            t = stock.get_market_ticker_list("20260724", market="KOSPI")
        if not t:
            rec("pykrx (참고)", None,
                "여전히 차단 (빈 결과). KRX_ID/KRX_PW 환경변수를 사용자가 직접 설정하면 복구됨")
        else:
            rec("pykrx (참고)", True,
                f"{len(t)}종목 조회 성공 — KRX 접근 복구됨. 순매수 금액을 원본으로 쓸 수 있다")
    except Exception as e:
        rec("pykrx (참고)", None, f"차단 상태 ({type(e).__name__})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="000990", help="점검용 종목코드 (기본 DB하이텍)")
    a = ap.parse_args()
    code = a.code

    print(f"\n{'='*78}\n소스 건전성 점검 · 대상 종목 {code}\n{'='*78}\n")

    print("[1] 유니버스 · 가격")
    bd, px = check_fdr()

    print("\n[2] 외국인 수급")
    trend = check_naver_trend(code)

    print("\n[3] 실적 · 컨센서스")
    check_naver_integration(code)
    check_fnguide_finance(code)
    fy, rev = check_wise(code)

    print("\n[4] 공시")
    check_dart()

    print("\n[5] 알려진 함정 재검사")
    check_fnguide_main_trap(code)
    check_price_trap(code, trend)
    check_val_mapping(code, rev)

    print("\n[6] 참고")
    check_pykrx()

    fails = [n for n, ok, _ in results if ok is False]
    warns = [n for n, ok, _ in results if ok is None]
    print(f"\n{'='*78}")
    if fails:
        print(f"실패 {len(fails)}건: {', '.join(fails)}")
        print("→ 해당 지표는 '확인불가'로 처리하거나 references/data-sources.md §6을 참고해 수리한다.")
    else:
        print("필수 소스 전부 정상. screener.py 실행 가능.")
    if warns:
        print(f"주의 {len(warns)}건: {', '.join(warns)} (대개 정상 — 상세 메시지 확인)")
    print(f"기준일: {bd or '확인불가'}")
    print('='*78 + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
