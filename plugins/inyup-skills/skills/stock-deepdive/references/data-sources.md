# 데이터 소스 — 국장·미장 분기

이 스킬의 데이터 소스는 **공개 시장 데이터와 웹 리서치뿐**이다. 노션·구글시트 등 내부 딜 원천에는 접근하지 않는다(5번 문항은 `dealflow-insight`가 만들어 둔 관찰 DB만 읽는다).

**모든 수치에 출처·조회일을 병기한다.** 조회 실패는 `확인 불가`로 남기고 왜 못 받았는지 적는다.

MCP 도구 이름에는 세션마다 달라지는 서버 해시가 붙는다. **이름을 외워 쓰지 말고 ToolSearch로 접미사를 찾아 로드한다.**

```
ToolSearch: "+opendart disclosures financial"
ToolSearch: "+UsStockInfo stock_info financial_statement"
ToolSearch: "select:WebSearch,WebFetch"
```

---

## 국장 (KOSPI / KOSDAQ)

### 웹 엔드포인트 — `stock-finder-foreign` 스킬의 문서를 따른다

주가·수급·컨센서스·재무 경로는 이미 검증돼 있다. **중복 작성하지 말고 읽는다:**

```
C:\Users\biy06\.claude\skills\stock-finder-foreign\references\data-sources.md
```

거기서 이 딥다이브에 필요한 절:

| 필요한 것 | 절 |
|---|---|
| 12M Fwd PER·목표주가 | §2.3 네이버 `integration` |
| 외국인 수급(6번 매도자 구조) | §2.2 네이버 `trend`, §2.2b `frgn.naver` |
| 분기 손익·현금흐름(A3·3번) | §2.4 FnGuide (2026-08 경로 전면 교체됨) |
| FY 컨센서스와 변동 추이(1번·7번 킬 스위치) | §2.5 WISEreport |
| 매출구성(3번 믹스, 4번 밸류체인 위치) | `screen_result.json`의 `rev_mix` 또는 FnGuide |
| 희석 공시(A5) | §2.6 DART |

**반드시 알고 갈 함정 두 가지** (자세한 것은 위 문서 §3):

- **FnGuide 신버전은 종목 파라미터명이 `cmp_cd`다.** 다른 이름을 쓰면 오류 없이 **삼성전자 데이터**가 온다. 조용히 틀린다.
- **FnGuide 연간 응답(`freq_typ=Y`)은 마지막에 최근 분기를 덧붙인다.** "모두 `/12`면 연간"으로 판별하면 3년+1분기를 합산하게 된다. 판별은 **연속 컬럼 간격이 전부 3개월인지**로 한다.
- 네이버 `price` API의 거래량은 대체거래소를 포함해 KRX 기준보다 크다. 거래대금 비교에 쓰지 않는다.

### DART MCP (`opendart-*`) — 6번·A5의 주력

| 도구 | 쓰는 문항 |
|---|---|
| `find_company` | 종목코드 → 고유번호(`corp_code`) 변환. 다른 DART 도구의 선행 단계 |
| `search_disclosures` | 2번 촉매(수주·계약 공시), A5 희석(CB/BW/유상증자) |
| `get_major_stock` | **6번 — 대량보유 상황보고(5% 룰)** |
| `get_executive_stock` | **6번 — 임원·주요주주 소유보고. 내부자 매도 클러스터 판정의 핵심** |
| `get_largest_shareholders` | 6번 지배구조 |
| `get_treasury_stock` | 자기주식(희석 상계 확인) |
| `get_capital_change` | A5 — 증자·감자 이력 |
| `get_financial_account` / `get_full_financial_statement` | A3·3번 재무 교차검증 |

**희석 판정 시 주의:** 공시가 있어도 실제 주식수가 안 늘었으면 희석이 아니다(자사주 소각과 상계되는 경우가 있다). `get_capital_change`와 `get_treasury_stock`을 함께 본다.

---

## 미장

### UsStockInfo MCP (`UsStockInfo-*`, yfinance 계열)

| 도구 | 쓰는 문항 |
|---|---|
| `get_stock_info` | 1번 — `forwardPE`, `trailingPE`, 시총, 섹터, `earningsDate`(2번 촉매) |
| `get_financial_statement` | A3·3번 — 손익·재무상태·현금흐름(annual/quarterly) |
| `get_historical_stock_prices` | 낙폭 구간 특정(6번) |
| `get_recommendations` | 1번 — 애널리스트 컨센서스 방향·등급 변화 |
| `get_holder_info` | 6번 — 기관·내부자 보유 현황 |
| `get_stock_actions` | 배당·분할 |
| `get_finance_news` | 2번 촉매, 조정 원인 규명 |

`get_stock_info`의 `forwardPE`는 컨센서스 EPS 기준이다. **FY1/FY2 성장률을 알려면 별도 확인이 필요하다** — `get_recommendations`와 웹 리서치로 보완하고, 못 구하면 "컨센서스 성장률 확인 불가"로 남긴다.

### SEC EDGAR

| 필요한 것 | 경로 |
|---|---|
| **내부자 거래(6번)** | Form 4 — `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<티커>&type=4&dateb=&owner=include&count=40` |
| 사업 구조·세그먼트(4번) | 10-K Item 1·7, 10-Q |
| 리스크 요인(7번 스틸맨) | 10-K Item 1A |
| 수시 공시(2번 촉매) | 8-K |
| 전문 검색 | `https://efts.sec.gov/LATEST/search-index?q=...` (EDGAR full-text search) |

WebFetch 시 SEC는 User-Agent를 요구한다. 차단되면 그대로 "확인 불가"로 적고 대체 경로(뉴스·IR)를 쓴다.

### 웹 리서치

`WebSearch`/`WebFetch`로 보완할 것: 조정 원인(지수 급락 vs 종목 고유), 경쟁사 실적, 1차 수혜주의 수주 상황(4번), 정책·규제 일정(2번).

---

## 교차검증 (최소 2건)

1. **컨센서스 PER 이중 소스** — 국장은 네이버 `cnsPer`와 WISEreport FY 추정 PER이 원천이 같아 일치해야 한다. 어긋나면 파싱이 틀린 것이다. 미장은 yfinance `forwardPE`와 뉴스·리서치 인용값을 대조한다.
2. **최근 분기 실적 방향** — 재무 API 값과 실적 발표 기사의 방향이 일치하는지. 어긋나면 분기/연간을 혼동했을 가능성이 높다.

두 검증 결과를 카드 하단에 한 줄로 남긴다. 실패했으면 실패했다고 적는다.

## 조회 실패 시의 원칙

- **`확인 불가`와 `미충족`은 다르다.** 데이터를 못 받은 것을 부정적 판정으로 처리하면 조용히 틀린 결론이 나온다.
- 필수 문항(1·2·7)의 근거를 못 구하면 그 문항은 **성립하지 않은 것**이고, 결론은 PASS다. 다만 카드에 "데이터 부재로 인한 PASS"임을 구분해 적는다 — 나중에 데이터가 생기면 재검토 대상이다.
