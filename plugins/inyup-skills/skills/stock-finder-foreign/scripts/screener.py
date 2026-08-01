# -*- coding: utf-8 -*-
"""
외국인 수급 기반 한국 주식 스크리너 (KOSPI/KOSDAQ)

유니버스 → 외국인 수급 A~D → 실적 필수컷 → 스코어링까지 수행하고
screen_result.json을 남긴다. 단계별 체크포인트를 저장하므로 --resume으로
뒷단계만 다시 돌릴 수 있다.

KRX/pykrx가 로그인 차단된 환경을 전제로 네이버·FnGuide·WISEreport·DART를 쓴다.
각 소스의 함정은 references/data-sources.md 참조.

usage:
  python screener.py --outdir ./run
  python screener.py --outdir ./run --lookback 30 --min-marcap 5000 --op-yoy-min 15
  python screener.py --outdir ./run --resume          # 수집 건너뛰고 재계산만
"""
import sys, io, os, re, json, time, argparse, warnings
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
NV = {**UA, "Referer": "https://m.stock.naver.com/"}
WISE = "https://navercomp.wisereport.co.kr/company/ajax/c1050001_data.aspx"

# 2순위 가점 섹터 — 종목별 밸류체인 포지션은 사람이 쓴다(SKILL.md 참조)
CORE_SECTOR_HINT = ["AI", "데이터센터", "반도체", "전력기기", "뷰티", "조선", "원자력", "방산", "로봇"]


# ────────────────────────── 유틸 ──────────────────────────
def pn(s):
    """'+1,234' '46.70%' → float. 실패 시 NaN (0으로 채우지 않는다)."""
    if s is None:
        return np.nan
    t = str(s).replace(",", "").replace("+", "").replace("%", "").strip()
    if t in ("", "-", "nan", "N/A", "None"):
        return np.nan
    try:
        return float(t)
    except ValueError:
        return np.nan


def log(msg):
    print(msg, flush=True)


# 스로틀링(ConnectionResetError 10054 등)은 밀리초가 아니라 초 단위 대기가 필요하다.
# 짧은 백오프로 포기하면 빈 응답이 '커버리지 없음'으로 위장돼 조용히 틀린 결과가 나온다.
BACKOFF = [1.0, 3.0, 7.0, 15.0]


def retry_json(url, params, headers, tries=4, timeout=25):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(BACKOFF[min(i, len(BACKOFF) - 1)])
    return None


def retry_text(url, params, headers, tries=4, timeout=40, min_len=3000):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200 and len(r.text) >= min_len:
                r.encoding = 'utf-8'
                return r.text
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(BACKOFF[min(i, len(BACKOFF) - 1)])
    return None


def jd(txt):
    try:
        return json.loads(txt).get("JsonData") or []
    except Exception:
        return []


# ────────────────────── 1. 유니버스 ──────────────────────
def build_universe(cfg, out):
    import FinanceDataReader as fdr
    log("\n[1] 유니버스 구축")
    kl = fdr.StockListing('KRX')
    funnel = [("전 상장 종목", len(kl))]
    df = kl.copy()

    df = df[df['MarketId'].isin(['STK', 'KSQ'])]
    funnel.append(("KOSPI+KOSDAQ (KONEX 제외)", len(df)))

    pref = (~df['Code'].str.endswith('0')) | df['Name'].str.contains(
        r'우[BC]?$|\(전환\)|우선주', regex=True, na=False)
    df = df[~pref]
    funnel.append(("우선주 제외", len(df)))

    dept = df['Dept'].astype(str)
    for pat, label in [(df['Name'].str.contains('스팩', na=False) | dept.str.contains('SPAC', na=False), "스팩 제외"),
                       (df['Name'].str.contains('리츠', na=False), "리츠 제외")]:
        df = df[~pat.reindex(df.index, fill_value=False)]
        funnel.append((label, len(df)))
    dept = df['Dept'].astype(str)
    df = df[~dept.str.contains('관리종목', na=False)]
    funnel.append(("관리종목 제외", len(df)))
    dept = df['Dept'].astype(str)
    df = df[~dept.str.contains('투자주의환기', na=False)]
    funnel.append(("투자주의환기 제외", len(df)))

    df = df[df['Marcap'] >= cfg['min_marcap']]
    funnel.append((f"시총 {cfg['min_marcap']/1e8:,.0f}억 이상", len(df)))

    df = df[df['Volume'] > 0]
    funnel.append(("거래정지 배제 (거래량>0)", len(df)))

    for label, n in funnel:
        log(f"    {label:<34} {n:>6}")
    df = df.reset_index(drop=True)
    df.to_pickle(os.path.join(out, "_universe.pkl"))
    json.dump(funnel, open(os.path.join(out, "_funnel.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return df, funnel


# ─────────────────── 2. 외국인 수급 수집 ───────────────────
def fetch_trend_api(code):
    """네이버 모바일 trend API — 빠르지만 page 파라미터를 무시해 항상 최근 20거래일만 준다."""
    j = retry_json(f"https://m.stock.naver.com/api/stock/{code}/trend",
                   {"pageSize": 20, "page": 1}, NV)
    return j or []


def fetch_trend_html(code, need):
    """finance.naver.com/item/frgn.naver — 느리지만 페이지네이션이 실제로 동작한다.

    lookback > 20 일 때 유일한 경로. 모바일 API는 몇 페이지를 요청하든 같은 20행을
    돌려주므로, 이걸 모르면 --lookback 30 이 전 종목 short_hist로 빠져 후보가 0이 된다.
    """
    rows, pages = [], (need + 19) // 20 + 1
    for p in range(1, min(pages, 8) + 1):
        for attempt in range(3):
            try:
                r = requests.get("https://finance.naver.com/item/frgn.naver",
                                 params={"code": code, "page": p}, headers=UA, timeout=25)
                r.encoding = 'euc-kr'
                t = pd.read_html(io.StringIO(r.text), match="날짜")[-1].dropna(how="all")
                t = t[t.iloc[:, 0].astype(str).str.match(r"\d{4}\.\d{2}\.\d{2}")]
                if len(t) == 0:
                    return rows
                for _, x in t.iterrows():
                    rows.append({
                        "bizdate": str(x.iloc[0]).replace(".", ""),
                        "closePrice": x.iloc[1],
                        "accumulatedTradingVolume": x.iloc[4],
                        "organPureBuyQuant": x.iloc[5],
                        "foreignerPureBuyQuant": x.iloc[6],
                        "foreignerHoldRatio": x.iloc[8],
                    })
                break
            except Exception:
                time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
        if len(rows) >= need + 2:
            break
    return rows


def fetch_trend(code, need=20):
    if need <= 20:
        rows = fetch_trend_api(code)
        if len(rows) >= need:
            return rows
    return fetch_trend_html(code, need)


def collect_trend(codes, out, workers, need=20):
    log(f"\n[2] 외국인 수급 수집 ({len(codes)}종목, {need}거래일 필요"
        f"{' · HTML 페이지네이션 경로' if need > 20 else ''})")
    res, fails, t0 = {}, [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_trend, c, need): c for c in codes}
        for n, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                rows = f.result()
                if rows:
                    res[c] = rows
                else:
                    fails.append(c)
            except Exception:
                fails.append(c)
            if n % 100 == 0:
                log(f"    {n}/{len(codes)}  ({time.time()-t0:.0f}s)")
    log(f"    완료 {len(res)} / 실패 {len(fails)}  ({time.time()-t0:.0f}s)")
    if fails:
        log(f"    실패 종목(확인불가 처리): {fails[:15]}{'...' if len(fails)>15 else ''}")
    json.dump({"data": res, "fails": fails},
              open(os.path.join(out, "_trend.json"), "w", encoding="utf-8"))
    return res, fails


# ─────────────────── 3. 수급 지표 A~D ───────────────────
def a_threshold(marcap, cfg):
    if marcap >= cfg['tier_hi']:
        return cfg['a_hi']
    if marcap >= cfg['tier_mid']:
        return cfg['a_mid']
    return cfg['a_lo']


def compute_foreign(uni, trend, cfg, out):
    log("\n[3] 외국인 수급 지표 A~D")
    L = cfg['lookback']
    rows = []
    for _, r in uni.iterrows():
        code = r['Code']
        recs = trend.get(code)
        if not recs:
            continue
        d = pd.DataFrame(recs).drop_duplicates('bizdate').sort_values('bizdate', ascending=False)
        for src, dst in [('foreignerPureBuyQuant', 'fq'), ('closePrice', 'close'),
                         ('accumulatedTradingVolume', 'vol'), ('foreignerHoldRatio', 'fr')]:
            d[dst] = d[src].map(pn)
        d = d.dropna(subset=['close', 'vol'])
        if len(d) < L:
            rows.append({'Code': code, 'Name': r['Name'], 'n_hist': len(d), 'short_hist': True})
            continue
        w = d.head(L).copy()
        w['val'] = w['close'] * w['vol']
        w['fval'] = w['close'] * w['fq']
        tot_val, f_net = w['val'].sum(), w['fval'].sum()
        pos = w.loc[w['fval'] > 0, 'fval']
        rows.append({
            'Code': code, 'Name': r['Name'], 'Market': r['Market'], 'Marcap': r['Marcap'],
            'Close': r['Close'], 'n_hist': len(d), 'short_hist': False,
            'adtv': tot_val / L, 'tot_val': tot_val, 'f_net': f_net,
            'f_net_pct_mcap': f_net / r['Marcap'] * 100,
            'f_concentration': f_net / tot_val * 100 if tot_val else np.nan,
            'f_buy_days': int((w['fq'] > 0).sum()),
            'fr_end': w['fr'].iloc[0], 'fr_start': w['fr'].iloc[-1],
            'd_fr': w['fr'].iloc[0] - w['fr'].iloc[-1],
            'max1d_share': (pos.max() / f_net) if (len(pos) and f_net > 0) else np.nan,
            'start_date': w['bizdate'].iloc[-1], 'end_date': w['bizdate'].iloc[0],
        })
    m = pd.DataFrame(rows)
    short = m[m.get('short_hist', False) == True]
    if len(short):
        log(f"    {L}거래일 미만(신규상장 의심) {len(short)}종목: {short['Name'].tolist()[:10]}")
    m = m[m['short_hist'] == False].copy()

    before = len(m)
    m = m[m['adtv'] >= cfg['min_adtv']]
    log(f"    유동성 컷 (평균 거래대금 {cfg['min_adtv']/1e8:,.0f}억↑): {before} → {len(m)}")

    m['A_thr'] = m['Marcap'].map(lambda x: a_threshold(x, cfg))
    m['A_pass'] = m['f_net_pct_mcap'] >= m['A_thr']
    m['B_pass'] = m['f_concentration'] >= cfg['b_min']
    m['C_pass'] = m['f_buy_days'] >= cfg['c_min']
    m['D_pass'] = m['d_fr'] >= cfg['d_min']
    m['cand'] = m['A_pass'] & (m['B_pass'] | m['C_pass'])
    m['ABCD'] = m[['A_pass', 'B_pass', 'C_pass', 'D_pass']].all(axis=1)

    log(f"    A {int(m['A_pass'].sum())} · B {int(m['B_pass'].sum())} · "
        f"C {int(m['C_pass'].sum())} · D {int(m['D_pass'].sum())}")
    log(f"    후보 A&(B|C) = {int(m['cand'].sum())} · A~D 전부 = {int(m['ABCD'].sum())}")

    m.to_pickle(os.path.join(out, "_foreign.pkl"))
    return m[m['cand']].copy()


# ─────────────────── 4. 실적·컨센서스 수집 ───────────────────
def fetch_fund(code):
    g = "A" + code
    d = {"code": code}
    d["integration"] = retry_json(f"https://m.stock.naver.com/api/stock/{code}/integration", None, NV)
    d["fn_finance"] = retry_text("https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp",
                                 {"pGB": "1", "gicode": g, "cID": "", "MenuYn": "Y",
                                  "ReportGB": "", "NewMenuID": "103", "stkGb": "701"}, UA)
    d["fn_corp"] = retry_text("https://comp.fnguide.com/SVO2/ASP/SVD_Corp.asp",
                              {"pGB": "1", "gicode": g, "cID": "", "MenuYn": "Y",
                               "ReportGB": "", "NewMenuID": "102", "stkGb": "701"}, UA)
    H = {**UA, "X-Requested-With": "XMLHttpRequest",
         "Referer": f"https://navercomp.wisereport.co.kr/v1/company/c1050001.aspx?cmp_cd={code}"}
    base = {"cmp_cd": code, "finGubun": "MAIN", "frq": "0", "sec_cd": ""}
    d["rev0"] = d["rev1"] = None
    fy = retry_json(WISE, {**base, "flag": "2"}, H)
    d["fy"] = fy
    est = [x["YYMM"][:4] for x in (fy.get("JsonData") if fy else []) or [] if "(E)" in x["YYMM"]]
    d["est_years"] = est[:2]
    for i, yr in enumerate(est[:2]):
        d[f"rev{i}"] = retry_json(WISE, {**base, "flag": "4", "yymm": f"{yr}12"}, H)
    return d


REQUIRED_FUND = ("integration", "fn_finance", "fy")


def _missing(store):
    out = {}
    for k, v in store.items():
        m = [f for f in REQUIRED_FUND if not v.get(f)]
        if not m and not (v.get("rev0") or v.get("rev1")):
            m = ["rev"]
        if m:
            out[k] = m
    return out


def collect_fund(codes, out, workers, abort_ratio=0.20):
    """FnGuide/WISEreport는 동시 요청이 많으면 조용히 빈 응답을 준다.

    빈 응답을 그대로 두면 '컨센서스 커버리지 없음'으로 위장돼 필수컷에서 탈락하고,
    결과는 '엄격한 스크린이 잘 돌았다'처럼 보인다 — 가장 위험한 실패 모드다.
    그래서 (1) 동시성을 낮추고 (2) 결측을 순차로 재수집하고 (3) 그래도 많이 남으면
    결과를 내지 않고 중단한다.
    """
    w = max(1, min(workers, 3))
    log(f"\n[4] 실적·컨센서스 수집 ({len(codes)}종목, 동시 {w})")
    store, t0 = {}, time.time()
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs = {ex.submit(fetch_fund, c): c for c in codes}
        for n, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                store[c] = f.result()
            except Exception as e:
                store[c] = {"code": c, "error": repr(e)[:80]}
            if n % 10 == 0:
                log(f"    {n}/{len(codes)} ({time.time()-t0:.0f}s)")

    miss = _missing(store)
    if miss:
        log(f"    1차 결측 {len(miss)}종목 → 순차 재수집")
        for n, c in enumerate(list(miss), 1):
            time.sleep(0.4)
            try:
                store[c] = fetch_fund(c)
            except Exception as e:
                store[c] = {"code": c, "error": repr(e)[:80]}
            if n % 5 == 0:
                log(f"      재수집 {n}/{len(miss)}")
        miss = _missing(store)

    log(f"    완료 {len(store)} · 최종 결측 {len(miss)}  ({time.time()-t0:.0f}s)")
    for k, v in list(miss.items())[:12]:
        log(f"      {k}: {v}")

    json.dump(store, open(os.path.join(out, "_fund.json"), "w", encoding="utf-8"))

    ratio = len(miss) / max(len(store), 1)
    if ratio > abort_ratio:
        log(f"\n{'!'*70}")
        log(f"중단: 후보의 {ratio*100:.0f}%({len(miss)}/{len(store)})가 실적 데이터를 못 받았다.")
        log("이 상태로 진행하면 데이터 실패가 '실적 미달'로 위장돼 잘못된 스크린 결과가 나온다.")
        log("잠시 후 --resume 으로 재실행하면 캐시된 성공분은 유지되고 결측만 다시 받는다.")
        log(f"{'!'*70}")
        raise SystemExit(2)
    return store


# ─────────────────── 5. 실적 필수컷 ───────────────────
def row_by_label(tbl, label):
    c0 = tbl.columns[0]
    key = label.replace(" ", "")
    for _, r in tbl.iterrows():
        if str(r[c0]).replace(" ", "").startswith(key):
            return r
    return None


def is_quarterly(dates):
    """연속 날짜 컬럼의 간격이 전부 3개월이어야 분기 테이블이다.

    FnGuide의 '연간' 테이블은 마지막에 최근 분기를 덧붙인다 —
    ['2023/12','2024/12','2025/12','2026/03'] 처럼. 월 집합만 보면 {12,3}이라
    분기로 오판하게 되고, 그러면 4개 분기 누적이 아니라 '3년 + 1분기'를 합산해
    영업이익·현금흐름이 3배 넘게 부풀려진다(신세계 17,946억 vs 실제 5,454억).
    간격을 보면 연간은 {12,3}, 분기는 {3}으로 확실히 갈린다.
    """
    if len(dates) < 3:
        return False
    v = [int(d[:4]) * 12 + int(d[5:7]) for d in dates]
    return {v[i + 1] - v[i] for i in range(len(v) - 1)} == {3}


def pick_quarter_tables(html):
    """인덱스가 아니라 컬럼 간격으로 분기 손익/현금흐름 테이블을 찾는다."""
    ts = pd.read_html(io.StringIO(html))
    q_is = q_cf = None
    for t in ts:
        cols = [str(c) for c in t.columns]
        dates = [c for c in cols if re.match(r"^\d{4}/\d{2}$", c)]
        if not is_quarterly(dates):
            continue
        first = str(t.iloc[0, 0]) if len(t) else ""
        if q_is is None and "전년동기(%)" in cols and first.startswith("매출"):
            q_is = t
        if q_cf is None and first.replace(" ", "").startswith("영업활동"):
            q_cf = t
    return q_is, q_cf


def fy_weight(basedate, fy_label):
    """FY0E/FY1E 블렌딩 가중치. 결산월을 YYMM 라벨에서 읽는다."""
    y, m = int(fy_label[:4]), int(fy_label[5:7])
    end = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
    days = (end - pd.Timestamp(basedate)).days
    return float(np.clip(days / 365.0, 0.0, 1.0))


def analyze(cand, fund, cfg, basedate, out):
    log("\n[5] 실적 필수컷")
    rows = []
    for code in cand['Code']:
        f = fund.get(code, {})
        rec = {"Code": code}
        # 분기 실적
        try:
            q_is, q_cf = pick_quarter_tables(f["fn_finance"])
            qcols = [c for c in q_is.columns if re.match(r"^\d{4}/\d{2}$", str(c))]
            r_op, r_np = row_by_label(q_is, "영업이익"), row_by_label(q_is, "당기순이익")
            r_sl = row_by_label(q_is, "매출액")
            rec["lastq"] = qcols[-1]
            rec["op_4q"] = np.nansum([pn(r_op[c]) for c in qcols])
            rec["np_4q"] = np.nansum([pn(r_np[c]) for c in qcols])
            rec["sales_4q"] = np.nansum([pn(r_sl[c]) for c in qcols])
            rec["op_lastq"] = pn(r_op[qcols[-1]])
            rec["op_prevyr"] = pn(r_op["전년동기"]) if "전년동기" in q_is.columns else np.nan
            cfc = [c for c in q_cf.columns if re.match(r"^\d{4}/\d{2}$", str(c))]
            r_cf = row_by_label(q_cf, "영업활동으로인한현금흐름")
            rec["ocf_4q"] = np.nansum([pn(r_cf[c]) for c in cfc])
        except Exception as e:
            rec["fn_err"] = repr(e)[:70]
        # FY 컨센서스
        try:
            fy = {x["YYMM"]: x for x in jd(json.dumps(f["fy"]))} if f.get("fy") else {}
            est = sorted([k for k in fy if "(E)" in k])
            act = sorted([k for k in fy if "(A)" in k])
            rec["fy0"], rec["fy1"] = (est + [None, None])[:2]
            if rec["fy0"] and rec["fy1"]:
                w = fy_weight(basedate, rec["fy0"])
                rec["w0"], rec["w1"] = w, 1 - w
                e0, e1 = fy[rec["fy0"]], fy[rec["fy1"]]
                rec["op0E"], rec["op1E"] = pn(e0["OP"]), pn(e1["OP"])
                rec["eps0E"], rec["eps1E"] = pn(e0["EPS"]), pn(e1["EPS"])
                rec["per0E"] = pn(e0["PER"])
                rec["fwd_eps"] = w * rec["eps0E"] + (1 - w) * rec["eps1E"]
                px = float(cand.set_index('Code').loc[code, 'Close'])
                rec["fwdPER"] = px / rec["fwd_eps"] if rec["fwd_eps"] and rec["fwd_eps"] > 0 else np.nan
                g = (rec["eps1E"] / rec["eps0E"] - 1) * 100 if rec["eps0E"] and rec["eps0E"] > 0 else np.nan
                rec["eps_growth"] = g
                rec["PEG"] = rec["fwdPER"] / g if (g and g > 0) else np.nan
                rec["fwdOP"] = w * rec["op0E"] + (1 - w) * rec["op1E"]
            if act:
                rec["opA"] = pn(fy[act[-1]]["OP"])
                rec["shares_hist"] = {k: (pn(fy[k]["NP"]) * 1e8 / pn(fy[k]["EPS"]) / 1e6)
                                      for k in (act[-2:] + est[:1])
                                      if pn(fy[k]["EPS"]) not in (0, np.nan)}
        except Exception as e:
            rec["fy_err"] = repr(e)[:70]
        # 컨센서스 3개월 변동 (12M 선행 = 두 회계연도 가중)
        try:
            r0 = {x["ACC_NM"]: x for x in jd(json.dumps(f["rev0"]))} if f.get("rev0") else {}
            r1 = {x["ACC_NM"]: x for x in jd(json.dumps(f["rev1"]))} if f.get("rev1") else {}
            o0 = next((v for k, v in r0.items() if k.startswith("영업이익")), None)
            o1 = next((v for k, v in r1.items() if k.startswith("영업이익")), None)
            w0 = rec.get("w0", 0.5)

            def blend(key):
                a = pn(o0[key]) if o0 else np.nan
                b = pn(o1[key]) if o1 else np.nan
                if np.isnan(a) and np.isnan(b):
                    return np.nan
                if np.isnan(b):
                    return a
                if np.isnan(a):
                    return b
                return w0 * a + (1 - w0) * b
            now, m3 = blend("VAL1"), blend("VAL4")
            rec["fwdOP_now"], rec["fwdOP_3m"] = now, m3
            rec["cons_chg"] = (now / m3 - 1) * 100 if (m3 and m3 > 0 and not np.isnan(now)) else np.nan
            # 현재 추정치는 있는데 3개월 전 값이 없는 경우(신규 커버리지)와
            # 애초에 커버리지가 없는 경우는 다르다 — 섞으면 탈락 사유가 틀려진다.
            rec["cons_reason"] = ("정상" if not np.isnan(rec["cons_chg"]) else
                                  "3개월전_없음(신규커버리지)" if not np.isnan(now) else
                                  "커버리지_없음")
        except Exception as e:
            rec["rev_err"] = repr(e)[:70]
        # 네이버 보조 + 교차검증
        try:
            it = f.get("integration") or {}
            ti = {x['code']: x['value'] for x in it.get('totalInfos', [])}
            rec["cnsPER_naver"] = pn(str(ti.get('cnsPer', '')).replace('배', ''))
            rec["PER_naver"] = pn(str(ti.get('per', '')).replace('배', ''))
            rec["PBR_naver"] = pn(str(ti.get('pbr', '')).replace('배', ''))
            ci = it.get('consensusInfo') or {}
            rec["tp_mean"] = pn(ci.get('priceTargetMean'))
            rec["recomm"] = pn(ci.get('recommMean'))
            rec["n_report"] = len(it.get('researches') or [])
            rec["rev_mix"] = extract_rev_mix(f.get("fn_corp"))
        except Exception:
            pass
        rows.append(rec)

    df = pd.DataFrame(rows).set_index("Code").join(cand.set_index("Code"))

    # YoY: 흑자전환 처리
    def yoy(r):
        cur, prv = r.get("op_lastq"), r.get("op_prevyr")
        if pd.isna(cur) or pd.isna(prv):
            return np.nan, "확인불가"
        if prv > 0:
            return (cur / prv - 1) * 100, "정상"
        if cur > 0:
            return np.inf, "흑자전환"
        return np.nan, "적자지속"
    df[["op_yoy", "yoy_type"]] = df.apply(lambda r: pd.Series(yoy(r)), axis=1)

    df["cut_op4q"] = df["op_4q"] > 0
    df["cut_opyoy"] = df.apply(
        lambda r: (r["yoy_type"] == "흑자전환") or
                  (r["yoy_type"] == "정상" and r["op_yoy"] >= cfg['op_yoy_min']), axis=1)
    df["cut_ocf"] = df["ocf_4q"] > 0
    if "cons_reason" not in df.columns:
        df["cons_reason"] = "커버리지_없음"
    df["cons_status"] = np.where(df["cons_chg"].isna(),
                         "확인불가(" + df["cons_reason"].fillna("커버리지_없음") + ")",
                         np.where(df["cons_chg"] >= 5, "상향(+5%↑)",
                          np.where(df["cons_chg"] >= 0, "유지/소폭상향", "하향")))
    df["cut_cons"] = df["cons_status"].isin(["상향(+5%↑)", "유지/소폭상향"])
    df["val_status"] = np.where(df["fwdPER"].isna(), "확인불가",
                        np.where((df["fwdPER"] <= cfg['fwd_per_max']) | (df["PEG"] <= cfg['peg_max']),
                                 "충족", "초과"))
    df["cut_val"] = df["val_status"] == "충족"
    df["PASS"] = df[["cut_op4q", "cut_opyoy", "cut_ocf", "cut_cons", "cut_val"]].all(axis=1)

    for c, lab in [("cut_op4q", "4개분기 누적 OP 흑자"), ("cut_opyoy", f"직전분기 OP YoY +{cfg['op_yoy_min']}%"),
                   ("cut_ocf", "4개분기 영업CF 합 (+)"), ("cut_cons", "컨센서스 3개월 비하향"),
                   ("cut_val", f"Fwd PER≤{cfg['fwd_per_max']} 또는 PEG≤{cfg['peg_max']}")]:
        log(f"    {lab:<30} {int(df[c].sum()):>3}/{len(df)}")
    log(f"    {'전부 통과':<30} {int(df['PASS'].sum()):>3}/{len(df)}")
    for reason, n in df.loc[df["cons_chg"].isna(), "cons_reason"].value_counts().items():
        log(f"    컨센서스 확인불가 · {reason}: {n}종목")

    # 배제 플래그 (판정은 사람이)
    df["np_op"] = df["np_4q"] / df["op_4q"]
    df["flag_oneoff"] = df["np_op"] > cfg['np_op_max']
    df["dilution"] = df["shares_hist"].map(dilution_pct) if "shares_hist" in df.columns else np.nan
    df["flag_dilution"] = df["dilution"] > cfg['dilution_max']
    df["flag_block"] = df["max1d_share"] > cfg['max1d_max']
    return df


def dilution_pct(h):
    if not isinstance(h, dict) or len(h) < 2:
        return np.nan
    v = [x for x in h.values() if x and not np.isnan(x)]
    return (v[-1] / v[0] - 1) * 100 if len(v) >= 2 and v[0] else np.nan


def extract_rev_mix(html):
    """제품별 매출 비중을 '제품 비중%' 형태로 정리해 반환.

    원본 표는 연도 컬럼이 대부분 NaN이라 그대로 덤프하면 리포트에 쓸 수 없다.
    가장 최근 값이 있는 연도를 골라 비중 내림차순 문자열로 만든다.
    """
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
        for t in soup.find_all("table"):
            head = t.get_text(" ", strip=True)[:90]
            if "제품명" not in head:
                continue
            d = pd.read_html(io.StringIO(str(t)))[0]
            ycols = [c for c in d.columns if re.match(r"^\d{4}/\d{2}$", str(c))]
            if not ycols or d.shape[1] < 2:
                continue
            label = d.columns[0]
            for y in reversed(ycols):                       # 최신 연도부터
                sub = d[[label, y]].dropna()
                sub = sub[~sub[label].astype(str).str.contains("기타\\(계\\)|^nan$", regex=True)]
                if len(sub) == 0:
                    continue
                sub = sub.sort_values(y, ascending=False).head(6)
                parts = [f"{str(r[label]).strip()} {float(r[y]):.1f}%" for _, r in sub.iterrows()]
                return f"[{y}] " + " · ".join(parts)
        txt = soup.get_text(" ", strip=True)
        m = re.search(r"매출\s*구성(.{0,240})", txt)
        return re.sub(r"\s+", " ", m.group(1)) if m else ""
    except Exception:
        return ""


# ─────────────────── 6. 낙폭 · 상장일 ───────────────────
def add_price_stats(df, cfg, workers):
    import FinanceDataReader as fdr
    log("\n[6] 낙폭 · 상장일 (FDR)")

    def one(code):
        try:
            return code, fdr.DataReader(code, "2015-01-01")
        except Exception:
            return code, None
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for code, d in ex.map(one, list(df.index)):
            if d is None or len(d) == 0:
                rows.append({"Code": code, "dd": np.nan, "hi_n": np.nan,
                             "first_date": None, "n_days": 0})
                continue
            w = d.tail(cfg['dd_window'])
            hi = float(w['High'].max())
            cur = float(d['Close'].iloc[-1])
            rows.append({"Code": code, "hi_n": hi, "dd": (cur / hi - 1) * 100,
                         "hi52": float(d.tail(250)['High'].max()),
                         "first_date": str(d.index[0].date()), "n_days": len(d)})
    p = pd.DataFrame(rows).set_index("Code")
    df = df.join(p)
    cutoff = str((pd.Timestamp.today() - pd.DateOffset(months=cfg['new_listing_months'])).date())
    df["flag_new_listing"] = df["first_date"] > cutoff
    n = int(df["flag_new_listing"].sum())
    if n:
        log(f"    신규상장 {cfg['new_listing_months']}개월 이내 {n}종목 제외: "
            f"{df[df['flag_new_listing']]['Name'].tolist()}")
    return df


# ─────────────────── 7. 스코어링 ───────────────────
def score(df, cfg):
    log("\n[7] 스코어링")

    def f(r):
        a = min(r["f_net_pct_mcap"] / r["A_thr"], 4) / 4 * 20
        b = min(max(r["f_concentration"], 0) / cfg['b_min'], 3) / 3 * 8
        c = float(np.clip((r["f_buy_days"] - cfg['c_min'] + 1) / (cfg['lookback'] - cfg['c_min'] + 1), 0, 1)) * 6
        d = min(max(r["d_fr"], 0) / cfg['d_min'], 4) / 4 * 6
        s1 = a + b + c + d
        yv = 10.0 if r["yoy_type"] == "흑자전환" else float(np.clip(r["op_yoy"] / 100, 0, 1)) * 10
        cv = float(np.clip(max(r["cons_chg"], 0) / 20, 0, 1)) * 8 if not pd.isna(r["cons_chg"]) else 0.0
        ov = 4.0 + (2.0 if (r["op_4q"] > 0 and r["ocf_4q"] / r["op_4q"] >= 1) else 0.0)
        p = r["fwdPER"]
        vv = 6 if p <= 15 else 4.5 if p <= 20 else 3 if p <= 25 else 1.5 if p <= 30 else 1
        s3 = yv + cv + ov + vv
        s2 = 20.0 if r.get("sector_core") else 5.0
        dd = r["dd"]
        s4 = (6 if dd <= -30 else 3 if dd <= -20 else 0) + \
             (4 if (dd <= -30 and not pd.isna(r["cons_chg"]) and r["cons_chg"] >= 0) else 0)
        return pd.Series({"s1": s1, "s1_A": a, "s1_B": b, "s1_C": c, "s1_D": d,
                          "s3": s3, "s3_yoy": yv, "s3_cons": cv, "s3_ocf": ov, "s3_val": vv,
                          "s2": s2, "s4": s4, "total": s1 + s2 + s3 + s4})
    if "sector_core" not in df.columns:
        df["sector_core"] = False          # 섹터 태깅은 사람이 — 기본 '기타'
    if not df["sector_core"].any():
        log("    ※ 섹터 미태깅 — 전 종목 '기타' 5점으로 계산됨. 밸류체인을 확인해 sectors.json을")
        log("      만든 뒤 --sectors sectors.json --resume 으로 재실행하면 2순위 20점이 반영된다.")
    df = df.join(df.apply(f, axis=1))
    df["reset_star"] = (df["dd"] <= -30) & (df["cons_chg"] >= 0)
    # 동점자 처리: 총점 → 순매수 지속일수 → A 기준 대비 배수.
    # 지속일수까지 같은 사례(신세계·리노공업 둘 다 16일)가 실제로 나와서 3차 기준이 필요했다.
    df["a_multiple"] = df["f_net_pct_mcap"] / df["A_thr"]
    return df.sort_values(["total", "f_buy_days", "a_multiple"], ascending=[False, False, False])


# ─────────────────── 메인 ───────────────────
def main():
    ap = argparse.ArgumentParser(description="외국인 수급 기반 한국 주식 스크리너")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--resume", action="store_true", help="수집 단계 건너뛰고 재계산만")
    ap.add_argument("--workers", type=int, default=10)
    # 유니버스
    ap.add_argument("--min-marcap", type=float, default=2000, help="시총 하한 (억원)")
    ap.add_argument("--min-adtv", type=float, default=30, help="20일 평균 거래대금 하한 (억원)")
    ap.add_argument("--new-listing-months", type=int, default=6)
    # 수급
    ap.add_argument("--lookback", type=int, default=20, help="측정 거래일 수")
    ap.add_argument("--a-hi", type=float, default=0.7, help="시총 3조↑ 순매수/시총 임계 (%%)")
    ap.add_argument("--a-mid", type=float, default=1.5)
    ap.add_argument("--a-lo", type=float, default=2.5)
    ap.add_argument("--tier-hi", type=float, default=3e12)
    ap.add_argument("--tier-mid", type=float, default=5e11)
    ap.add_argument("--b-min", type=float, default=5.0, help="집중도 임계 (%%)")
    ap.add_argument("--c-min", type=int, default=11, help="순매수 일수 임계")
    ap.add_argument("--d-min", type=float, default=0.5, help="지분율 변화 임계 (%%p)")
    # 실적
    ap.add_argument("--op-yoy-min", type=float, default=20.0)
    ap.add_argument("--fwd-per-max", type=float, default=30.0)
    ap.add_argument("--peg-max", type=float, default=1.5)
    ap.add_argument("--np-op-max", type=float, default=1.5, help="순이익/영업이익 괴리 플래그")
    ap.add_argument("--dilution-max", type=float, default=10.0)
    ap.add_argument("--max1d-max", type=float, default=0.5, help="단일일 집중 플래그")
    # 조정
    ap.add_argument("--dd-window", type=int, default=40)
    # 섹터 태깅 (2순위) — 밸류체인 판단은 사람이 하므로 파일로 주입한다
    ap.add_argument("--sectors", default=None,
                    help='JSON: {"011070": {"sector":"AI·데이터센터 / 반도체 기판", '
                         '"core":true, "chain_pos":"FC-BGA 반도체기판 → ..."}}')
    a = ap.parse_args()

    cfg = dict(vars(a))
    cfg['min_marcap'] = a.min_marcap * 1e8
    cfg['min_adtv'] = a.min_adtv * 1e8
    out = a.outdir
    os.makedirs(out, exist_ok=True)

    import FinanceDataReader as fdr
    basedate = str(fdr.DataReader('005930', '2026-01-01').index[-1].date())
    log(f"기준일 (직전 거래일): {basedate}")

    ck = lambda n: os.path.join(out, n)
    if a.resume and os.path.exists(ck("_universe.pkl")):
        uni = pd.read_pickle(ck("_universe.pkl"))
        funnel = json.load(open(ck("_funnel.json"), encoding="utf-8"))
        log(f"\n[1] 유니버스 (캐시) {len(uni)}종목")
    else:
        uni, funnel = build_universe(cfg, out)

    if a.resume and os.path.exists(ck("_trend.json")):
        t = json.load(open(ck("_trend.json"), encoding="utf-8"))
        trend, tfails = t["data"], t["fails"]
        log(f"\n[2] 수급 (캐시) {len(trend)}종목")
        deep = max((len(v) for v in trend.values()), default=0)
        if deep < a.lookback:
            log(f"    캐시 이력 {deep}행 < lookback {a.lookback} → 재수집")
            trend, tfails = collect_trend(uni['Code'].tolist(), out, a.workers, a.lookback)
    else:
        trend, tfails = collect_trend(uni['Code'].tolist(), out, a.workers, a.lookback)

    cand = compute_foreign(uni, trend, cfg, out)
    if len(cand) == 0:
        log("\n후보 0종목. 기준을 확인하라.")
        return

    if a.resume and os.path.exists(ck("_fund.json")):
        fund = json.load(open(ck("_fund.json"), encoding="utf-8"))
        need = [c for c in cand['Code'] if c not in fund] + list(_missing(fund))
        need = sorted(set(need))
        log(f"\n[4] 실적 (캐시) {len(fund)}종목 · 보충 필요 {len(need)}종목")
        if need:
            # 캐시를 그대로 믿으면 이전 실행의 수집 실패가 '실적 미달'로 굳는다.
            log("    결측분만 순차 재수집")
            for n, c in enumerate(need, 1):
                time.sleep(0.4)
                try:
                    fund[c] = fetch_fund(c)
                except Exception as e:
                    fund[c] = {"code": c, "error": repr(e)[:80]}
                if n % 5 == 0:
                    log(f"      {n}/{len(need)}")
            left = _missing(fund)
            log(f"    보충 후 결측 {len(left)}종목")
            json.dump(fund, open(ck("_fund.json"), "w", encoding="utf-8"))
    else:
        fund = collect_fund(cand['Code'].tolist(), out, a.workers)

    df = analyze(cand, fund, cfg, basedate, out)
    df = add_price_stats(df, cfg, a.workers)
    df = df[~df["flag_new_listing"].fillna(False)]

    if a.sectors and os.path.exists(a.sectors):
        smap = json.load(open(a.sectors, encoding="utf-8"))
        df["sector"] = df.index.map(lambda c: smap.get(c, {}).get("sector", "기타"))
        df["sector_core"] = df.index.map(lambda c: bool(smap.get(c, {}).get("core", False)))
        df["chain_pos"] = df.index.map(lambda c: smap.get(c, {}).get("chain_pos", ""))
        log(f"\n섹터 태깅 적용: {len(smap)}종목 · 가점 대상 {int(df['sector_core'].sum())}종목")

    passed = score(df[df["PASS"]].copy(), cfg)

    log(f"\n{'='*70}\n최종 통과 {len(passed)}종목\n{'='*70}")
    if len(passed):
        show = passed[["Name", "total", "f_net_pct_mcap", "f_buy_days", "d_fr",
                       "op_yoy", "yoy_type", "cons_chg", "fwdPER", "dd", "reset_star"]].round(2)
        log(show.to_string())
    log("\n배제 플래그 (판정은 직접):")
    for col, lab in [("flag_oneoff", "순이익/영업이익 괴리"), ("flag_dilution", "희석 10%↑"),
                     ("flag_block", "단일일 집중 50%↑")]:
        hit = passed[passed[col].fillna(False)]["Name"].tolist() if col in passed else []
        log(f"    {lab:<22} {hit if hit else '없음'}")

    export = {
        "basedate": basedate,
        "generated": str(pd.Timestamp.today().date()),
        "config": {k: (v if not isinstance(v, float) or np.isfinite(v) else None)
                   for k, v in cfg.items()},
        "funnel": funnel,
        "counts": {"universe": len(uni), "liquid_candidates": len(cand),
                   "passed": len(passed), "trend_fails": len(tfails)},
        "cross_check": build_cross_check(df),
        "stocks": json.loads(passed.reset_index().to_json(orient="records", force_ascii=False)),
        # 탈락 종목도 리포트 Ⅵ장(아까운 종목)에 쓰이므로 낙폭·수급·섹터까지 함께 내보낸다.
        "reject_detail": json.loads(
            df[~df["PASS"]].reset_index()[
                [c for c in ["Code", "Name", "Market", "Marcap", "Close", "sector", "chain_pos",
                             "cut_op4q", "cut_opyoy", "cut_ocf", "cons_status", "cons_reason",
                             "val_status", "op_4q", "op_lastq", "op_prevyr", "op_yoy", "yoy_type",
                             "ocf_4q", "cons_chg", "fwdPER", "PEG", "f_net", "f_net_pct_mcap",
                             "A_thr", "f_concentration", "f_buy_days", "d_fr", "dd", "hi_n",
                             "np_op", "rev_mix"] if c in df.columns]]
            .to_json(orient="records", force_ascii=False)),
    }
    p = os.path.join(out, "screen_result.json")
    json.dump(export, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"\n저장: {p}")
    log("다음 단계 — SKILL.md '2. 결과 해석과 개별 확인'을 따라 밸류체인 포지션·조정 원인·노이즈를 확인한 뒤 리포트를 쓴다.")


def build_cross_check(df):
    """자체 계산 선행 PER과 네이버 cnsPer 대조 (원천이 같아 일치해야 정상)."""
    out = []
    for code, r in df.iterrows():
        a, b = r.get("per0E"), r.get("cnsPER_naver")
        if pd.isna(a) or pd.isna(b):
            continue
        out.append({"code": code, "name": r.get("Name"),
                    "wise_fy0_per": round(float(a), 2), "naver_cnsPer": round(float(b), 2),
                    "match": bool(abs(a - b) <= 0.05)})
    n_ok = sum(1 for x in out if x["match"])
    return {"fy0_per_vs_naver_cnsper": {"checked": len(out), "matched": n_ok,
                                        "detail": out[:20]}}


if __name__ == "__main__":
    main()
