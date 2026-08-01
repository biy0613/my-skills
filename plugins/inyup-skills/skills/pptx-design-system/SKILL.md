---
name: pptx-design-system
description: PPT/PPTX 슬라이드를 python-pptx로 만들 때 적용하는 기본 디자인 시스템. 컬러(웜 네이비 ink + 코랄 액센트 + 크림 베이스), 타이포그래피, 인라인 강조(ink-bold + accent-bold 2단 layered), 카드/Callout/테이블/Chip 컴포넌트, 슬라이드 타입 패턴(Title/Section/Comparison/Demo/Data/Signal/Closing) 모두 포함. 사용자가 "발표 자료", "슬라이드", "PPT", "PPTX", "deck", "데크", "프레젠테이션", "pitch deck", "투자 thesis 발표", "투심보고서 발표", "회사 소개 deck", "데모 deck", "demo day 자료", "포트폴리오 발표", "리서치 발표", "섹터 분석 슬라이드", "시장 전망 deck", "thesis deck" 등을 만들거나 수정한다고 할 때 자동 트리거. python-pptx 헬퍼 함수(add_card, add_callout, add_chip, style_table, add_rich_text)를 번들로 제공해 매번 재작성 방지. FV in-house IDM/Company Brief(docx 시스템)와는 다른 PPT 전용 시스템이며, 어떤 주제·맥락의 PPT에도 이 시각 언어를 default로 적용한다.
---

# PPTX Design System  ·  v1.0

> Editorial Research 변종을 PPT에 적용한 시스템 · 웜 네이비 ink + 코랄 액센트 + 크림 베이스
> Parent: `research-report-design-system` (HTML/docx/pptx 공용)
> 이 스킬: **PPT 전용 — python-pptx 실행 가이드 + 재사용 헬퍼 번들**

## 0. When to Use This Skill

PPT/슬라이드/deck/데크/프레젠테이션 관련 산출물이 필요한 모든 경우. 주제 무관 — 투자 thesis, 리서치 발표, 데모 deck, 회사 소개, 섹터 분석, 포트폴리오 모니터링 발표, 외부 미팅용 자료 무엇이든 이 시스템을 default로 적용한다.

**예외**: FV 공식 docx 산출물(IDM, Company Brief, 대표님 보고서)은 별도 Navy/Blue 시스템 사용 — 이 스킬은 PPT에만 적용.

## 1. 작업 시작 전 체크리스트

작업 시작할 때 다음을 확인:

1. python-pptx 설치 여부 (`pip install python-pptx --break-system-packages` 가능)
2. 헬퍼 import: `from scripts.pptx_helpers import *` (이 스킬에 번들된 함수 사용 — 매번 다시 짜지 말 것)
3. 16:9 슬라이드 base (13.333 × 7.5 in)
4. 작업 디렉토리 확인 후 `.pptx` 저장 경로 계획

**Claude Code/Codex 실행 시**: `instruction.md`에 dependency ordering과 verification conditions를 명시. 예: "Step 1: 헬퍼 import 검증 → Step 2: 슬라이드 1 (Title) 생성 → 검증: 배경 white, accent 틱마크 존재 → Step 3..." 형태로.

## 2. Slide Dimensions & Layout

| Token | Value |
|---|---|
| Slide width | 13.333 in (16:9) |
| Slide height | 7.5 in |
| Left margin | 0.8 in |
| Right margin | 0.5 in |
| Top margin | 0.5 in |
| Bottom margin | 0.4 in |
| Content width | ~12.0 in |
| Grid base | 4px (Emu(36576)) |

## 3. Color Tokens (python-pptx RGBColor)

번들된 `scripts/pptx_helpers.py`에 모두 상수로 정의되어 있음 — 직접 RGB 값 쓰지 말고 import해서 사용.

### Surface (배경)

| Token | Hex | Constant | Use |
|---|---|---|---|
| `slide-bg` | `#FFFFFF` | `WHITE` | 슬라이드 배경 (필수 white) |
| `card-bg` | `#FAF6EE` | `CREAM` | 카드/박스 배경 |
| `callout-bg` | `#FCEFE6` | `PEACH` | Callout 배경 |
| `line` | `#E8E1D4` | `LINE` | 카드 보더, 테이블 라인 |
| `line-soft` | `#F0EBE0` | `LINE_SOFT` | 내부 행 디바이더 |

### Ink (텍스트)

| Token | Hex | Constant | Use |
|---|---|---|---|
| `ink` | `#16223F` | `INK` | **Primary 본문 + 헤딩 + ink-bold** |
| `ink-soft` | `#3B486A` | `INK_SOFT` | 보조 설명, 부연 |
| `mute` | `#8C8478` | `MUTE` | 라벨, 캡션, 오버라인 |

### Accent (코랄 — 절제 사용)

| Token | Hex | Constant | Use |
|---|---|---|---|
| `accent` | `#E65A3A` | `ACCENT` | 틱마크, 칩, accent-bold, 결론 anchor |
| `accent-deep` | `#C94524` | `ACCENT_DEEP` | Callout 라벨 |
| `accent-soft` | `#FDE6DA` | `ACCENT_SOFT` | 매우 약한 틴트 배경 |

### Semantic

| Token | Hex | Constant | Use |
|---|---|---|---|
| `signal-green` | `#3A8F5C` | `SIGNAL_GREEN` | Good signal (✓) |
| `signal-yellow` | `#C49B2F` | `SIGNAL_YELLOW` | Yellow flag (❓) |
| `signal-red` | `#C94524` | `SIGNAL_RED` | Risk (= ACCENT_DEEP) |

## 4. Typography

### Font Stack

우선순위: Pretendard → 맑은 고딕 (Malgun Gothic) → Apple SD Gothic Neo

python-pptx에서: `font.name = 'Pretendard'` 또는 시스템 폴백 시 `'맑은 고딕'`.

### Size Hierarchy (슬라이드용)

| Token | Size (Pt) | Weight | Use |
|---|---|---|---|
| Display | 38–42 | Bold | 커버 메인 타이틀 |
| H1 | 28–32 | Bold | 슬라이드 타이틀 |
| H2 | 22–24 | Bold | 서브 헤딩, 핵심 문장 |
| H3 | 18–20 | Bold | 카드 타이틀, 소제목 |
| Body LG | 16–18 | Regular | 핵심 본문, 1줄 강조 |
| Body | 14–15 | Regular | 일반 본문, 카드 텍스트 |
| Label | 12–13 | Regular | 테이블 헤더, 카드 라벨 |
| Caption | 11–12 | Regular | 출처, 주석, 메타 |
| Overline | 10–11 | SemiBold | 섹션 분류 라벨 (UPPER) |

### Inline Emphasis (이 시스템의 핵심)

같은 텍스트 박스 안에서 run을 분리해 두 단계로 강조:

- **ink-bold** (`#16223F` Bold): 슬라이드당 5–10개. 핵심 키워드를 풍성하게 강조해서 10초 안에 슬라이드가 읽히도록.
- **accent-bold** (`#E65A3A` Bold): 슬라이드당 2–4개. 결론 anchor·핵심 takeaway·이상치 수치만.

번들된 `add_rich_text()` 헬퍼로 구현:

```python
from scripts.pptx_helpers import add_rich_text, INK, ACCENT, INK_BOLD, ACCENT_BOLD

# segments: list of (text, bold, color) tuples
segments = [
    ("삼성전자는 ", False, INK),
    ("실적으로 검증된 핵심축", True, INK),       # ink-bold
    ("이다. 결론은 ", False, INK),
    ("고점권에서의 선별", True, ACCENT),          # accent-bold (결론 anchor)
    ("이다.", False, INK),
]
add_rich_text(textframe, segments, font_size=15)
```

**Accent-bold 트리거 (4개 케이스만)**:
1. 슬라이드의 핵심 결론 문장 (1개)
2. 데모 포인트의 핵심 takeaway
3. 리스크/경고 항목의 핵심 phrase
4. 핵심 수치 중 이상치

이외 강조는 모두 ink-bold로. accent를 장식으로 쓰면 navigation anchor 기능을 잃는다.

## 5. Component Patterns

번들된 헬퍼로 모든 컴포넌트가 한 줄 호출. `from scripts.pptx_helpers import *` 후 사용.

### 5.1 Slide Background

```python
set_slide_bg(slide)  # 항상 white. 다른 색 금지.
```

### 5.2 Section Header (슬라이드 타이틀 영역)

좌측 4px 코랄 틱마크 + 타이틀(28–32pt ink bold) + 부제(16–18pt ink-soft 또는 accent).

```python
add_section_header(
    slide,
    title="Stage 1 — 이 딜을 더 볼 것인가",
    subtitle="Day 1 매출, exit 각도, people dependency 3축으로 스크리닝",
)
```

### 5.3 Card (cream background)

```python
add_card(slide, left=Inches(0.8), top=Inches(1.5),
         width=Inches(5.5), height=Inches(3.0))
# ROUNDED_RECTANGLE, fill=CREAM, border=LINE 1pt
```

### 5.4 Callout (peach + left accent bar)

핵심 takeaway, 경고, 결론 박스에 사용.

```python
add_callout(slide, left=Inches(0.8), top=Inches(5.5),
            width=Inches(11.7), height=Inches(1.2),
            label="Key Takeaway")
```

### 5.5 Table

```python
table = slide.shapes.add_table(rows, cols, left, top, width, height).table
style_table(table, header_row=True)
# 헤더: cream bg + ink bold 12pt
# 본문: white bg + ink 13pt
```

### 5.6 Chip (Priority/Status badge)

```python
add_chip(slide, left=Inches(0.8), top=Inches(0.9),
         text="P0", variant='accent')   # 코랄 bg + white text
add_chip(slide, left=Inches(1.3), top=Inches(0.9),
         text="A1", variant='ink')      # 네이비 bg + white text
```

### 5.7 Tick Mark (좌측 코랄 4px 바)

Section Header 외 어디든 강조 시작 위치에. `add_section_header`가 내부적으로 사용하지만 단독으로도 호출 가능:

```python
add_tick_mark(slide, left=Inches(0.8), top=Inches(0.5), height=Inches(0.45))
```

## 6. Slide Type Patterns

### 6.1 Title Slide

```
[White bg, left-aligned]
  [Display 38–42pt ink bold]            ← 메인 타이틀
  [18pt accent]                          ← 부제 (1줄)
  [14pt mute]                            ← 발표자 | 소속 | 날짜
```

### 6.2 Section Intro

```
[코랄 틱마크 + 타이틀 28–30pt ink bold]
[18pt ink-soft 또는 accent-bold]         ← 핵심 문장 1줄
[본문 또는 비교 레이아웃]
```

### 6.3 Comparison (Before/After, 기존/AI)

2-column. 양쪽 모두 cream card. 좌(기존): mute label 위주. 우(개선): accent highlight on key gains.

### 6.4 Demo

타이틀 + 우상단 "LIVE DEMO" 칩(accent bg, white text) + 결과 구조 리스트 또는 스크린샷 placeholder. 텍스트 최소화.

### 6.5 Data/Table

타이틀 + full-width 테이블(헤더 cream) + 하단 캡션(11pt mute, 출처).

### 6.6 Signal (Yellow Flag / Good Signal)

2-column bullet. Yellow flag = `accent-deep` 도트, Good signal = `signal-green` 도트. 각 항목: ink-bold 키워드 + ink 본문.

### 6.7 Closing

3-tier table 또는 pyramid + 하단 결론 1문장(accent-bold).

## 7. Slide Density Guide

| Slide Type | 텍스트 분량 | 권장 요소 |
|---|---|---|
| Title | 3줄 이내 | 타이틀 + 부제 + 메타 |
| Section Intro | 5–8줄 | 타이틀 + 핵심문장 + 3–4 bullet |
| Comparison | 표 5–6행 | 2열 비교 또는 카드 |
| Demo | 최소 텍스트 | 결과 구조 + 데모 영역 |
| Data | 표 6행 이내 | 표 + 캡션 |
| Signal | 2열 bullet | 각 3–5 항목 |
| Closing | 표 3행 + 결론 1문장 | 3단계 + 핵심 1줄 |

## 8. Anti-patterns (PPT 전용 — 위반 금지)

| # | 금지 | 대신 |
|---|---|---|
| 1 | 다크 배경 (네이비/검정) | White 배경 + ink 텍스트 |
| 2 | 그라데이션 배경 | 단색 white |
| 3 | 그림자 효과 | 1px 보더 또는 없음 |
| 4 | 이모지 (🔴🟡🟢) | 텍스트 칩 또는 컬러 도트 |
| 5 | 파란색 accent | 코랄 `#E65A3A` 단일 |
| 6 | 다수 폰트 | Pretendard/맑은 고딕 단일 |
| 7 | 장식 이미지 | 데이터·텍스트·구조로 승부 |
| 8 | accent 12개+/slide | 슬라이드당 2–4개 |
| 9 | 강조 없는 평면 텍스트 | ink-bold 풍성 + accent 정확히 |
| 10 | 모든 텍스트 동일 사이즈 | 위계 준수 (38→28→18→15→12) |
| 11 | 카드 radius 변주 | ROUNDED_RECTANGLE 단일 |
| 12 | 컬러 4색+ | ink + accent + mute + signal 3색 |

## 9. 출고 전 체크리스트

| # | 체크 | 기준 |
|---|---|---|
| 1 | 배경이 white인가? | 필수 |
| 2 | 본문이 INK인가? | 필수 |
| 3 | 슬라이드당 ink-bold 5개+ | 권장 |
| 4 | 슬라이드당 accent-bold 2–4개 | 권장 |
| 5 | 핵심 takeaway가 accent-bold인가? | 필수 |
| 6 | 테이블 헤더가 cream + ink bold인가? | 필수 |
| 7 | Callout이 peach + left accent bar인가? | 필수 |
| 8 | "LIVE DEMO" 배지가 accent bg + white text인가? | 필수 (해당 시) |
| 9 | 10초 안에 슬라이드 핵심 추출 가능? | self-check |
| 10 | 코랄이 navigation anchor로 작동? | self-check |

## 10. 실행 패턴 (Claude Code/Codex)

새 deck 만들 때 권장 순서:

1. `instruction.md` 작성 — 슬라이드 수, 각 슬라이드 type, 핵심 메시지 1줄씩
2. 헬퍼 import + 슬라이드 1개씩 build
3. 매 슬라이드 후 검증 조건 명시 (예: "Slide 3은 cream card 2개와 accent bar 1개를 포함해야 함")
4. 최종 출고 전 §9 체크리스트로 self-review
5. `.pptx` 저장 → present_files

## Reference: 번들된 헬퍼 함수 시그니처

`scripts/pptx_helpers.py`에 정의 (자세한 구현은 해당 파일 참조):

- `set_slide_bg(slide)` → 슬라이드 배경 white
- `add_text_box(slide, left, top, w, h, text, font_size, bold, color, font_name)` → 일반 텍스트 박스
- `add_rich_text(tf, segments, font_size, font_name)` → ink-bold/accent-bold 인라인 강조
- `add_section_header(slide, title, subtitle=None)` → 틱마크 + 타이틀 + 부제
- `add_tick_mark(slide, left, top, height)` → 좌측 코랄 4px 바
- `add_card(slide, left, top, width, height)` → cream 카드
- `add_callout(slide, left, top, width, height, label)` → peach + accent bar callout
- `style_table(table, header_row=True)` → 테이블 스타일링
- `add_chip(slide, left, top, text, variant)` → priority/status chip

상수: `WHITE, CREAM, PEACH, LINE, LINE_SOFT, INK, INK_SOFT, MUTE, ACCENT, ACCENT_DEEP, ACCENT_SOFT, SIGNAL_GREEN, SIGNAL_YELLOW, SIGNAL_RED`
