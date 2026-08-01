# 한국 주식 데이터 경로 (2026-07 실측)

목차
1. [KRX / pykrx 차단 현황](#1-krx--pykrx-차단-현황)
2. [작동하는 소스](#2-작동하는-소스)
3. [함정 — 조용히 틀린 값을 주는 경로](#3-함정--조용히-틀린-값을-주는-경로)
   · 3.1 FnGuide `SVD_Main` 캐시 버그 · 3.2 네이버 `price` 거래량 · **3.3 동시 요청 시 빈 응답**
   · 3.4 기준일 확정 · 3.5 시총 컷 순서
4. [컨센서스 VAL1~VAL5 시점 매핑](#4-컨센서스-val1val5-시점-매핑)
5. [지표별 소스 매핑과 계산 정의](#5-지표별-소스-매핑과-계산-정의)
6. [소스가 또 바뀌었을 때](#6-소스가-또-바뀌었을-때)

---

## 1. KRX / pykrx 차단 현황

### 증상

`data.krx.co.kr`의 대량 조회 엔드포인트가 **HTTP 400 + 본문 `LOGOUT`**(6바이트)을 반환한다.

```python
r = requests.post('http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd',
    data={'bld':'dbms/MDC/STAT/standard/MDCSTAT01501','mktId':'STK','trdDd':'20260724', ...})
# r.status_code == 400, r.text == 'LOGOUT'
```

pykrx 1.2.8은 이에 맞춰 `KRX_ID`/`KRX_PW` 환경변수 기반 로그인을 요구하도록 바뀌었다(`pykrx/website/comm/auth.py`). 자격증명 없이 import하면 즉시 이 메시지가 출력된다:

```
KRX 로그인 실패: KRX_ID 또는 KRX_PW 환경 변수가 설정되지 않았습니다.
```

### 실측 결과

| 함수 | 결과 |
|---|---|
| `get_market_ticker_list` | 빈 리스트 |
| `get_market_ohlcv(date, market=)` | KeyError (빈 응답) |
| `get_market_cap(date, market=)` | KeyError |
| `get_market_fundamental(date, market=)` | KeyError |
| `get_market_net_purchases_of_equities` | 빈 DataFrame |
| `get_market_trading_value_by_date` | 빈 DataFrame |
| `get_shorting_balance_by_date` | 빈 DataFrame |
| `get_exhaustion_rates_of_foreign_investment` | JSONDecodeError |
| `get_index_ohlcv` | JSONDecodeError |
| `get_market_ohlcv_by_date(from, to, ticker)` | **정상 20행 반환** |

마지막 항목만 살아 있다. 개별 종목 시계열 엔드포인트 일부는 아직 열려 있으나 **거래대금 컬럼이 없어** 쓸모가 제한적이다. 횡단면(by_ticker) 조회는 전부 막혔다.

`openapi.krx.co.kr`도 HTTP 404. 인증키 발급이 필요하다.

### 대응

계정이 있는 사용자라면 환경변수를 **사용자가 직접** 설정하면 pykrx가 정상 작동한다. 자격증명을 대신 입력하거나 물어보지 않는다. 계정이 없으면 아래 우회 경로를 쓴다 — 공매도 잔고를 뺀 모든 지표를 확보할 수 있다.

---

## 2. 작동하는 소스

### 2.1 FinanceDataReader — 유니버스 원장, 가격 시계열

```python
import FinanceDataReader as fdr
kl = fdr.StockListing('KRX')      # 2,872행 × 17열
```

컬럼: `Code, ISU_CD, Name, Market, Dept, Close, ChangeCode, Changes, ChagesRatio, Open, High, Low, Volume, Amount, Marcap, Stocks, MarketId`

**`Dept` 컬럼이 제외 조건을 거의 다 해결한다:**

| Dept 값 | 종목 수(2026-07) | 용도 |
|---|---|---|
| `관리종목(소속부없음)` | 78 | 관리종목 제외 |
| `SPAC(소속부없음)` | 70 | 스팩 제외 |
| `투자주의환기종목(소속부없음)` | 44 | 투자주의환기 제외 |
| `외국기업(소속부없음)` | 17 | 필요 시 제외 |
| NaN / 우량기업부 / 중견기업부 등 | 나머지 | 정상 |

`MarketId`: `STK`(코스피 943) / `KSQ`(코스닥 1,821) / `KNX`(코넥스 108). KONEX는 `MarketId != 'KNX'`로 뺀다.

**ETF·ETN은 애초에 포함되지 않는다** — 별도 제거 단계가 불필요하다.

우선주는 `Dept`로 안 잡히므로 종목코드 끝자리(보통주는 통상 `0`)와 종목명 패턴(`우`, `우B`, `(전환)`)으로 판정한다.

가격 시계열:
```python
d = fdr.DataReader('005930', '2019-01-01', '2026-07-24')
# Open High Low Close Volume Change — 거래대금 없음
```
**KRX 기준 거래량**이라 네이버 `trend`와 일치한다. 40거래일 장중 최고가와 상장일 판정에 쓴다. `d.index[0]`이 최초 거래일이므로 신규상장 판정에 사용할 수 있다.

주의: `pandas 3.x`에서 pykrx가 깨지므로 `pip install pykrx finance-datareader`가 pandas를 2.x로 내린다. 정상이다.

### 2.2 네이버 증권 `trend` — 외국인 수급 (핵심)

```
GET https://m.stock.naver.com/api/stock/{code}/trend?pageSize=20&page={1,2,3}
Headers: User-Agent(브라우저), Referer: https://m.stock.naver.com/
```

응답(배열):
```json
{"itemCode":"005930","bizdate":"20260724",
 "foreignerPureBuyQuant":"-3,428,259","foreignerHoldRatio":"46.70%",
 "organPureBuyQuant":"-3,378,638","individualPureBuyQuant":"+6,675,340",
 "closePrice":"249,500","accumulatedTradingVolume":"26,175,580"}
```

- 순매매는 **주식 수**다. 금액이 필요하면 종가를 곱한다(§5 참조).
- `foreignerHoldRatio`는 KRX 보유비중과 동일. **언론 보도치와 소수점까지 일치**함을 실측으로 확인했다.
- `accumulatedTradingVolume`은 KRX 기준이며 FDR과 일치한다.
- 816종목 동시 수집 시 스레드 10개로 약 5분, 실패 0건.
- ⚠️ **`page` 파라미터가 무시된다.** page 1·2·3·4를 요청해도 전부 **동일한 최근 20거래일**이 온다(실측 확인). 즉 이 엔드포인트로는 20거래일이 한계다. `--lookback`을 20보다 크게 잡으면 전 종목이 이력 부족으로 걸러져 **후보가 0이 되는데 에러는 나지 않는다.**
- 20거래일보다 긴 이력이 필요하면 **§2.2b HTML 경로**를 쓴다. 40거래일 낙폭은 FDR로 계산한다.

### 2.2b 네이버 `frgn.naver` HTML — 20거래일 초과 이력

```
GET https://finance.naver.com/item/frgn.naver?code={code}&page={1,2,3,...}
encoding: euc-kr   →  pd.read_html(..., match="날짜")[-1]
```

이쪽은 **페이지네이션이 실제로 동작한다**. 페이지당 20행씩 과거로 이동한다:

```
p1  2026.07.24 ~ 2026.06.26      p3  2026.05.27 ~ 2026.04.27
p2  2026.06.25 ~ 2026.05.28      p4  2026.04.24 ~ 2026.03.30
```

컬럼 순서: `날짜 · 종가 · 전일비 · 등락률 · 거래량 · 기관 순매매량 · 외국인 순매매량 · 보유주수 · 보유율`

느리고(HTML 파싱) euc-kr이라 번거롭지만 값은 모바일 API와 동일하다. `screener.py`의 `fetch_trend()`가 `lookback > 20`일 때 자동으로 이 경로로 전환한다.

### 2.3 네이버 증권 `integration` — 컨센서스 PER, 목표주가

```
GET https://m.stock.naver.com/api/stock/{code}/integration
```

`totalInfos` 배열에서:
- `per` / `eps` — 실적 기준(후행)
- **`cnsPer` / `cnsEps` — 컨센서스 기준(선행)**
- `pbr`, `bps`, `marketValue`, `foreignRate`, `highPriceOf52Weeks`, `lowPriceOf52Weeks`, `dividendYieldRatio`

그 외 키: `consensusInfo`(목표주가 평균 `priceTargetMean`, 투자의견 `recommMean`, 기준일 `createDate`), `researches`(애널리스트 리포트 목록: 증권사·제목·일자), `industryCode`, `industryCompareInfo`.

`consensusInfo`에 **과거 추정치는 없다.** 컨센서스 변동 이력은 §2.5를 쓴다.

### 2.4 FnGuide — 분기 손익계산서·현금흐름표

```
GET https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp
    ?pGB=1&gicode=A{code}&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701
encoding: utf-8
```

`pd.read_html`로 6개 테이블이 나온다. **인덱스가 아니라 날짜 컬럼의 "간격"으로 판별하라.**

| 인덱스(통상) | 내용 | 날짜 컬럼 예 | 간격 |
|---|---|---|---|
| 0 | 연간 손익계산서 | `2023/12, 2024/12, 2025/12, **2026/03**` | `{12, 3}` |
| **1** | **분기 손익계산서** | `2025/06, 2025/09, 2025/12, 2026/03` | `{3}` |
| 2 / 3 | 연간 / 분기 재무상태표 | 첫 행 `자산` | |
| 4 | 연간 현금흐름표 | 첫 행 `영업활동으로인한현금흐름` | `{12, 3}` |
| **5** | **분기 현금흐름표** | 위 + 3개월 간격 | `{3}` |

> ⚠️ **연간 테이블은 마지막에 최근 분기 컬럼을 덧붙인다.** 그래서 "날짜 컬럼이 모두 `/12`이면 연간"이라는 판별은 **틀린다** — 연간 테이블의 월 집합도 `{12, 3}`이라 분기로 오판된다. 실제로 이 오판 때문에 신세계의 4개 분기 누적 영업이익이 **17,946억(3년+1분기)** 으로 잡혔다. 정답은 **5,454억**이다. 3배 넘게 부풀려지는데 에러는 나지 않는다.
>
> 올바른 판별: **연속한 날짜 컬럼의 간격이 전부 3개월인가.** 연간은 `{12,3}`, 분기는 `{3}`으로 확실히 갈린다. `screener.py`의 `is_quarterly()`가 이 방식이다.

분기 손익계산서 컬럼: `['IFRS(연결)', '2025/06', '2025/09', '2025/12', '2026/03', '전년동기', '전년동기(%)']`

**`전년동기(%)`가 직전분기 OP YoY를 직접 준다.** 단, 전년동기가 적자면 공란이므로 흑자전환으로 재분류해야 한다(SKILL.md 참조).

단위는 **억원**.

사업 개요·매출구성은 `SVD_Corp.asp` + `NewMenuID=102`. 제품별 매출 비중 테이블이 들어 있다.

### 2.5 WISEreport — FY 컨센서스와 변동 추이 (가장 찾기 어려운 경로)

네이버 증권 종목분석 탭의 백엔드다. `cF4002.aspx` 등 대부분의 ajax는 `기업재무정보 접속장애` 페이지를 반환하지만, **`c1050001_data.aspx`는 열려 있다.**

```
GET https://navercomp.wisereport.co.kr/company/ajax/c1050001_data.aspx
Headers: Referer: https://navercomp.wisereport.co.kr/v1/company/c1050001.aspx?cmp_cd={code}
         X-Requested-With: XMLHttpRequest
```

**`flag=2` — FY별 실적/컨센서스 (핵심)**
```
?flag=2&cmp_cd={code}&finGubun=MAIN&frq=0&sec_cd=
```
```json
{"JsonData":[
 {"YYMM":"2025.12(A)","SALES":"13,972.3","YOY":"23.52","OP":"2,772.9","NP":"2,560.7",
  "EPS":"5,783","BPS":"52,634","PER":"11.69","PBR":"1.28","ROE":"12.52","EV":"5.06"},
 {"YYMM":"2026.12(E)","SALES":"16,114.0","OP":"3,667.7","EPS":"8,413","PER":"11.89", ...},
 {"YYMM":"2027.12(E)", ...}, {"YYMM":"2028.12(E)", ...}]}
```
`(A)`=확정, `(E)`=컨센서스. FY-3 ~ FY+3까지 7개 기간. 단위 억원. **12M Fwd PER/OP 산출의 원천**이다.

**`flag=4` — 컨센서스 변동 추이 (필수컷 판정용)**
```
?flag=4&cmp_cd={code}&finGubun=MAIN&frq=0&yymm=202612&sec_cd=
```
```json
{"JsonData":[
 {"ACC_CD":"121500","ACC_NM":"영업이익(억원)","DT":"20260724",
  "VAL1":3668.0,"VAL2":3668.0,"VAL3":3626.0,"VAL4":3080.0,"VAL5":3124.0}, ...]}
```
`ACC_NM`: 투자의견(점수) / 매출액 / 영업이익 / 순이익 / EPS / PER / BPS / PBR / ROE.
`yymm`은 대상 회계연도(`202612`, `202712`). **12M 선행 컨센서스 변동을 보려면 두 연도를 모두 받아 가중 합산**한다.

`flag=5` — 실적 발표 전후 컨센서스(`3개월전(E)`, `발표직전(E)` 등). 보조용.

주의: `yymm` 없이 호출하면 `flag=4`가 빈 배열을 준다. `cF5001/cF5002.aspx`도 `yymm`이 있어야 데이터가 나온다.

### 2.6 DART — 희석성 공시

OpenDART API(`opendart.fss.or.kr`)는 `crtfc_key`가 필요하다. 키 없이 쓰려면 **공시검색 화면을 POST로** 호출한다. **GET은 빈 결과를 준다 — 반드시 POST.**

```python
s = requests.Session()
s.get("https://dart.fss.or.kr/dsab007/main.do", headers=UA)   # 세션 워밍업 필수
r = s.post("https://dart.fss.or.kr/dsab007/detailSearch.ax",
    data={"currentPage":"1","maxResults":"100","sort":"date","series":"desc",
          "textCrpNm":"<회사명>","startDate":"20250725","endDate":"20260724",
          "finalReport":"recent"},
    headers={**UA, "Referer":"https://dart.fss.or.kr/dsab007/main.do",
             "X-Requested-With":"XMLHttpRequest",
             "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"})
# BeautifulSoup(r.text).select("tbody tr") → 공시 목록
```

`textCrpNm`은 **종목코드가 아니라 회사명**이 잘 먹는다. 유사명 회사가 섞이므로 결과에서 회사명을 다시 필터링한다.

키워드: `유상증자`, `전환사채`, `신주인수권부사채`, `교환사채`, `무상증자`.

**공시 존재 ≠ 희석.** 자사주 소각과 상계되는 경우가 있다. 실제 희석률은 EPS 역산 주식수로 교차 확인한다(§5).

---

## 3. 함정 — 조용히 틀린 값을 주는 경로

에러를 던지지 않고 **그럴듯한 틀린 값**을 주기 때문에 위험하다.

### 3.1 FnGuide `SVD_Main.asp` — 항상 삼성전자를 반환

```
SVD_Main.asp?...&gicode=A000990&NewMenuID=101  →  giName = 삼성전자
SVD_Main.asp?...&gicode=A095340&NewMenuID=101  →  giName = 삼성전자
```
응답 길이까지 158,766으로 동일하다. 파라미터 5종(`MenuYn`, `stkGb`, `pGB`, `ReportGB`, `cID`)을 변형해도 동일. 서버측 캐시 버그로 보인다.

**이 페이지의 `PER(Fwd.12M)`을 쓰면 전 종목이 삼성전자 값으로 채워진다.** 선행 PER은 §2.5의 `flag=2`로 직접 계산한다.

`SVD_Finance.asp`, `SVD_Corp.asp`, `SVD_Invest.asp`는 gicode별로 정상 동작한다. 검증법: 응답에서 `id="giName"` 요소를 읽어 요청한 종목명과 대조한다.

### 3.2 네이버 `price` API — 거래량이 KRX 기준이 아님

```
GET https://m.stock.naver.com/api/stock/{code}/price?pageSize=&page=
```
`accumulatedTradingVolume`이 **`trend` API 및 FDR보다 크다.** 삼성전자 2026-07-24 기준 41,226,307 vs 26,175,580 — **57% 괴리**. 대체거래소(넥스트레이드)·시간외 물량을 포함하는 것으로 추정된다. 시가·고가도 다르다.

거래대금·거래량은 **`trend` 또는 FDR로 통일**한다. `price` API는 쓰지 않는다.

### 3.3 FnGuide·WISEreport 동시 요청 — 빈 응답이 "커버리지 없음"으로 위장

동시 요청이 몰리면 이 두 호스트는 **빈 본문이나 `ConnectionResetError [WinError 10054]`** 를 돌려준다. 헤더 문제가 아니다 — 무헤더로도 200이 오므로 `Referer` 유무와 무관하다. 순수한 처리량 제한이다.

위험한 건 실패 방식이다. 빈 `fn_finance`/`fy`는 예외를 던지지 않고 **"실적 데이터가 없는 종목"** 처럼 보인다. 그러면 실적 필수컷에서 탈락하고, 결과는 *엄격한 스크린이 잘 돌았다* 는 모습이 된다. 실측 사례: 워커 6개로 33종목을 받다가 **27종목이 빈 응답** → 최종 "2종목 통과"라는 그럴듯한 답이 나왔고, 순차 재수집(건당 1초 미만) 후에는 **15종목**이었다.

대응 3단:
1. 이 단계만 **동시 3 이하**로 낮춘다 (수급 수집은 네이버라 10도 괜찮다)
2. 결측분을 **순차로 재수집**한다 — 대개 전부 복구된다
3. 그래도 **20% 넘게 남으면 결과를 내지 말고 중단**한다

`screener.py`의 `collect_fund()`가 이 3단을 구현하며, 3번에서 `SystemExit(2)`로 멈춘다. **`verify_sources.py`는 이걸 못 잡는다** — 1종목 점검은 언제나 통과하기 때문이다.

### 3.4 `get_nearest_business_day_in_a_week` — KRX 차단 시 IndexError

기준일 확정에 pykrx를 쓰면 안 된다. FDR로 지수나 대형주를 조회해 마지막 인덱스를 쓴다:
```python
d = fdr.DataReader('005930', <30일전>, <오늘>)
basedate = d.index[-1]
```

### 3.5 유니버스에서 시총 컷을 늦게 걸면 느려진다

시총 2,000억 컷을 먼저 적용하면 2,872 → 820으로 줄어 수집량이 3.5배 감소한다. 유동성 컷은 20일 데이터가 필요하므로 수집 후에 적용한다.

---

## 4. 컨센서스 VAL1~VAL5 시점 매핑

`flag=4`의 컬럼 라벨은 응답에 없다. 페이지 HTML에도 명시되지 않는다. **실증으로 확정했다.**

방법: `PER` 행과 `EPS` 행을 곱하면 각 시점의 주가가 역산된다. 이를 FDR 실제 종가와 대조한다.

```
ISC(095340) PER×EPS 역산가: 134,600 / 145,000 / 184,000 / 242,500 / 58,300
실제 종가:  07-24 134,600 | 07-17 145,000 | 06-24 190,500 | 04-24 235,000 | 2025-07-24 58,900
```

DB하이텍·리노공업으로 재확인한 결과:

| 컬럼 | 시점 | 정확도 |
|---|---|---|
| `VAL1` | **현재(기준일)** | 정확히 일치 |
| `VAL2` | **1주 전** | 정확히 일치 |
| `VAL3` | 1개월 전 | 근사 |
| `VAL4` | **3개월 전** | 근사 |
| `VAL5` | **1년 전** (6개월 전이 아님) | 근사 |

`VAL5`를 6개월 전으로 오해하기 쉽다. 실제로는 1년 전이다.

→ **3개월 컨센서스 변동 = `VAL1` vs `VAL4`**

소스가 바뀌어 매핑이 의심되면 이 역산 방법을 다시 쓴다. `scripts/verify_sources.py`가 자동으로 검사한다.

---

## 5. 지표별 소스 매핑과 계산 정의

| 지표 | 소스 | 정의 |
|---|---|---|
| 외국인 순매수금액 | 네이버 `trend` | Σ(일별 순매매량 × 당일 종가). **KRX는 체결단가 가중이므로 근사치** — 리포트에 명시한다 |
| 거래대금 | 네이버 `trend` | Σ(거래량 × 종가). VWAP 근사 |
| A 순매수÷시총 | 위 ÷ FDR `Marcap` | ×100 |
| B 집중도 | 위 두 값 | 순매수금액 ÷ 거래대금 × 100. **분자·분모에 같은 가격이 곱해져 종가 근사 오차가 상당 부분 상쇄된다** |
| C 지속성 | 네이버 `trend` | 20일 중 순매매량 > 0인 일수. 오차 없음 |
| D 지분율 변화 | 네이버 `trend` | 보유율(기준일) − 보유율(구간 첫날). 오차 없음 |
| 4개 분기 OP/OCF | FnGuide `SVD_Finance` | 분기 테이블의 날짜 컬럼 4개 합 |
| 직전분기 OP YoY | FnGuide `전년동기(%)` | 공란이면 전년동기 적자 → 흑자전환 판정 |
| 12M Fwd EPS/OP | WISEreport `flag=2` | FY0E × w + FY1E × (1−w), w = FY0 잔여일수/365 |
| 12M Fwd PER | 위 + FDR 종가 | 종가 ÷ 12M Fwd EPS |
| 컨센 3개월 변동 | WISEreport `flag=4` ×2개 연도 | 12M Fwd OP(VAL1) ÷ 12M Fwd OP(VAL4) − 1 |
| 40일 낙폭 | FDR | 종가 ÷ 최근 40거래일 `High` 최대 − 1 |
| 희석률 | WISEreport `flag=2` | (NP ÷ EPS) 역산 주식수의 연도별 증감 |
| 공매도 잔고 | — | **확인불가.** KRX 전용, 대체 무료 소스 없음 |
| 수주잔고 | — | **확인불가.** 사업보고서 수동 확인 필요 |

### 12M Fwd 가중치 계산

기준일이 2026-07-24, FY 결산이 12월이면 잔여 160일 → `w = 160/365 = 0.438`.
`12M Fwd EPS = 0.438 × FY26E_EPS + 0.562 × FY27E_EPS`

12월 결산이 아닌 종목은 `YYMM` 문자열에서 결산월을 읽어 조정한다.

---

## 6. 소스가 또 바뀌었을 때

웹 엔드포인트는 계속 변한다. 수리 순서:

1. **`scripts/verify_sources.py`로 어디가 깨졌는지 특정**한다. 전체를 다시 조사하지 않는다.
2. **ajax 엔드포인트를 찾는 법** — 데이터가 차트로만 보이면 백엔드 ajax가 있다. 페이지 HTML을 받아 정규식으로 뽑는다:
   ```python
   re.findall(r'url\s*:\s*["\']([^"\']+)["\']', html)
   re.findall(r"\$\.ajax\([^)]{0,300}", html)
   ```
   `c1050001_data.aspx`를 이렇게 찾았다.
3. **파라미터는 `<select>` 옵션에서** — `itemCnsItem` 같은 셀렉트 박스의 `value`가 API 파라미터 코드다(영업이익 = `121500`).
4. **응답이 비면 필수 파라미터 누락을 의심**한다. `flag=4`는 `yymm` 없이는 빈 배열을 준다.
5. **새 소스를 신뢰하기 전에 교차검증**한다. 알려진 값(다른 소스, 언론 보도)과 대조해 일치를 확인한 뒤에 쓴다. §3의 사례들이 전부 "그럴듯해 보였지만 틀린" 값이었다.
