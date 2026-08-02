# -*- coding: utf-8 -*-
"""포트폴리오기록.xlsx 생성 · 조회 · 기록 공용 라이브러리.

스킬 `stock-record` / `stock-price` 가 함께 쓴다.

워크북 구조
  대시보드  : KPI + 평가액 스냅샷 시계열 + 차트
  보유종목  : 종목 마스터 (수량·평단이 여기 소스 오브 트루스)
  시세기록  : 날짜×종목 주당단가 원장 (append-only) → 나머지가 여기서 파생
  설정      : 환율·비중 상한
  <종목명>  : 종목별 진입/보유점검/회수/사후추적 기록

종목 시트는 A열의 앵커 마커(#ENTRY, #REVIEW ...)로 섹션을 찾는다.
사용자가 행을 끼워 넣어도 기록 위치를 잃지 않게 하기 위함이다.
"""
from __future__ import annotations

import os
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# --------------------------------------------------------------------------
# 경로
# --------------------------------------------------------------------------
DEFAULT_WB_PATH = os.environ.get(
    "STOCK_PORTFOLIO_XLSX",
    r"C:\Users\biy06\OneDrive\바탕 화면\클로드실습\주식\트레이딩 기록\포트폴리오기록.xlsx",
)

# --------------------------------------------------------------------------
# 디자인 토큰
# --------------------------------------------------------------------------
INK = "1F2A44"        # 웜 네이비
ACCENT = "E8674C"     # 코랄
CREAM = "FBF7F0"
BAND = "EEF1F6"       # 섹션 밴드
LINE = "D6DBE4"
MUTED = "8A93A3"

F_TITLE = Font(name="맑은 고딕", size=16, bold=True, color=INK)
F_SECTION = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF")
F_HEAD = Font(name="맑은 고딕", size=9, bold=True, color="FFFFFF")
F_LABEL = Font(name="맑은 고딕", size=9, bold=True, color=INK)
F_BODY = Font(name="맑은 고딕", size=9, color="222222")
F_MUTED = Font(name="맑은 고딕", size=8, color=MUTED)
F_KPI_LABEL = Font(name="맑은 고딕", size=8, bold=True, color=MUTED)
F_KPI_VALUE = Font(name="맑은 고딕", size=13, bold=True, color=INK)
F_ANCHOR = Font(name="맑은 고딕", size=6, color="EDEDED")

FILL_HEAD = PatternFill("solid", fgColor=INK)
FILL_SECTION = PatternFill("solid", fgColor=INK)
FILL_BAND = PatternFill("solid", fgColor=BAND)
FILL_CREAM = PatternFill("solid", fgColor=CREAM)
FILL_INPUT = PatternFill("solid", fgColor="FFFFFF")

THIN = Side(style="thin", color=LINE)
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WRAP_TOP = Alignment(wrap_text=True, vertical="top")
WRAP_CTR = Alignment(wrap_text=True, vertical="center", horizontal="center")
RIGHT = Alignment(horizontal="right", vertical="center")
LEFT_C = Alignment(horizontal="left", vertical="center")

# 숫자 포맷 — 한국 관행(상승 빨강 / 하락 파랑)
FMT_KRW = "#,##0"
FMT_PNL = '[Red]#,##0;[Blue]-#,##0;"-"'
FMT_PCT = '[Red]0.00%;[Blue]-0.00%;"-"'
FMT_PCT0 = "0.0%"
FMT_PRC = "#,##0.00"
FMT_DATE = "yyyy-mm-dd"

MAXR = 200            # 마스터/원장 수식이 훑는 최대 행

# --------------------------------------------------------------------------
# 시트별 스키마
# --------------------------------------------------------------------------
MASTER_COLS = [
    ("상태", 8), ("종목명", 14), ("티커", 10), ("시장", 9), ("통화", 7),
    ("수량", 10), ("평균단가", 12), ("투자원금(원)", 14),
    ("현재가", 12), ("시세기준일", 12), ("평가액(원)", 14),
    ("평가손익(원)", 14), ("수익률", 10), ("비중", 9), ("목표비중", 9),
    ("손절선", 11), ("익절목표", 11), ("손절까지", 10),
    ("진입일", 12), ("최근점검일", 12), ("기록시트", 14),
]
MASTER_HEAD_ROW = 2
MASTER_FIRST_ROW = 3

PRICE_COLS = [
    ("날짜", 12), ("종목명", 14), ("통화", 7), ("주당단가", 13),
    ("수량", 10), ("환율", 10), ("평가액(원)", 14), ("입력경로", 11),
]
PRICE_HEAD_ROW = 2
PRICE_FIRST_ROW = 3

SNAP_COLS = [
    ("기록일", 12), ("주식평가액", 15), ("보유현금", 14), ("총자산", 15),
    ("입출금(당회)", 13), ("순입금누계", 15), ("평가손익", 15),
    ("누적수익률", 12), ("직전대비", 11), ("메모", 40),
]
SNAP_HEAD_ROW = 11
SNAP_FIRST_ROW = 12

# 종목 시트 — 진입 블록 항목
ENTRY_FIELDS = [
    "기록일",
    "하드게이트 통과 (O/6)",
    "미통과 항목",
    "규칙 이탈 여부",
    "핵심 논지 (한 문장)",
    "가정 1",
    "가정 1 — 확인 시점·방법",
    "가정 2",
    "가정 2 — 확인 시점·방법",
    "가정 3",
    "가정 3 — 확인 시점·방법",
    "반대 논지 (2개 이상)",
    "가장 반박하기 어려운 것",
    "컨센서스와 내 견해 차이",
    "지금 가격이 이미 반영한 것",
    "펀더멘탈",
    "법률·규제 리스크",
    "수급",
    "카탈리스트",
    "시간 지평",
    "정보원",
    "매수 시 감정 상태",
    "목표 비중 / 최대 허용 손실",
    "분할·추가매수 규칙",
    "손절 조건 — 사실",
    "손절 조건 — 가격",
    "손절하지 않는 경우",
    "익절 조건 — 사실",
    "익절 조건 — 가격",
]

REVIEW_COLS = [
    ("점검일", 12), ("점검 요약 — 무엇이 바뀌었나", 70), ("가정1", 10),
    ("가정2", 10), ("가정3", 10), ("논지 드리프트", 12), ("리셋 질문", 11),
    ("손절선 갱신", 12), ("현재 비중", 10), ("결론", 12),
]

EXIT_FIELDS = [
    "매도일",
    "매도 단가",
    "매도 수량",
    "실현 손익(원)",
    "실현 수익률",
    "보유 기간",
    "A 보류게이트 X 개수",
    "B 강제트리거 O 개수",
    "매도 유형",
    "유형 근거 — 요건이 성립하는가",
    "계획대로였나",
    "이탈 내용",
]

HOLD_COLS = [
    ("날짜", 12), ("그래도 보유하기로 한 이유", 70), ("켜진 B 트리거", 22),
    ("구분", 14), ("재점검 기한", 12),
]

FOLLOW_COLS = [
    ("시점", 10), ("내 매도 판단은 옳았나", 70), ("날짜", 12),
    ("주가", 12), ("매도가 대비", 12),
]
FOLLOW_ROWS = ["D+90", "D+180", "D+365"]

POST_FIELDS = [
    "과정/결과 4분면",
    "배운 것",
    "다음 종목에 적용할 규칙 변경",
]

# 드롭다운
DV_STATUS = '"보유,청산,관찰"'
DV_ASSUM = '"확인,미확인,반증"'
DV_YN = '"예,아니오"'
DV_DRIFT = '"같음,다름"'
DV_RESET = '"산다,안 산다"'
DV_REVIEW_CONC = '"유지,비중조절,회수검토,전량매도"'
DV_EXITTYPE = '"①논지훼손,②목표달성,③교체,④리스크관리,⑤현금필요"'
DV_PLAN = '"계획대로,규칙 이탈"'
DV_HOLDKIND = '"규칙 이탈,사전 정의된 예외"'
DV_QUAD = '"과정O·결과O,과정O·결과X,과정X·결과O(경고),과정X·결과X"'

STAGES = ("진입", "보유점검", "회수", "홀드", "사후추적")


# --------------------------------------------------------------------------
# 저수준 헬퍼
# --------------------------------------------------------------------------
def _anchor(ws, row: int, marker: str) -> None:
    """A열에 섹션 앵커를 심는다 (거의 안 보이는 회색 6pt)."""
    c = ws.cell(row=row, column=1, value=marker)
    c.font = F_ANCHOR


def _section(ws, row: int, title: str, last_col: int = 10) -> None:
    for col in range(2, last_col + 1):
        c = ws.cell(row=row, column=col)
        c.fill = FILL_SECTION
    c = ws.cell(row=row, column=2, value=title)
    c.font = F_SECTION
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[row].height = 22


def _table_header(ws, row: int, cols, start_col: int = 2) -> None:
    for i, (name, width) in enumerate(cols):
        col = start_col + i
        c = ws.cell(row=row, column=col, value=name)
        c.font = F_HEAD
        c.fill = FILL_HEAD
        c.alignment = WRAP_CTR
        c.border = BOX
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[row].height = 26


def _label_value_block(ws, start_row: int, fields, note: str | None = None) -> int:
    """B=라벨 / C=입력칸 세로 블록. 마지막 행 번호를 돌려준다."""
    r = start_row
    for f in fields:
        lab = ws.cell(row=r, column=2, value=f)
        lab.font = F_LABEL
        lab.fill = FILL_BAND
        lab.alignment = WRAP_TOP
        lab.border = BOX
        val = ws.cell(row=r, column=3)
        val.font = F_BODY
        val.alignment = WRAP_TOP
        val.border = BOX
        val.fill = FILL_INPUT
        ws.row_dimensions[r].height = 30
        r += 1
    if note:
        c = ws.cell(row=r, column=2, value=note)
        c.font = F_MUTED
        r += 1
    return r


def _blank_rows(ws, header_row: int, cols, n: int, start_col: int = 2) -> None:
    for i in range(n):
        r = header_row + 1 + i
        for j in range(len(cols)):
            c = ws.cell(row=r, column=start_col + j)
            c.border = BOX
            c.font = F_BODY
            c.alignment = WRAP_TOP
        ws.row_dimensions[r].height = 28


def _add_dv(ws, formula: str, cell_range: str) -> None:
    dv = DataValidation(type="list", formula1=formula, allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.add(cell_range)


def _safe_sheet_name(name: str) -> str:
    bad = set('[]:*?/\\')
    cleaned = "".join(ch for ch in name if ch not in bad).strip()
    return cleaned[:31] or "종목"


def _today() -> str:
    return date.today().isoformat()


def _norm_date(v):
    """문자열/날짜 무엇이 오든 date 로."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------
# 시트 빌더
# --------------------------------------------------------------------------
def build_settings(wb) -> None:
    ws = wb.create_sheet("설정")
    ws.sheet_properties.tabColor = MUTED
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 60

    ws["B2"] = "설정"
    ws["B2"].font = F_TITLE

    rows = [
        ("기준 통화", "KRW", "모든 평가액은 원화로 환산해 집계한다"),
        ("USD/KRW 환율", 1380, "stock-price 실행 시 함께 갱신한다"),
        ("환율 기준일", None, ""),
        ("단일 종목 비중 상한", 0.20, "진입 게이트 5번 판정 기준"),
        ("단일 팩터 비중 상한", 0.40, "분기 포트폴리오 점검용"),
        ("최대 허용 손실 (1종목, 원)", None, "진입 게이트 5번 판정 기준"),
    ]
    r = 4
    for lab, val, memo in rows:
        ws.cell(row=r, column=2, value=lab).font = F_LABEL
        ws.cell(row=r, column=2).fill = FILL_BAND
        ws.cell(row=r, column=2).border = BOX
        c = ws.cell(row=r, column=3, value=val)
        c.font = F_BODY
        c.border = BOX
        c.alignment = LEFT_C
        ws.cell(row=r, column=4, value=memo).font = F_MUTED
        r += 1

    ws["C5"].number_format = FMT_KRW
    ws["C6"].number_format = FMT_DATE
    ws["C7"].number_format = FMT_PCT0
    ws["C8"].number_format = FMT_PCT0
    ws["C9"].number_format = FMT_KRW

    wb.defined_names.add(_defined_name("환율", "설정", "$C$5"))
    wb.defined_names.add(_defined_name("비중상한", "설정", "$C$7"))

    ws["B12"] = "이 파일을 고치는 방법"
    ws["B12"].font = F_LABEL
    for i, line in enumerate([
        "· 수량·평균단가는 [보유종목] 시트에서만 고친다. 나머지 시트는 전부 여기서 파생된 수식이다.",
        "· 주당단가는 [시세기록]에 쌓기만 하면 된다. 가장 마지막 행이 현재가로 잡힌다.",
        "· 종목별 시트의 A열 회색 글자(#ENTRY 등)는 스킬이 기록 위치를 찾는 앵커다. 지우지 말 것.",
        "· 행을 끼워 넣거나 지워도 앵커만 살아 있으면 자동 기록은 계속 동작한다.",
    ]):
        ws.cell(row=13 + i, column=2, value=line).font = F_MUTED


def _defined_name(name, sheet, ref):
    from openpyxl.workbook.defined_name import DefinedName
    return DefinedName(name, attr_text=f"{sheet}!{ref}")


def build_master(wb) -> None:
    ws = wb.create_sheet("보유종목")
    ws.sheet_properties.tabColor = INK
    ws.column_dimensions["A"].width = 3
    ws["B1"] = "보유종목 마스터 — 수량·평균단가는 여기서만 고친다"
    ws["B1"].font = F_TITLE
    ws.row_dimensions[1].height = 26

    _table_header(ws, MASTER_HEAD_ROW, MASTER_COLS)
    ws.freeze_panes = "D3"
    last_col = get_column_letter(1 + len(MASTER_COLS))
    ws.auto_filter.ref = f"B{MASTER_HEAD_ROW}:{last_col}{MASTER_HEAD_ROW}"

    for r in range(MASTER_FIRST_ROW, MASTER_FIRST_ROW + 40):
        _write_master_formulas(ws, r)

    _add_dv(ws, DV_STATUS, f"B{MASTER_FIRST_ROW}:B{MASTER_FIRST_ROW+39}")


def _write_master_formulas(ws, r: int) -> None:
    """마스터 한 행의 서식과 파생 수식."""
    for i in range(len(MASTER_COLS)):
        c = ws.cell(row=r, column=2 + i)
        c.border = BOX
        c.font = F_BODY
        c.alignment = LEFT_C
    ws.row_dimensions[r].height = 20

    # 마스터 열 매핑: B상태 C종목명 D티커 E시장 F통화 G수량 H평균단가 I투자원금
    #                J현재가 K시세기준일 L평가액 M평가손익 N수익률 O비중 P목표비중
    #                Q손절선 R익절목표 S손절까지 T진입일 U최근점검일 V기록시트
    # 시세기록 열 매핑: B날짜 C종목명 D통화 E주당단가 F수량 G환율 H평가액 I입력경로
    name = f"$C{r}"
    fx = "설정!$C$5"
    ws[f"I{r}"] = (f'=IF(OR($G{r}="",$H{r}=""),"",'
                   f'IF($F{r}="USD",$G{r}*$H{r}*{fx},$G{r}*$H{r}))')
    ws[f"J{r}"] = (f'=IFERROR(LOOKUP(2,1/(시세기록!$C$3:$C${MAXR}={name}),'
                   f"시세기록!$E$3:$E${MAXR}),\"\")")
    ws[f"K{r}"] = (f'=IFERROR(LOOKUP(2,1/(시세기록!$C$3:$C${MAXR}={name}),'
                   f"시세기록!$B$3:$B${MAXR}),\"\")")
    ws[f"L{r}"] = (f'=IF(OR($G{r}="",$J{r}=""),"",'
                   f'IF($F{r}="USD",$G{r}*$J{r}*{fx},$G{r}*$J{r}))')
    ws[f"M{r}"] = f'=IF(OR($L{r}="",$I{r}=""),"",$L{r}-$I{r})'
    ws[f"N{r}"] = f'=IFERROR($M{r}/$I{r},"")'
    ws[f"O{r}"] = (f'=IFERROR($L{r}/SUMIF($B$3:$B${MASTER_FIRST_ROW+39},"보유",'
                   f'$L$3:$L${MASTER_FIRST_ROW+39}),"")')
    ws[f"S{r}"] = f'=IFERROR($Q{r}/$J{r}-1,"")'
    ws[f"V{r}"] = f'=IF($C{r}="","",$C{r})'

    ws[f"G{r}"].number_format = "#,##0.####"
    for col in ("H", "J", "Q", "R"):
        ws[f"{col}{r}"].number_format = FMT_PRC
    for col in ("I", "L"):
        ws[f"{col}{r}"].number_format = FMT_KRW
    ws[f"M{r}"].number_format = FMT_PNL
    for col in ("N", "S"):
        ws[f"{col}{r}"].number_format = FMT_PCT
    for col in ("O", "P"):
        ws[f"{col}{r}"].number_format = FMT_PCT0
    for col in ("K", "T", "U"):
        ws[f"{col}{r}"].number_format = FMT_DATE
    for col in ("I", "J", "K", "L", "M", "N", "O", "S", "V"):
        ws[f"{col}{r}"].fill = FILL_CREAM


def build_prices(wb) -> None:
    ws = wb.create_sheet("시세기록")
    ws.sheet_properties.tabColor = ACCENT
    ws.column_dimensions["A"].width = 3
    ws["B1"] = "시세 원장 — 아래로 계속 쌓기만 한다 (stock-price 스킬이 append)"
    ws["B1"].font = F_TITLE
    ws.row_dimensions[1].height = 26

    _table_header(ws, PRICE_HEAD_ROW, PRICE_COLS)
    ws.freeze_panes = "B3"
    last_col = get_column_letter(1 + len(PRICE_COLS))
    ws.auto_filter.ref = f"B{PRICE_HEAD_ROW}:{last_col}{PRICE_HEAD_ROW}"

    for r in range(PRICE_FIRST_ROW, MAXR + 1):
        _write_price_row_format(ws, r)


def _write_price_row_format(ws, r: int) -> None:
    # 열: B날짜 C종목명 D통화 E주당단가 F수량 G환율 H평가액 I입력경로
    for i in range(len(PRICE_COLS)):
        c = ws.cell(row=r, column=2 + i)
        c.border = BOX
        c.font = F_BODY
        c.alignment = LEFT_C
    ws[f"B{r}"].number_format = FMT_DATE
    ws[f"E{r}"].number_format = FMT_PRC
    ws[f"F{r}"].number_format = "#,##0.####"
    ws[f"G{r}"].number_format = FMT_KRW
    ws[f"H{r}"] = (f'=IF(OR($E{r}="",$F{r}=""),"",'
                   f'IF($D{r}="USD",$E{r}*$F{r}*$G{r},$E{r}*$F{r}))')
    ws[f"H{r}"].number_format = FMT_KRW
    ws[f"H{r}"].fill = FILL_CREAM
    ws.row_dimensions[r].height = 18


def build_dashboard(wb) -> None:
    ws = wb.create_sheet("대시보드", 0)
    ws.sheet_properties.tabColor = ACCENT
    ws.column_dimensions["A"].width = 3
    ws.sheet_view.showGridLines = False

    ws["B2"] = "포트폴리오 기록"
    ws["B2"].font = Font(name="맑은 고딕", size=20, bold=True, color=INK)
    ws["B3"] = "수량·평단은 [보유종목], 주당단가는 [시세기록]에 넣는다. 이 시트는 전부 수식이다."
    ws["B3"].font = F_MUTED
    ws.row_dimensions[2].height = 30

    mlast = MASTER_FIRST_ROW + 39
    kpis = [
        ("주식 평가액", f'=SUMIF(보유종목!$B$3:$B${mlast},"보유",보유종목!$L$3:$L${mlast})', FMT_KRW),
        ("보유 현금", f'=IFERROR(LOOKUP(2,1/($B${SNAP_FIRST_ROW}:$B${MAXR}<>""),'
                     f'$D${SNAP_FIRST_ROW}:$D${MAXR}),0)', FMT_KRW),
        ("총자산", "=B5+C5", FMT_KRW),
        ("투자원금", f'=SUMIF(보유종목!$B$3:$B${mlast},"보유",보유종목!$I$3:$I${mlast})', FMT_KRW),
        ("평가손익", "=B5-E5", FMT_PNL),
        ("수익률", '=IFERROR(F5/E5,"")', FMT_PCT),
        ("보유 종목 수", f'=COUNTIF(보유종목!$B$3:$B${mlast},"보유")', "0"),
        ("최근 기록일", f'=IFERROR(LOOKUP(2,1/($B${SNAP_FIRST_ROW}:$B${MAXR}<>""),'
                       f'$B${SNAP_FIRST_ROW}:$B${MAXR}),"")', FMT_DATE),
    ]
    for i, (label, formula, fmt) in enumerate(kpis):
        col = 2 + i
        lc = ws.cell(row=4, column=col, value=label)
        lc.font = F_KPI_LABEL
        lc.fill = FILL_CREAM
        lc.alignment = Alignment(horizontal="center", vertical="center")
        lc.border = BOX
        vc = ws.cell(row=5, column=col, value=formula)
        vc.font = F_KPI_VALUE
        vc.fill = FILL_CREAM
        vc.number_format = fmt
        vc.alignment = Alignment(horizontal="center", vertical="center")
        vc.border = BOX
        ws.column_dimensions[get_column_letter(col)].width = 17
    ws.row_dimensions[4].height = 18
    ws.row_dimensions[5].height = 30
    # 날짜는 13pt 굵게면 폭이 모자라 ####### 이 된다
    ws.cell(row=5, column=1 + len(kpis)).font = Font(
        name="맑은 고딕", size=11, bold=True, color=INK)

    ws["B8"] = "■ 평가액 스냅샷"
    ws["B8"].font = Font(name="맑은 고딕", size=12, bold=True, color=INK)
    ws["B9"] = ("주 2회 stock-price 스킬로 append. 주식평가액은 [시세기록]의 같은 날짜 합계로 자동 계산된다. "
                "보유현금과 입출금만 직접 넣으면 된다.")
    ws["B9"].font = F_MUTED

    _table_header(ws, SNAP_HEAD_ROW, SNAP_COLS)
    for r in range(SNAP_FIRST_ROW, MAXR + 1):
        _write_snapshot_row_format(ws, r)
    ws.freeze_panes = f"B{SNAP_FIRST_ROW}"

    chart = LineChart()
    chart.title = "총자산 추이"
    chart.height = 8.5
    chart.width = 20
    chart.style = 2
    data = Reference(ws, min_col=5, min_row=SNAP_HEAD_ROW, max_row=SNAP_FIRST_ROW + 60)
    cats = Reference(ws, min_col=2, min_row=SNAP_FIRST_ROW, max_row=SNAP_FIRST_ROW + 60)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.y_axis.numFmt = "#,##0"
    ws.add_chart(chart, "M11")


def _write_snapshot_row_format(ws, r: int) -> None:
    # 열: B기록일 C주식평가액 D보유현금 E총자산 F입출금 G순입금누계 H평가손익 I누적수익률 J직전대비 K메모
    for i in range(len(SNAP_COLS)):
        c = ws.cell(row=r, column=2 + i)
        c.border = BOX
        c.font = F_BODY
        c.alignment = LEFT_C
    ws[f"B{r}"].number_format = FMT_DATE
    for col in ("C", "D", "E", "F", "G"):
        ws[f"{col}{r}"].number_format = FMT_KRW
    ws[f"H{r}"].number_format = FMT_PNL
    for col in ("I", "J"):
        ws[f"{col}{r}"].number_format = FMT_PCT
    ws[f"K{r}"].alignment = WRAP_TOP
    ws.row_dimensions[r].height = 18


def snapshot_row_formulas(r: int) -> dict:
    """스냅샷 한 행에 들어갈 파생 수식 (append 시 스크립트가 씀)."""
    return {
        "C": f'=IF($B{r}="","",IFERROR(SUMIFS(시세기록!$H$3:$H${MAXR},'
             f'시세기록!$B$3:$B${MAXR},$B{r}),0))',
        "E": f'=IF($B{r}="","",N($C{r})+N($D{r}))',
        "G": f'=IF($B{r}="","",SUM($F${SNAP_FIRST_ROW}:$F{r}))',
        "H": f'=IF($B{r}="","",$E{r}-$G{r})',
        "I": f'=IFERROR($H{r}/$G{r},"")',
        "J": (f'=IFERROR($E{r}/$E{r-1}-1,"")' if r > SNAP_FIRST_ROW else '=""'),
    }


# --------------------------------------------------------------------------
# 종목 시트
# --------------------------------------------------------------------------
def build_stock_sheet(wb, name: str):
    """종목 기록 시트를 만든다. 이미 있으면 그대로 돌려준다."""
    sname = _safe_sheet_name(name)
    if sname in wb.sheetnames:
        return wb[sname]

    ws = wb.create_sheet(sname)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 72
    for col in "DEFGHIJ":
        ws.column_dimensions[col].width = 13
    ws.column_dimensions["K"].width = 13

    ws["B2"] = name
    ws["B2"].font = F_TITLE
    ws["C2"] = "← 이 셀의 종목명으로 [보유종목] 마스터를 찾는다. 마스터의 종목명과 정확히 같아야 한다."
    ws["C2"].font = F_MUTED
    ws.row_dimensions[2].height = 26

    mlast = MASTER_FIRST_ROW + 39

    def midx(col_letter: str) -> str:
        return (f'=IFERROR(INDEX(보유종목!${col_letter}$3:${col_letter}${mlast},'
                f'MATCH($B$2,보유종목!$C$3:$C${mlast},0)),"")')

    r = 4
    _anchor(ws, r, "#SUMMARY")
    _section(ws, r, "요약 — [보유종목] 마스터에서 자동")
    r += 1
    summary = [
        ("상태", midx("B"), None),
        ("수량", midx("G"), "#,##0.####"),
        ("평균단가", midx("H"), FMT_PRC),
        ("현재가", midx("J"), FMT_PRC),
        ("평가액(원)", midx("L"), FMT_KRW),
        ("평가손익(원)", midx("M"), FMT_PNL),
        ("수익률", midx("N"), FMT_PCT),
        ("비중", midx("O"), FMT_PCT0),
        ("진입일", midx("T"), FMT_DATE),
        ("최근 점검일", midx("U"), FMT_DATE),
    ]
    for lab, formula, fmt in summary:
        lc = ws.cell(row=r, column=2, value=lab)
        lc.font = F_LABEL
        lc.fill = FILL_BAND
        lc.border = BOX
        vc = ws.cell(row=r, column=3, value=formula)
        vc.font = F_BODY
        vc.border = BOX
        vc.fill = FILL_CREAM
        vc.alignment = LEFT_C
        if fmt:
            vc.number_format = fmt
        ws.row_dimensions[r].height = 18
        r += 1

    r += 1
    _anchor(ws, r, "#ENTRY")
    _section(ws, r, "① 진입 기록 — 매수 주문 전에 작성. 체결 후 수정 금지(추가만)")
    r += 1
    r = _label_value_block(ws, r, ENTRY_FIELDS)

    r += 1
    _anchor(ws, r, "#REVIEW")
    _section(ws, r, "② 보유 점검 — 분기 1회 + 이벤트 발생 시 (아래로 누적)")
    r += 1
    hdr = r
    _table_header(ws, hdr, REVIEW_COLS)
    _blank_rows(ws, hdr, REVIEW_COLS, 12)
    _add_dv(ws, DV_ASSUM, f"D{hdr+1}:F{hdr+12}")
    _add_dv(ws, DV_DRIFT, f"G{hdr+1}:G{hdr+12}")
    _add_dv(ws, DV_RESET, f"H{hdr+1}:H{hdr+12}")
    _add_dv(ws, DV_REVIEW_CONC, f"K{hdr+1}:K{hdr+12}")
    for rr in range(hdr + 1, hdr + 13):
        ws[f"B{rr}"].number_format = FMT_DATE
        ws[f"J{rr}"].number_format = FMT_PCT0
    r = hdr + 13

    r += 1
    _anchor(ws, r, "#EXIT")
    _section(ws, r, "③ 회수 — A 보류게이트 7 / B 강제트리거 6 통과 후 작성")
    r += 1
    exit_start = r
    r = _label_value_block(ws, r, EXIT_FIELDS)
    ws[f"C{exit_start}"].number_format = FMT_DATE
    ws[f"C{exit_start+1}"].number_format = FMT_PRC
    ws[f"C{exit_start+3}"].number_format = FMT_PNL
    ws[f"C{exit_start+4}"].number_format = FMT_PCT
    _add_dv(ws, DV_EXITTYPE, f"C{exit_start+8}")
    _add_dv(ws, DV_PLAN, f"C{exit_start+10}")

    r += 1
    _anchor(ws, r, "#HOLD")
    _section(ws, r, "③-E 홀드 기록 — B 트리거가 켜졌는데 팔지 않은 경우 (반드시 기록)")
    r += 1
    hdr = r
    _table_header(ws, hdr, HOLD_COLS)
    _blank_rows(ws, hdr, HOLD_COLS, 6)
    _add_dv(ws, DV_HOLDKIND, f"E{hdr+1}:E{hdr+6}")
    for rr in range(hdr + 1, hdr + 7):
        ws[f"B{rr}"].number_format = FMT_DATE
        ws[f"F{rr}"].number_format = FMT_DATE
    r = hdr + 7

    r += 1
    _anchor(ws, r, "#FOLLOW")
    _section(ws, r, "④ 사후 추적 — 매도 후에도 닫지 않는다")
    r += 1
    hdr = r
    _table_header(ws, hdr, FOLLOW_COLS)
    _blank_rows(ws, hdr, FOLLOW_COLS, 3)
    for i, lab in enumerate(FOLLOW_ROWS):
        ws.cell(row=hdr + 1 + i, column=2, value=lab).font = F_LABEL
        ws[f"D{hdr+1+i}"].number_format = FMT_DATE
        ws[f"E{hdr+1+i}"].number_format = FMT_PRC
        ws[f"F{hdr+1+i}"].number_format = FMT_PCT
    r = hdr + 4

    r += 1
    _anchor(ws, r, "#POST")
    _section(ws, r, "④-B 사후 평가")
    r += 1
    post_start = r
    r = _label_value_block(ws, r, POST_FIELDS)
    _add_dv(ws, DV_QUAD, f"C{post_start}")

    _anchor(ws, r + 1, "#END")
    return ws


# --------------------------------------------------------------------------
# 워크북 생성
# --------------------------------------------------------------------------
def build_workbook(path: str, holdings: list[dict] | None = None) -> str:
    wb = Workbook()
    wb.remove(wb.active)

    build_dashboard(wb)
    build_master(wb)
    build_prices(wb)
    build_settings(wb)

    holdings = holdings or []
    ws = wb["보유종목"]
    for i, h in enumerate(holdings):
        r = MASTER_FIRST_ROW + i
        ws[f"B{r}"] = h.get("상태", "보유")
        ws[f"C{r}"] = h["종목명"]
        ws[f"D{r}"] = h.get("티커", "")
        ws[f"E{r}"] = h.get("시장", "")
        ws[f"F{r}"] = h.get("통화", "KRW")
        ws[f"G{r}"] = h.get("수량")
        ws[f"H{r}"] = h.get("평균단가")
        build_stock_sheet(wb, h["종목명"])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    return path


# --------------------------------------------------------------------------
# 조회 / 기록 API
# --------------------------------------------------------------------------
def open_wb(path: str = None):
    return load_workbook(path or DEFAULT_WB_PATH)


def read_holdings(path: str = None, only_active: bool = True) -> list[dict]:
    """마스터에서 종목 목록을 읽는다 (수식이 아닌 원시 입력값만)."""
    wb = load_workbook(path or DEFAULT_WB_PATH, data_only=False)
    ws = wb["보유종목"]
    out = []
    for r in range(MASTER_FIRST_ROW, MASTER_FIRST_ROW + 40):
        name = ws[f"C{r}"].value
        if not name:
            continue
        status = ws[f"B{r}"].value or "보유"
        if only_active and status != "보유":
            continue
        out.append({
            "row": r,
            "상태": status,
            "종목명": name,
            "티커": ws[f"D{r}"].value,
            "시장": ws[f"E{r}"].value,
            "통화": ws[f"F{r}"].value or "KRW",
            "수량": ws[f"G{r}"].value,
            "평균단가": ws[f"H{r}"].value,
        })
    return out


def get_setting(wb, key_row: int):
    return wb["설정"].cell(row=key_row, column=3).value


def find_anchor(ws, marker: str) -> int | None:
    for r in range(1, ws.max_row + 2):
        if ws.cell(row=r, column=1).value == marker:
            return r
    return None


def first_empty_row(ws, header_row: int, key_col: int = 2, limit: int = 400) -> int:
    r = header_row + 1
    while r < header_row + limit:
        if ws.cell(row=r, column=key_col).value in (None, ""):
            return r
        r += 1
    return r


def _ensure_row_style(ws, row: int, cols, start_col: int = 2) -> None:
    for j in range(len(cols)):
        c = ws.cell(row=row, column=start_col + j)
        if c.border is None or c.border.left.style is None:
            c.border = BOX
        c.font = F_BODY
        c.alignment = WRAP_TOP


def write_entry(ws, data: dict) -> list[str]:
    """진입 블록: 라벨 매칭으로 C열에 채운다."""
    start = find_anchor(ws, "#ENTRY")
    if start is None:
        raise RuntimeError("#ENTRY 앵커를 찾지 못했다")
    written = []
    r = start + 1
    for _ in range(len(ENTRY_FIELDS) + 6):
        label = ws.cell(row=r, column=2).value
        if label in data and data[label] not in (None, ""):
            val = data[label]
            if label == "기록일":
                val = _norm_date(val) or val
            ws.cell(row=r, column=3, value=val)
            written.append(label)
        r += 1
        if ws.cell(row=r, column=1).value and str(ws.cell(row=r, column=1).value).startswith("#"):
            break
    return written


def write_exit(ws, data: dict) -> list[str]:
    start = find_anchor(ws, "#EXIT")
    if start is None:
        raise RuntimeError("#EXIT 앵커를 찾지 못했다")
    written = []
    r = start + 1
    for _ in range(len(EXIT_FIELDS) + 6):
        label = ws.cell(row=r, column=2).value
        if label in data and data[label] not in (None, ""):
            val = data[label]
            if label == "매도일":
                val = _norm_date(val) or val
            ws.cell(row=r, column=3, value=val)
            written.append(label)
        r += 1
        if ws.cell(row=r, column=1).value and str(ws.cell(row=r, column=1).value).startswith("#"):
            break
    return written


def append_review(ws, data: dict) -> int:
    hdr = find_anchor(ws, "#REVIEW")
    if hdr is None:
        raise RuntimeError("#REVIEW 앵커를 찾지 못했다")
    hdr += 1
    row = first_empty_row(ws, hdr)
    _ensure_row_style(ws, row, REVIEW_COLS)
    order = ["점검일", "점검 요약", "가정1", "가정2", "가정3",
             "논지 드리프트", "리셋 질문", "손절선 갱신", "현재 비중", "결론"]
    for j, key in enumerate(order):
        v = data.get(key)
        if key == "점검일":
            v = _norm_date(v) or v
        ws.cell(row=row, column=2 + j, value=v)
    ws.cell(row=row, column=2).number_format = FMT_DATE
    ws.cell(row=row, column=10).number_format = FMT_PCT0
    ws.cell(row=row, column=3).alignment = WRAP_TOP
    ws.row_dimensions[row].height = 40
    return row


def append_hold(ws, data: dict) -> int:
    hdr = find_anchor(ws, "#HOLD")
    if hdr is None:
        raise RuntimeError("#HOLD 앵커를 찾지 못했다")
    hdr += 1
    row = first_empty_row(ws, hdr)
    _ensure_row_style(ws, row, HOLD_COLS)
    order = ["날짜", "보유 이유", "켜진 B 트리거", "구분", "재점검 기한"]
    for j, key in enumerate(order):
        v = data.get(key)
        if key in ("날짜", "재점검 기한"):
            v = _norm_date(v) or v
        ws.cell(row=row, column=2 + j, value=v)
    ws.cell(row=row, column=2).number_format = FMT_DATE
    ws.cell(row=row, column=6).number_format = FMT_DATE
    ws.row_dimensions[row].height = 40
    return row


def append_follow(ws, data: dict) -> int:
    """사후추적: 시점(D+90 등) 행을 찾아 채운다. 없으면 새 행."""
    hdr = find_anchor(ws, "#FOLLOW")
    if hdr is None:
        raise RuntimeError("#FOLLOW 앵커를 찾지 못했다")
    hdr += 1
    target = str(data.get("시점", "")).strip()
    row = None
    for r in range(hdr + 1, hdr + 10):
        v = ws.cell(row=r, column=2).value
        if v is None:
            row = row or r
            break
        if str(v).strip() == target:
            row = r
            break
    if row is None:
        row = first_empty_row(ws, hdr)
    _ensure_row_style(ws, row, FOLLOW_COLS)
    ws.cell(row=row, column=2, value=target or ws.cell(row=row, column=2).value)
    ws.cell(row=row, column=3, value=data.get("판단 평가"))
    ws.cell(row=row, column=4, value=_norm_date(data.get("날짜")) or data.get("날짜"))
    ws.cell(row=row, column=5, value=data.get("주가"))
    ws.cell(row=row, column=6, value=data.get("매도가 대비"))
    ws.cell(row=row, column=4).number_format = FMT_DATE
    ws.cell(row=row, column=5).number_format = FMT_PRC
    ws.cell(row=row, column=6).number_format = FMT_PCT
    ws.cell(row=row, column=3).alignment = WRAP_TOP
    ws.row_dimensions[row].height = 40

    post = find_anchor(ws, "#POST")
    if post is not None:
        pr = post + 1
        for key in POST_FIELDS:
            label = ws.cell(row=pr, column=2).value
            if label in data and data[label] not in (None, ""):
                ws.cell(row=pr, column=3, value=data[label])
            pr += 1
    return row


def touch_master(ws_master, name: str, **fields) -> None:
    """마스터의 해당 종목 행 갱신 (진입일·최근점검일·상태·손절선 등)."""
    col_of = {
        "상태": "B", "티커": "D", "시장": "E", "통화": "F", "수량": "G",
        "평균단가": "H", "목표비중": "P", "손절선": "Q", "익절목표": "R",
        "진입일": "T", "최근점검일": "U",
    }
    for r in range(MASTER_FIRST_ROW, MASTER_FIRST_ROW + 40):
        if ws_master[f"C{r}"].value == name:
            for k, v in fields.items():
                if v in (None, "") or k not in col_of:
                    continue
                if k in ("진입일", "최근점검일"):
                    v = _norm_date(v) or v
                ws_master[f"{col_of[k]}{r}"] = v
            return
    # 없으면 새 행
    for r in range(MASTER_FIRST_ROW, MASTER_FIRST_ROW + 40):
        if not ws_master[f"C{r}"].value:
            ws_master[f"B{r}"] = fields.get("상태", "보유")
            ws_master[f"C{r}"] = name
            for k, v in fields.items():
                if v in (None, "") or k not in col_of:
                    continue
                if k in ("진입일", "최근점검일"):
                    v = _norm_date(v) or v
                ws_master[f"{col_of[k]}{r}"] = v
            return
    raise RuntimeError("마스터에 빈 행이 없다 — 행을 늘려야 한다")
