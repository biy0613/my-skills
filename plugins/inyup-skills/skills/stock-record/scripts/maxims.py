# -*- coding: utf-8 -*-
"""원장의 [격언] 시트를 읽어 단계·게이트에 맞는 격언을 돌려준다.

**격언 본문은 이 저장소에 두지 않는다.** 이 스킬 폴더는 공개 저장소이고,
격언과 그 '위반 신호'는 사용자 개인의 판단 습관이다. 유일한 소스는
`포트폴리오기록.xlsx` 의 [격언] 시트다. 여기서는 읽기만 한다.

시트가 없거나 비어 있으면 조용히 빈 목록을 돌려준다 —
격언을 안 쓰는 워크북에서도 기록 자체는 그대로 동작해야 하기 때문이다.

시트 구조 (A열 앵커로 위치를 찾는다)
  #MAXIM   ① 격언 원장   B ID / C 주제 / D 격언 / E 뜻 / F 위반 신호 /
                          G 연결 설명 / H 출처 / I 원문 / J 적용 단계 / K 게이트 코드 / L 등록일
  #INVOKE  ② 제지 기록   B 일시 / C 격언 ID / D 하려던 행동 / E 짚은 것 / F 결정 / G 결과
  #SOURCE  ③ 원문 보관

게이트 코드: E1~E6 진입 하드게이트 / A1~A7 회수 A / B1~B6 회수 B / T1~T6 매도 유형
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import portfolio as P  # noqa: E402

SHEET = "격언"
A_MAXIM, A_INVOKE = "#MAXIM", "#INVOKE"

# B열부터의 열 번호
COL = {"id": 2, "topic": 3, "line": 4, "mean": 5, "signal": 6, "gate": 7,
       "src": 8, "quote": 9, "stages": 10, "codes": 11, "date": 12}

INVOKE_COLS = ["일시", "격언 ID", "내가 하려던 행동", "Claude가 짚은 것",
               "내 결정과 이유", "결과·복기"]

STAGE_GATE_PREFIX = {"진입": "E", "회수": ("A", "B", "T"), "홀드": ("B", "T"),
                     "보유점검": ("E", "A", "B"), "사후추적": "T"}


def _txt(v) -> str:
    return "" if v is None else str(v).strip()


def _split(v) -> list[str]:
    """콤마·슬래시로 나눈다. '—' 는 '해당 없음' 표시이므로 버린다."""
    out = []
    for part in _txt(v).replace("/", ",").split(","):
        part = part.strip()
        if part and part not in ("—", "-", "없음"):
            out.append(part)
    return out


def load(wb) -> list[dict]:
    """[격언] 시트를 읽어 목록으로 돌려준다. 시트가 없으면 []."""
    if SHEET not in wb.sheetnames:
        return []
    ws = wb[SHEET]
    start = P.find_anchor(ws, A_MAXIM)
    if start is None:
        return []
    stop = P.find_anchor(ws, A_INVOKE) or ws.max_row + 1

    items = []
    for r in range(start + 2, stop):          # 앵커행 + 헤더행 다음부터
        mid = _txt(ws.cell(row=r, column=COL["id"]).value)
        if not mid:
            continue
        items.append({
            "ID": mid,
            "주제": _txt(ws.cell(row=r, column=COL["topic"]).value),
            "격언": _txt(ws.cell(row=r, column=COL["line"]).value),
            "뜻": _txt(ws.cell(row=r, column=COL["mean"]).value),
            "위반신호": _txt(ws.cell(row=r, column=COL["signal"]).value),
            "연결": _txt(ws.cell(row=r, column=COL["gate"]).value),
            "출처": _txt(ws.cell(row=r, column=COL["src"]).value),
            "원문": _txt(ws.cell(row=r, column=COL["quote"]).value),
            "단계": _split(ws.cell(row=r, column=COL["stages"]).value),
            "코드": [c.upper() for c in _split(ws.cell(row=r, column=COL["codes"]).value)],
            "행": r,
        })
    return items


def for_stage(items, stage: str) -> list[dict]:
    return [m for m in items if stage in m["단계"]]


def for_gate(items, code: str) -> list[dict]:
    code = code.upper().strip()
    return [m for m in items if code in m["코드"]]


def gate_map(items, codes) -> dict:
    """['E1'..'E6'] 같은 코드 목록 → {코드: [격언ID, ...]}."""
    return {c: [m["ID"] for m in for_gate(items, c)] for c in codes}


def render(items, stage: str | None = None, full: bool = True) -> str:
    """사용자에게 그대로 붙여넣을 블록. 격언이 없으면 빈 문자열."""
    sel = for_stage(items, stage) if stage else items
    if not sel:
        return ""
    head = f"■ 이 단계에서 지킬 격언 — [격언] 시트 ({stage})" if stage else "■ 격언"
    out = [head, ""]
    for m in sel:
        tag = ("  ·  ".join(m["코드"])) if m["코드"] else "게이트 연결 없음"
        out.append(f"[{m['ID']}] {m['격언']}")
        out.append(f"        └ {tag}   |   {m['출처']}")
        if full:
            if m["원문"]:
                out.append(f"        “{m['원문']}”")
            if m["위반신호"]:
                sig = m["위반신호"].replace("\n", "\n           ")
                out.append(f"        ▸ 어길 때 나오는 말·행동:\n           {sig}")
        out.append("")
    return "\n".join(out).rstrip()


def render_for_gate(items, code: str) -> str:
    """게이트 문항 한 줄 뒤에 붙일 짧은 꼬리표."""
    sel = for_gate(items, code)
    if not sel:
        return ""
    return "   ← " + " / ".join(f"[{m['ID']}] {m['격언']}" for m in sel)


def append_invoke(wb, 일시: str, 격언ID: str, 행동: str,
                   짚은것: str = "", 결정: str = "", 결과: str = "") -> int:
    """② 제지 기록에 한 줄 추가하고 그 행 번호를 돌려준다."""
    if SHEET not in wb.sheetnames:
        raise KeyError(f"[{SHEET}] 시트가 없다. 먼저 격언 시트를 만들어야 한다.")
    ws = wb[SHEET]
    anchor = P.find_anchor(ws, A_INVOKE)
    if anchor is None:
        raise KeyError(f"[{SHEET}] 시트에 {A_INVOKE} 앵커가 없다.")
    header = anchor + 1
    r = P.first_empty_row(ws, header, key_col=2)
    for j, v in enumerate([일시, 격언ID, 행동, 짚은것, 결정, 결과]):
        c = ws.cell(row=r, column=2 + j, value=v)
        c.font = P.F_BODY
        c.alignment = P.WRAP_TOP
        if c.border is None or c.border.left.style is None:
            c.border = P.BOX
    if ws.row_dimensions[r].height in (None, 0):
        ws.row_dimensions[r].height = 32
    return r
