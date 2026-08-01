---
name: research-report-design-system
description: 리서치 리포트·시장 분석·섹터 딥다이브·종목 메모 등 분석형 문서를 만들 때 일관된 시각 언어를 적용하는 디자인 시스템. 컬러 토큰, 타이포그래피, 인라인 강조 시스템(ink-bold + accent-bold 2단 layered), 카드/테이블 스키마, 우선순위·강도·투자유형 분류 체계, 레이아웃 패턴을 모두 포함. HTML/docx/pptx 어떤 포맷이든 같은 룰로 출력. 사용자가 "리서치 리포트", "시장 분석 자료", "섹터 분석", "종목 카드", "이벤트 캘린더", "주장 검증 표", "테마 지도" 등을 만들 때 이 스킬을 참조한다. FV in-house Navy/Blue 시스템과 별개의 "Editorial Research" 변종.
---

# Research Report Design System  ·  v1.2

> Editorial Research 변종 · 웜 네이비 + 코랄 액센트 + 크림 베이스
> Source: SK증권 한국 AI 인프라·반도체 쇼티지 리포트 (2026.04.24) 시각 분석

## 0. When to Use This Skill

리서치/분석 톤의 문서가 필요할 때. 구체적으로:

- 섹터 분석, 산업 리포트, 시장 전망 자료
- 종목 정리 메모, 포트폴리오 모니터링 자료
- 테마 지도, 병목 분석, 이벤트 캘린더
- 외부 자료(증권사 리포트 등) 재구성·요약
- 다수 종목·다수 섹터를 동시 비교하는 자료

**FV in-house 시스템(Navy #1B2A4A / Blue #2E75B6 / BG #F2F6FA)과 구분.**
FV 회사 공식 문서(IDM, Company Brief, 대표님 보고서)는 **FV 시스템을** 쓴다.
이 스킬은 외부 리서치를 재구성하거나, 개인 노트, 대시보드, 비공식 분석에 쓴다.

## 1. Design Tokens

### 1.1 Color

4그룹으로 운영. 카테고리를 섞지 않는다.

**Surface (배경)**

| Token | Hex | Use |
|---|---|---|
| `--color-page` | `#FFFFFF` | 페이지 배경 |
| `--color-surface` | `#FAF6EE` | 카드 크림 배경 (KPI, Strategy, Sector, Stock 카드) |
| `--color-surface-2` | `#FCEFE6` | Callout 피치 배경 (경고·강조 박스) |
| `--color-line` | `#E8E1D4` | 1px 카드/테이블 보더 |
| `--color-line-soft` | `#F0EBE0` | 카드 내부 행 디바이더 |

**Ink (텍스트)**

| Token | Hex | Use |
|---|---|---|
| `--color-ink` | `#16223F` | **Primary 본문 + 헤딩 + 인라인 ink-bold 강조** |
| `--color-ink-soft` | `#3B486A` | 카드 라벨 옆 보조 설명, 캡션 부연 |
| `--color-mute` | `#8C8478` | 라벨, 캡션, 오버라인 |
| `--color-mute-2` | `#A8A199` | 가장 약한 메타 정보 |

> **v1.1 변경**: 본문 컬러를 `--color-ink-soft`에서 `--color-ink`로 격상. ink-bold 강조의 컬러 대비를 살리려면 본문 자체가 충분히 어두워야 한다. ink-soft는 보조 위계에만.

**Accent (단일 코랄, 절약 사용)**

| Token | Hex | Use |
|---|---|---|
| `--color-accent` | `#E65A3A` | 섹션 틱마크, 칩, 인라인 accent-bold 강조 |
| `--color-accent-deep` | `#C94524` | 호버/프레스, Callout 라벨 |
| `--color-accent-soft` | `#FDE6DA` | 매우 약한 틴트 (배경, 호버 피드백) |

**Color Rule (필수 준수) — v1.1 확장**

Accent는 페이지당 **5~8% 면적**에만. 일반 버튼·링크에는 절대 사용하지 않는다.
허용 사용처 5가지:

1. 섹션 헤더의 좌측 틱마크 + 로마숫자
2. 우선순위 칩 (1/2/3 등)
3. Callout 박스 좌측 바 + Callout 라벨
4. 강조 데이터 셀 (목표가 상회, 이례적 PBR, 위험 신호)
5. **인라인 accent-bold 강조** (§1.5 참조) — 경고·사실 정정·이상치·결론 핵심구

### 1.2 Typography

**Font Stack**

- 메인: `'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif`
- 모노 (테이블 숫자): `'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace`

한글·영문·숫자 모두 같은 스택. 폰트 변주를 만들지 않는다.

**위계 (9단계)**

| Token | Size | Weight | Tracking | Use |
|---|---|---|---|---|
| Display | 46px | 700 | -0.02em | 커버 메인 타이틀 (한 페이지에 1개) |
| H1 | 38px | 700 | -0.02em | 페이지 타이틀 |
| H2 (Section) | 24px | 700 | -0.01em | 섹션 헤더 (오렌지 틱+로마숫자 동반) |
| H3 | 19px | 700 | 0 | 서브섹션 |
| H4 (Card Title) | 17px | 700 | 0 | 카드 타이틀, 섹터명 |
| Body LG | 15.5px | 400 | 0 | 강조 본문, 서브타이틀 |
| Body | 14.5px | 400 | 0 | 일반 본문, 카드 텍스트 |
| Label | 13px | 400 | +0.04em | 카드 라벨, 표 헤더 |
| Caption | 12px | 400 | 0 | 표 주석, 출처, 캡션 |
| Overline | 11px | 600 | +0.18em UPPER | 메타 라벨 (오렌지 점 구분자) |

### 1.3 Body Weight (본문 무게 — v1.1 신규)

본문은 보기보다 무겁다. Pretendard는 다음 무게 매핑:

| 위계 | 무게 |
|---|---|
| 일반 본문 | 400 (regular) |
| 본문 내 ink-bold 강조 (`<strong>`, `<em>`) | **700 (bold)** — 절대 600 이하 쓰지 말 것 |
| 캡션·라벨 | 400 |
| 카드 타이틀 | 700 |
| KPI 숫자 | 700 |

**Numeric**

- KPI 숫자: 28px / 700 (sans, `tnum`)
- 인라인 강조 숫자: 22px / 700 (sans, `tnum`)
- 테이블 숫자: 13.5px / 500 (mono, `tnum`)

**Line Height**

- Tight (1.2): Display, H1, H2
- Snug (1.35): H3, H4, Caption
- Base (1.65): Body — v1.1 상향 (1.55 → 1.65)
- Loose (1.75): Card body, Callout — v1.1 상향

### 1.4 Spacing (4px 베이스 그리드)

| Token | Px |
|---|---|
| `--space-1` ~ `--space-10` | 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 56 / 72 |

기본값:

- 카드 내부 패딩: `--space-6` (24px)
- 카드 간 갭 (그리드): `--space-5` (20px)
- 섹션 간 갭: `--space-9` (56px) ~ `--space-10` (72px)
- 페이지 좌우 여백: `--space-6` (24px)

### 1.5 Inline Emphasis System (인라인 강조 시스템 — v1.1 핵심, v1.2 강화)

**이 시스템의 시그니처. 본문 안에 강조가 리듬감 있게 깔려야 스캔이 빠르다.**
두 단계의 강조를 layered로 운영. 하나만 쓰지 않는다.

> **v1.2 핵심 framing — Orange는 장식이 아니라 네비게이션 시스템이다.**
> 페이지를 10초에 스캔해서 결론·경고·이상치를 추출할 수 있어야 한다.
> 페이지에 visible orange anchor가 5~12개 없으면 navigation이 불가능하다.
> "강조를 절제해야 한다"는 ink-bold에 적용되지 않는다 — accent-bold만 절제한다.
> **결론적으로**: ink-bold는 풍성하게(단락당 2~5), accent-bold는 정확한 자리에(단락당 0~1, 페이지당 5~12).

#### 강조 위계

| Class / Tag | 색상 | 무게 | 용도 | 빈도 |
|---|---|---|---|---|
| `<strong>` 또는 `.em` | `--color-ink` | 700 | **핵심 키워드, 결론, 정의** — "ink-bold" | **풍성하게** (단락당 2~5회) |
| `.em-accent` | `--color-accent` | 700 | **경고·사실 정정·이상치·핵심 결론구** — "accent-bold" | **절제** (단락당 0~1회, 페이지당 ≤6회) |
| `<mark>` 또는 `.em-mark` | `--color-ink` on `--color-accent-soft` | 500 | 정의/용어 (희소 사용) | 페이지당 ≤2회 |

#### Ink-Bold (`<strong>`) 사용 기준

이 강조는 **풍성하게** 깔아야 시스템이 작동한다. 본문이 평면이면 시스템이 망한다.

대상:

- 핵심 명사구 ("**메모리 가격 강세**", "**실제 이익으로 확인**")
- 분류·결론 ("**이벤트형·관찰형으로 분류**")
- 정량 사실 ("**병목 강도 최상**", "**52주 고가 근접**")
- 인용 안의 핵심 ("**무조건 비중 확대**"가 아니라)
- 따옴표로 감싼 인용구 ("**삼성 파업은 매수 기회**") — §2.10 참조

자주 쓰지만 다음은 ink-bold 안 쓴다:

- 일반 형용사 ("좋은", "큰") — 정량 형용사("매우 강함")는 OK
- 접속어, 부사

#### Accent-Bold (`.em-accent`) 사용 기준

**이게 시스템의 향이다.** 풍성한 ink-bold 사이에 가끔 박혀 시각 anchor가 된다.

##### v1.2 — 명확한 4가지 트리거 (이 4가지가 보이면 무조건 accent)

**Trigger 1: Conclusion Phrase (단락 결론구)**

단락이 결론으로 닫히는 phrase는 accent. 매 단락마다 1회 권장.

- "...로 직결" / "...라고 판단" / "...가 핵심" / "...는 맞다" / "...아니다"
- "이미 반영" / "구조적으로 막힘" / "회복 어려움"
- "진짜 리스크" / "진짜 채널" / "진짜 변수"
- "둔화 시점" / "전이 시점" / "분기점"

예: "...채널이다" → 그 phrase는 accent

**Trigger 2: Cited Claim (Callout 안의 인용된 주장)**

Callout이 어떤 주장을 인용하면서 지지/검증/반박할 때, **인용된 주장 본문**이 accent. 라벨만으로 끝나지 않는다.

```html
<div class="callout">
  <span class="callout__label">CONTEXT</span>
  업로드 자료의 큰 방향성 —
  <span class="quote"><span class="em-accent">AI 인프라 투자가 메모리·패키징·수동부품·기판·전력기기 병목으로 확산</span></span>
  — 은 현재 데이터와 상당 부분 부합한다.
  SK하이닉스 1Q26 OP 37.6조, 삼성전자 잠정 OP 57.2조는 메모리 가격 강세가
  <span class="em-accent">실제 이익으로 확인</span> 되고 있음을 보여준다.
</div>
```

**Trigger 3: Numerical Anomaly (이상치 숫자)**

다음 임계 통과한 숫자는 accent (ink-bold 아님):

| 메트릭 | 임계값 | 근거 |
|---|---|---|
| PBR | ≥ 10 (또는 산업 평균 2배+) | 극단 밸류 |
| PER | ≥ 100 (또는 산업 평균 3배+) | 극단 밸류 |
| 외국인 비중 | ≤ 1% | 비정상 저비중 |
| 등락률 | ±20%+ | 급등락 |
| 컨센 목표가 | 현재가 ≥ 컨센 목표가 | 목표가 상회 |
| 성장률 | YoY ±50%+ | 비정상 성장/감소 |
| Drawdown | −2σ 이상 | 비정상 하락 |
| 비중 변화 | YoY 절대 ±20%p+ | 비정상 비중 변화 |

**Trigger 4: Warning / Correction (경고·정정)**

- "QA 주의" / "Risk Flag" / "단기 과열" / "조정 가능성"
- "...가능성 금지" / "...로 일반화 금지"
- "최신 IR 확인 기준 ..." (사실 정정)
- "반영도 매우 높음" — 자동 accent (§3.4)
- "둔화 시 동반 조정" — 위험 신호

##### Ink-bold가 맞는 것 (Accent 안 쓴다)

- 일반 키워드 강조
- 정량 사실 (이상치가 아닌 한)
- 분류명, 정의
- 일반 형용사
- 단순 데이터 포인트 ("$675B Capex" — 큰 숫자지만 컨텍스트상 normal)
- 카드의 일반 필드 ("반영도 중상", "강함")

##### v1.2 추가 — Field-by-field Concrete Mapping

각 컴포넌트의 어느 필드에 무슨 강조를 쓰는지 한눈에:

| 위치 | Ink-bold | Accent-bold |
|---|---|---|
| 본문 단락 | 키워드 2~3, 사실 1~2 | 결론구 1 |
| Callout 라벨 | — | 항상 accent (라벨만) |
| Callout 본문 | 일반 키워드 | 인용된 주장 + 결론 |
| Strategy Card 타이틀 | 핵심 명사구 | 결론 phrase 1개 |
| Strategy Card 본문 | 핵심 키워드 2~4 | 결론 1 |
| Sector Card "리스크·반영도" | "반영도 중상", "강함" | "반영도 매우 높음", "PBR 40배" |
| Stock Card "주가 위치" | 일반 PBR/PER | 임계 통과 시 accent |
| KPI 값 | 일반 데이터 | 이상치 데이터 |
| KPI 캡션 | "+36% YoY · 컨센 상회" | 이상치 시그널 |
| 데이터 테이블 셀 | 일반 데이터 | §1.5 Trigger 3 임계 통과 셀 |
| Verify "위험한 해석" | 일반 텍스트 | 핵심 경고구 |
| Verify "전략화 조건" | 조건명 | — |
| Trigger Calendar 마지막 행 | 일반 | "진짜 리스크" 같은 결론 |

#### Density Calibration (강조 밀도 보정 — v1.2 조정)

**평균 본문 단락 (3~5줄, 80~150자)**

- ink-bold: **2~5개 (필수 floor)**
- accent-bold: **1개 권장 (결론구)** — 0이면 단락에 결론이 없는지 의심

**카드 본문 (Sector / Stock / Strategy)**

- ink-bold: 1~3개
- accent-bold: 카드의 마지막 평가 필드에 1회 (필수에 가까움)

**Callout (5줄 이내)**

- 라벨 (항상 accent) + 1~2개 ink-bold + **1~2개 accent-bold** (인용 주장 + 결론)

**페이지 전체**

- accent-bold inline 사용 **5~12회** (구조적 사용 별도)
  - 5 미만: navigation 불가능 — 강조 추가
  - 12 초과: 시각 노이즈 — 우선순위 재조정
- 페이지를 10초 안에 스캔해서 핵심을 추출할 수 있는지 self-check

#### Visual Pattern (예시 — v1.2 확장)

❌ **Bad (강조 없음 — 평면)**

```
삼성전자와 SK하이닉스는 실적으로 검증된 핵심축이다.
5~6월에는 파업, 실적 발표, 가격 피크 논쟁을 이용한 분할 접근이 유효하다.
```

❌ **Bad (ink-bold만, 단조 · navigation 불가)**

```
삼성전자와 SK하이닉스는 **실적으로 검증된 핵심축**이다.
5~6월에는 **파업·실적 발표·가격 피크 논쟁**을 이용한 분할 접근이 유효하다.
```

✅ **Good (ink-bold 풍성 + accent-bold가 결론 anchor)**

```html
삼성전자와 SK하이닉스는 <strong>실적으로 검증된 핵심축</strong>이다.
5~6월에는 <strong>파업·실적 발표·가격 피크 논쟁</strong>을 이용한 분할 접근이 유효하다.
다만 결론은 <span class="quote"><strong>무조건 비중 확대</strong></span>가 아니라
<span class="em-accent">고점권에서의 선별</span>이다.
```

#### Common Transformation — 단락 결론구를 accent로 (v1.2)

거의 모든 단락은 다음 transformation을 적용할 수 있다:

```
Before: 그래서 결론은 X다.    ← X에 ink-bold
After:  그래서 결론은 X다.    ← X에 accent-bold
```

```
Before: 진짜 리스크는 Y이다.  ← ink-bold
After:  진짜 리스크는 Y이다.  ← accent-bold
```

```
Before: 채널은 A → B → C.    ← ink-bold
After:  채널은 A → B → C.    ← accent-bold
```

매 단락의 마지막 결론 phrase는 **default = accent**. 일반 정보 phrase는 ink-bold.

### 1.6 Radius

| Token | Px | Use |
|---|---|---|
| `--radius-sm` | 6 | 코드 칩, 인라인 태그 |
| `--radius-md` | 10 | Callout, 테이블 헤더 |
| `--radius-lg` | 14 | **모든 박스 카드 (단일 사용)** |
| `--radius-xl` | 18 | Hero 패널 |
| `--radius-pill` | 999 | 우선순위 칩, 태그 |

카드 라디우스는 **14px 단일**.

### 1.7 Layout

| Token | Value |
|---|---|
| `--container` | 1080~1120px (max page width) |
| `--gutter` | 24px (page side padding) |
| Wide table breakout | landscape A4 (842 × 595pt) |

## 2. Component Schemas

각 컴포넌트는 emphasis 위치를 명시한다 (v1.1 추가).

### 2.1 Section Header

```yaml
section_header:
  tick:        { width: 4px, height: 26px, color: --color-accent }
  roman:       { color: --color-accent, weight: 700, size: 24px }
  title:       { color: --color-ink, weight: 700, size: 24px }
  gap_between: 16px
```

### 2.2 KPI Card

```yaml
kpi_card:
  background: --color-surface
  border:     1px --color-line
  radius:     --radius-lg (14px)
  padding:    --space-5 (20px)

  fields:
    label:   { style: overline, color: --color-mute }
    value:   { size: 28px, weight: 700, color: --color-ink, tnum: true }
    caption: { size: 12px, color: --color-mute }

  emphasis:
    caption_can_have_bold: true   # caption 안에 핵심 사실 ink-bold OK
    accent_in_caption:     "이상치일 때만 (예: '+36% YoY · 컨센 상회')"
```

### 2.3 Callout

```yaml
callout:
  background:    --color-surface-2
  border_left:   4px solid --color-accent
  border_radius: 0 10px 10px 0
  padding:       18px 22px

  optional_label:
    text:   "QA 주의" | "Disclaimer" | "Key Takeaway" | "Risk Flag" | "Context"
    color:  --color-accent-deep
    weight: 700

  emphasis_inside:
    ink_bold:     "1~3회 — 핵심 사실, 결론"
    accent_bold:  "0~1회 — 사실 정정, 경고, 이상치"
```

**예시 마크업:**

```html
<div class="callout">
  <span class="callout__label">QA 주의</span>
  업로드 문서상 일정이 5월 29일로 기재되어 있으나,
  <span class="em-accent">최신 IR 확인 기준 2026년 4월 30일 오전 10시 KST</span>가 맞다.
  5~6월 전략의 출발점은 <strong>4월 30일 콜</strong>이다.
</div>
```

### 2.4 Strategy Card

```yaml
strategy_card:
  background: --color-surface
  border:     1px --color-line
  radius:     14px
  padding:    24px

  badge:  { circle 26px, bg --color-ink, white, 700 }
  title:  { 17px / 700 / --color-ink (H4) }
  body:   { 14.5px / 400 / --color-ink, line 1.7 }

  emphasis:
    body_ink_bold:    "2~4회 (강조 풍성)"
    body_accent_bold: "1회 권장 — 결론 핵심구"
```

### 2.5 Priority Chip

| Variant | Background | Text | Use |
|---|---|---|---|
| `chip` | `--color-accent` | white | 일반 우선순위 (1, 2, 3) |
| `chip--ink` | `--color-ink` | white | Strategy 카드 배지 |
| `chip--ghost` | transparent / 1px accent | `--color-accent` | 보조 라벨 |

### 2.6 Stock Card

```yaml
stock_card:
  required_fields:
    - 투자 포인트
    - 주가 위치
    - 핵심 이벤트
    - 투자 유형
    - 리스크

  emphasis_per_field:
    투자 포인트: "ink-bold 1~2회"
    주가 위치:   "이상치 메트릭은 accent-bold (예: 'PBR 7' accent)"
    핵심 이벤트: "ink-bold (날짜·이벤트명)"
    투자 유형:   "ink-bold (분류명)"
    리스크:      "ink-bold + 가장 큰 리스크는 accent-bold 가능"
```

### 2.7 Sector Card

```yaml
sector_card:
  required_fields:
    - 현재 산업 상황
    - 쇼티지 원인 (또는 "구조적 동인")
    - 단기 모멘텀
    - 중기 모멘텀
    - 수혜 종목
    - 리스크 · 주가 반영도

  emphasis_per_field:
    현재 산업 상황:        "ink-bold 1~2회"
    쇼티지 원인:           "ink-bold (핵심 메커니즘)"
    단기 모멘텀:           "ink-bold (트리거 이벤트)"
    중기 모멘텀:           "ink-bold"
    수혜 종목:             "ink-bold (대표 종목)"
    리스크 · 주가 반영도:  "마지막 평가구는 accent-bold 권장 (필수에 가까움)"
                           "예: '... · [accent]반영도 매우 높음 · PBR 40배[/accent]'"
```

### 2.8 Priority List

```yaml
priority_list:
  emphasis:
    list_items: "각 종목명은 ink-bold, 대시(—) 뒤 thesis는 일반"
    optional:   "한 항목 정도는 핵심 메트릭 accent-bold OK"
```

### 2.9 Meta Table (Key-Value)

```yaml
meta_table:
  emphasis:
    value: "핵심 정체성 (작성자, 출처, 일자)는 ink-bold"
```

### 2.10 Quotation Pattern (인용 패턴 — v1.1 신규)

원본의 시그니처. 따옴표(`"..."`)로 감싸고 안의 내용을 강조한다.

#### 직접 인용 (claim/주장)

```html
<span class="quote">"<strong>삼성 파업은 매수 기회</strong>"</span>
```

- 따옴표는 그대로 (이모지 따옴표 ❝ 금지)
- 내부는 ink-bold (검증할 주장이면)
- 검증된 결론 또는 정정 사실은 accent-bold 가능

#### Verify Component 통합

```html
<div class="verify__claim">삼성 파업은 매수 기회다</div>
```

`.verify__claim`은 `::before`/`::after`로 자동 따옴표 + accent 컬러 처리.

#### 정의 인용

```html
"<strong>AI 수혜</strong>" 라벨이 아닌 실제 매출·OP·FCF로 확인되는 종목 중심
```

#### Don'ts

- 강조 목적의 따옴표 남발 금지 (단락당 1회 이내)
- 큰따옴표/작은따옴표 혼용 금지 — 큰따옴표만
- 빈 따옴표 (강조 없음) 의미 약함 — 차라리 일반 텍스트

## 3. Classification Systems

### 3.1 Priority Tier System (4단계)

| Tier | Chip | Meaning | When to Use |
|---|---|---|---|
| `1` | 🟠 1 | **최우선** — 실적·논리·타이밍 모두 검증됨 | 즉시 액션 / 중심 비중 |
| `1~2` | 🟠 1~2 | **우선** — 핵심 그룹이나 일부 변수 미확정 | 액션 후보 / 추가 확인 필요 |
| `2` | 🟠 2 | **중간** — 논리 강하나 밸류·타이밍 부담 | 관찰 + 트리거 시 액션 |
| `3` | 🟠 3 | **관찰** — 기대감 우선, 실적 확인 부족 | 모니터링만 / 비중 최소 |

### 3.2 Investment Type Taxonomy (5분류)

| Type | Holding Period | Trigger | Position Logic |
|---|---|---|---|
| `장기 코어` | 1년+ | thesis 변화 | 큰 비중 / 분할 매수 |
| `중기 스윙` | 3~12개월 | 실적·이벤트 사이클 | 중간 비중 / 모멘텀 |
| `이벤트 스윙` | 1~3개월 | 단발 이벤트 | 작은 비중 / 빠른 익절 |
| `단기 트레이딩` | 1~4주 | 가격 모멘텀, 수급 | 최소 비중 / 즉시 손절 |
| `관찰형` | — | 트리거 대기 | 비중 0 / 워치리스트 |

### 3.3 Intensity Scale (4단계)

| Level | Meaning |
|---|---|
| `매우 강함` | 가격 인상 + 리드타임 + 실적 전환 모두 확인 |
| `강함` | 2개 이상 확인 |
| `중간~강함` | 1개 확인 + 방향성 명확 |
| `중간` | 방향성만 확인, 데이터 약함 |
| `약함` | 방향성도 불확실 |

### 3.4 Reflection in Price (3단계)

| Level | Meaning | Action Bias |
|---|---|---|
| `반영도 낮음` | 시장이 아직 반영 못함 | 진입 우호 |
| `반영도 중상` | 일부 반영, 추가 트리거 필요 | 트리거 확인 후 진입 |
| `반영도 매우 높음` | 이미 다 반영, 차익실현 위험 | 추격 매수 금지 |

**v1.1 추가**: "반영도 매우 높음" 항목은 **반드시** accent-bold inline 강조 적용.

### 3.5 Highlight Rule (테이블 셀 강조)

자동 강조 트리거:

1. 현재가 ≥ 컨센 목표가 → "컨센 목표가" 셀 accent
2. PBR ≥ 산업 평균의 2배 (또는 절대값 10 이상) → "PBR" 셀 accent
3. PER ≥ 산업 평균의 3배 (또는 절대값 100 이상) → "PER" 셀 accent
4. 외국인 비중 ≤ 1% → "외국인" 셀 accent
5. 당일 ±20% 이상 급등락 → 종목명 또는 핵심 포인트 셀 accent

금지:

- "좋은 신호"를 accent로 강조하지 않는다
- 한 행에 3개 이상 셀 accent 금지

## 4. Table Schemas

### 4.1 Market Data Table (9-column wide, landscape 권장)

| # | Header | Type | Format | Highlight |
|---|---|---|---|---|
| 1 | 종목 | name | bold sans | — |
| 2 | 현재가 | num | mono, comma | — |
| 3 | 시총 | num | mono, "조" 단위 | — |
| 4 | 52주 고 / 저 | num | mono, "X / Y" | — |
| 5 | PER / 추정PER | num | mono, "X.X / Y.Y" | §3.5 #3 |
| 6 | PBR | num | mono, 1자리 소수 | §3.5 #2 |
| 7 | 외국인 | num | mono, "%" | §3.5 #4 |
| 8 | 컨센 목표가 | num | mono, comma | §3.5 #1 |
| 9 | 핵심 포인트 | text | sans, 14자 이내 | — |

### 4.2 Event Calendar Table (4-column)

| # | Header | Type | Width |
|---|---|---|---|
| 1 | 시기 | date_label | 80px |
| 2 | 이벤트 | text | 1fr |
| 3 | 관련 섹터·종목 | tags | 1fr |
| 4 | 전략적 의미 | text | 1.5fr |

### 4.3 Argument Verification Table (4-step) — 시그니처 패턴

| # | Header | Question |
|---|---|---|
| 1 | 논리적 타당성 | 이 주장은 논리적으로 일관되는가? |
| 2 | 데이터 확인 | 실제 데이터/숫자가 이를 지지하는가? |
| 3 | 위험한 해석 | 어떻게 잘못 해석될 수 있는가? |
| 4 | 전략화 조건 | 어떤 조건이 만족돼야 액션 가능한가? |

### 4.4 Intensity Matrix Table (7-column, landscape 권장)

| # | Header |
|---|---|
| 1 | 섹터 |
| 2 | 강도 |
| 3 | 근거 |
| 4 | 수혜 종목 |
| 5 | 단기 모멘텀 |
| 6 | 중기 모멘텀 |
| 7 | 리스크 |

## 5. Layout Patterns

### 5.1 Cover Page

```
[Overline · all-caps · 트래킹]
[Display Title · 46px / 700]
[Subtitle · 15.5px / mute]
[Meta Table · 5~6 rows]
[KPI Grid · 4-up]
[Callout · disclaimer]
```

### 5.2 Standard Section Page (portrait)

```
[Section Header · 틱+로마+제목]
[Lead paragraph · 1~2 줄, ink-bold 강조 포함]
[H3 sub-section]
[Body / Cards / List]
```

### 5.3 Wide Data Section (landscape A4)

7컬럼+ 또는 12행+ 테이블 시.

### 5.4 Card Grid Page

| Type | Recommended Grid | Max per page |
|---|---|---|
| KPI | 4-col | 8 |
| Strategy | 1-col | 3 |
| Sector | 1-col (full-width) | 3 |
| Stock | 3-col | 6 |
| Priority List | 2-col | 4 |

### 5.5 Verification Section

```
[Section Header]
[Lead]
For each claim:
  [Claim Title with 따옴표 + accent]
    ▸ 논리적 타당성
    ▸ 데이터 확인
    ▸ 위험한 해석
    ▸ 전략화 조건
```

### 5.6 Document Skeleton (full report)

```
1   Cover                      [Cover Page]
2   Executive Summary          [Standard Section]
3-4 Hypothesis Extraction      [Standard + Strategy Cards]
5   Market Data                [Wide Data Section · landscape]
6   Macro Analysis             [Standard Section]
7-10 Sector Cards (10개)       [Sector Card Grid]
11-13 Stock Cards (15개)       [Stock Card Grid]
14-15 Argument Verification    [Verification Section]
16   Event Calendar            [Standard + Event Table]
16-17 Priority Watchlist       [Priority List Grid]
17   Risks                     [Standard Section]
18   Conclusion                [Standard Section]
19-20 Appendix                 [Intensity Matrix + Verification Summary]
```

## 6. Document Structure Rules

### 6.1 Section Numbering

- 메인 섹션: 로마숫자 (Ⅰ, Ⅱ, Ⅲ ... Ⅺ)
- 서브섹션: 아라비아 (1, 2, 3)
- 부록: "부록 1.", "부록 2."

### 6.2 Cross-Referencing

- 같은 문서 내 참조: "Ⅶ장 참고", "§3.2 참고"
- 외부 출처: 본문 끝 "출처 — ..." 형식

### 6.3 QA / Disclaimer

- 본문 중 사실 오류 가능 지점은 Callout, 라벨 `QA 주의`
- Disclaimer는 cover 1회, 마지막 1회

### 6.4 Number Formatting

- 단위: "조", "억", "만" 한글 (예: 1,283.3조)
- 천단위 콤마, PER/PBR 2자리 소수, 비율 1자리 소수
- Mono font: 표 셀 숫자만. 본문 인라인 숫자는 sans + `tnum`
- **본문 인라인 핵심 숫자는 ink-bold, 이상치는 accent-bold** (v1.1)

## 7. CSS Tokens (Copy-Paste — v1.1)

```css
/* CDN: <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.min.css" /> */

:root {
  /* Surface */
  --color-page: #FFFFFF;
  --color-surface: #FAF6EE;
  --color-surface-2: #FCEFE6;
  --color-line: #E8E1D4;
  --color-line-soft: #F0EBE0;

  /* Ink */
  --color-ink: #16223F;       /* primary body — v1.1: 본문 기본값 */
  --color-ink-soft: #3B486A;  /* 보조 위계 only */
  --color-mute: #8C8478;

  /* Accent */
  --color-accent: #E65A3A;
  --color-accent-deep: #C94524;
  --color-accent-soft: #FDE6DA;

  /* Type */
  --font-sans: 'Pretendard', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Spacing — 4px base */
  --space-1: 4px;   --space-2: 8px;
  --space-3: 12px;  --space-4: 16px;
  --space-5: 20px;  --space-6: 24px;
  --space-7: 32px;  --space-8: 40px;
  --space-9: 56px;  --space-10: 72px;

  /* Radius */
  --radius-sm: 6px;   --radius-md: 10px;
  --radius-lg: 14px;  --radius-xl: 18px;
  --radius-pill: 999px;
}

/* Body — v1.1 본문 컬러·라인하이트 강화 */
body {
  font-family: var(--font-sans);
  font-size: 14.5px;
  line-height: 1.65;             /* v1.1: 1.55 → 1.65 */
  color: var(--color-ink);       /* v1.1: ink-soft → ink */
}

p { line-height: 1.7; color: var(--color-ink); margin: 0 0 16px; }

/* Inline Emphasis — v1.1 핵심 신규 */
strong, .em {
  font-weight: 700;
  color: var(--color-ink);       /* ink-bold */
}
.em-accent {
  font-weight: 700;
  color: var(--color-accent);    /* accent-bold */
}
mark, .em-mark {
  background: var(--color-accent-soft);
  color: var(--color-ink);
  padding: 0 4px;
  border-radius: 3px;
  font-weight: 500;
}

/* Quotation */
.quote { color: inherit; }
.quote::before { content: '"'; color: var(--color-accent); margin-right: 1px; }
.quote::after  { content: '"'; color: var(--color-accent); margin-left: 1px; }
```

## 8. Format-Specific Application

### 8.1 HTML / Web

- 모든 토큰을 `:root` CSS variables로
- Pretendard CDN 1줄
- **Inline emphasis 마크업** (v1.1):
  - `<strong>` 또는 `.em` → ink-bold
  - `<span class="em-accent">` → accent-bold
  - `<span class="quote">"..."</span>` → 인용
- 컴포넌트 클래스: `.kpi`, `.callout`, `.strategy`, `.stock`, `.sector`, `.section-header`, `.chip`, `.data-table`, `.priority`, `.meta-table`, `.verify`

### 8.2 docx (python-docx / docx-js)

- 컬러: 동일 hex 값
- ink-bold: `bold=True`, `color=#16223F`
- **accent-bold: `bold=True`, `color=#E65A3A`** (v1.1)
- 카드: 1행 1열 테이블 + shading + 보더
- 섹션 헤더: 4pt 컬러 셀 + 텍스트 셀 = 1행 2열 테이블

### 8.3 pptx (python-pptx)

- 슬라이드 배경 white
- 컴포넌트는 직사각형 + fill
- 폰트 Pretendard / 맑은 고딕 폴백
- **inline 강조**: 같은 텍스트 박스 안에서 run마다 color 변경 (v1.1)

### 8.4 Markdown (Obsidian, GitHub)

- 색상 적용 불가 → 구조만
- ink-bold: `**...**`
- accent-bold: 표현 불가 → 굵기 + ⚠️ 또는 `🟠` prefix로 시그널 (Obsidian 전용)
- 또는 Obsidian callout `> [!warning]` 으로 대체
- Priority chip: 이모지 (🟠 1순위)

## 9. Anti-patterns (v1.2 업데이트)

다음은 시스템 룰을 깨는 패턴.

1. **Accent를 일반 강조에 쓰기** — 코랄은 §1.5의 4가지 트리거에만.
2. **Accent를 너무 안 쓰기 (v1.2 강화)** — 페이지당 visible orange anchor가 5개 미만이면 navigation 불가능. **단락 결론구를 ink-bold로 끝내는 것은 가장 흔한 실패 모드**.
3. **Ink-bold를 너무 안 쓰기** — 본문이 평면이면 시스템이 망한다. 단락당 2~5회 ink-bold 권장.
4. **본문 컬러를 ink-soft로** — 본문은 `--color-ink`. ink-soft는 보조 위계 only.
5. **카드 라디우스 변주** — 14px 단일.
6. **컬러 그라데이션** — 단색만.
7. **이모지 사용** — 본문/카드/표에 금지. 분류용 칩(🟠)은 markdown 환경만.
8. **다중 폰트 패밀리** — Pretendard + JetBrains Mono 외 금지.
9. **그림자 (drop shadow)** — depth는 보더로만.
10. **Tier mixing** — Tier 1과 Tier 3을 한 카드 그리드에 섞지 않는다.
11. **6필드 초과 Sector Card** — 6필드 표준.
12. **표 셀 3개 이상 강조** — 한 행 최대 2개.
13. **AI 슬롭 패턴** — 보라 그라데이션, 둥근 큰 카드, 과도한 그림자, 절제 없는 이모지.
14. **따옴표 강조 남발** — 단락당 1회 이내.
15. **Callout 라벨만 orange (v1.2 신규)** — Callout 본문에 인용된 주장이 있으면 그 주장 본문도 orange. 라벨만 orange면 navigation 약함.
16. **임계 통과 데이터를 ink-bold로 (v1.2 신규)** — PBR 40, PER 200 같은 이상치는 자동 accent. ink-bold 처리 시 시스템 위반.
17. **단락 결론을 ink-bold로 (v1.2 신규)** — "...가 진짜 리스크다", "...이미 반영" 같은 결론구는 default accent.

## 10. Decision Tree

```
질문: 이 정보가 뭐야?

핵심 지표 1개?           → KPI Card
4개 이하 핵심 지표 묶음? → KPI Grid (4-up)
경고/주의/면책?          → Callout
번호 있는 주장 묶음?     → Strategy Card
종목 1개 요약?           → Stock Card
섹터 1개 분석?           → Sector Card
순위별 그룹 리스트?      → Priority List
다수 종목 데이터 비교?   → Market Data Table (9-col)
시기별 이벤트?           → Event Calendar Table
주장 검증?               → Argument Verification (4-step)
다수 섹터 강도 비교?     → Intensity Matrix Table
문서 메타데이터?         → Meta Table
긴 본문?                 → 그냥 paragraph (단, ink-bold 풍성하게)
```

## 11. Emphasis Application Checklist (v1.2 강화 — 출고 전 필수 체크)

| # | 체크 항목 | 기준 |
|---|---|---|
| 1 | 본문 컬러가 `--color-ink`인가? | ✅ 필수 |
| 2 | 단락마다 ink-bold 2~5회 있는가? | ✅ 권장 |
| 3 | 페이지당 accent-bold inline **5~12회** 있는가? (v1.2 상향) | ✅ 필수 |
| 4 | accent-bold가 12회 초과인가? | ❌ 줄여라 |
| 5 | accent-bold가 5회 미만인가? | ❌ navigation 불가 — 추가하라 |
| 6 | **각 단락의 결론구가 accent로 끝나는가?** (v1.2 신규) | ✅ 필수 |
| 7 | 카드의 마지막 평가 필드가 accent로 끝나는가? | ✅ 권장 |
| 8 | Callout 라벨이 accent로 시작하는가? | ✅ 필수 |
| 9 | **Callout 안의 인용된 주장 본문이 accent인가?** (v1.2 신규) | ✅ 필수 |
| 10 | 따옴표 인용이 단락당 1회 이내인가? | ✅ 필수 |
| 11 | ink-bold가 단락당 0회인 단락이 많은가? | ❌ 본문 평면 — 강조 추가 |
| 12 | `<strong>` 무게가 700인가? | ✅ 필수 |
| 13 | `<mark>` 사용이 페이지당 ≤2회인가? | ✅ 필수 |
| 14 | **임계 통과 데이터가 모두 accent인가?** (v1.2 신규 · §1.5 Trigger 3 표) | ✅ 필수 |
| 15 | **페이지를 10초 안에 스캔해서 결론을 추출할 수 있는가?** (v1.2 신규) | ✅ 필수 self-check |

이 체크리스트를 통과 못 하면 시스템이 작동하지 않는다.

### v1.2 Self-Check Mantra

> "이 페이지에 visible orange anchor가 5개 이상인가?"
> "10초 안에 결론·경고·이상치를 추출할 수 있는가?"
>
> 둘 중 하나라도 No면, 강조가 부족한 것.

---

## Changelog

### v1.2 — 2026.04.25

**Major: Orange = Navigation System (강조 강도·정확성 강화)**

원본 PDF 재분석 결과 v1.1이 여전히 부족했던 점들 보완:

- **§1.5 Framing 추가**: "Orange는 장식이 아니라 네비게이션 시스템" 명시
- **§1.5 Accent 트리거 4가지 명문화**:
  1. **Conclusion Phrase** — 단락 결론구는 default accent (단락당 1회)
  2. **Cited Claim** — Callout 안의 인용된 주장 본문 accent (라벨만 X)
  3. **Numerical Anomaly** — 8개 임계값 표 (PBR≥10, PER≥100, 외국인≤1%, 등락 ±20%, 컨센 목표가 상회 등)
  4. **Warning / Correction** — 정정·경고·반영도 매우 높음
- **§1.5 Field-by-field Mapping (신규)**: 각 컴포넌트의 어느 필드에 ink/accent 쓰는지 표로
- **§1.5 Common Transformation (신규)**: 단락 결론구를 ink → accent로 변환하는 보편 패턴
- **§1.5 Density**: accent-bold 페이지당 floor를 **5~12회**로 상향 (기존 ≤6 → 5~12)
- **§11 Checklist**: 5 항목 추가 (결론구 체크, Callout 인용 체크, 임계 통과 체크, 10초 스캔 self-check)
- **§11 Self-Check Mantra (신규)**: "10초 스캔으로 결론 추출 가능한가?"

**Why this matters**: v1.1은 emphasis system을 정의했지만 페이지 단위 navigation을 보장하지 않았다. 결과물에서 orange가 visible하지 않아 스캔이 안 되는 문제. v1.2는 "단락 결론은 default accent" 룰로 navigation을 강제한다.

### v1.1 — 2026.04.25

**Major: Inline Emphasis System 정립**

- **§1.1 Color Rule**: 허용 사용처 4 → 5로 확장 (인라인 accent-bold 추가)
- **§1.1 Body Color**: 본문 컬러를 `--color-ink-soft` → `--color-ink`로 격상
- **§1.3 Body Weight (신규)**: Pretendard 무게 매핑 가이드
- **§1.5 Inline Emphasis System (신규 핵심)**: ink-bold (풍성) + accent-bold (절제) 2단 layered system. 빈도 가이드, density calibration, 좋은/나쁜 예시.
- **§2 Component Schemas**: 각 컴포넌트에 `emphasis_per_field` 추가 — 어느 필드가 accent를 받아야 하는지 명시
- **§2.10 Quotation Pattern (신규)**: 따옴표 인용 마크업 표준
- **§3.4 Reflection in Price**: "반영도 매우 높음" 항목 accent-bold inline 의무화
- **§7 CSS Tokens**: `.em`, `.em-accent`, `.em-mark`, `.quote` 추가. body 라인하이트 1.55 → 1.65
- **§9 Anti-patterns**: 4개 추가 (under-emphasis 관련)
- **§11 Emphasis Application Checklist (신규)**: 출고 전 체크리스트

**Why this matters**: v1.0은 컴포넌트는 정확했지만 본문이 평면이었다. 원본 SK증권 리포트의 시각적 리듬은 인라인 강조의 layered 운영에서 나온다. v1.1로 그 리듬을 명문화.

### v1.0 — 2026.04.25

- 초기 디자인 토큰, 컴포넌트 스키마, 분류 체계 정립

---

**Source**: SK증권 부산금융센터 한국 AI 인프라·반도체 쇼티지 리서치 분석 리포트 (2026.04.24) 시각 분석
**Maintainer**: kyung-vault `/rules/research-report-design-system.md`
