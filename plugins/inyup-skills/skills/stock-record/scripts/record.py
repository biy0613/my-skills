# -*- coding: utf-8 -*-
"""종목 기록을 포트폴리오기록.xlsx 에 쓴다.

사용법
  # 단계별 입력 필드 목록 확인
  python record.py --fields 진입

  # 기록 (JSON 파일 경로 또는 stdin)
  python record.py --input payload.json
  echo '{...}' | python record.py

payload 형식 (종목·수치는 전부 가상 예시)
{
  "종목명": "ACME",
  "단계": "진입",                       # 진입 | 보유점검 | 회수 | 홀드 | 사후추적
  "마스터": {                            # 선택 — 있으면 [보유종목] 마스터도 갱신
    "티커": "ACME", "시장": "NASDAQ", "통화": "USD",
    "수량": 10, "평균단가": 50.0,
    "진입일": "2026-01-01", "목표비중": 0.05,
    "손절선": 35, "익절목표": 80
  },
  "데이터": { "핵심 논지 (한 문장)": "...", ... }
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maxims as MX  # noqa: E402
import portfolio as P  # noqa: E402

REVIEW_FIELDS = ["점검일", "점검 요약", "가정1", "가정2", "가정3",
                 "근거 변경 유무", "현가 매수 의중", "손절선 갱신", "현재 비중", "결론"]
HOLD_FIELDS = ["날짜", "보유 이유", "켜진 B 트리거", "구분", "재점검 기한"]
FOLLOW_FIELDS = ["시점", "날짜", "주가", "매도가 대비", "판단 평가"] + P.POST_FIELDS

FIELDS = {
    "진입": P.ENTRY_FIELDS,
    "보유점검": REVIEW_FIELDS,
    "회수": P.EXIT_FIELDS,
    "홀드": HOLD_FIELDS,
    "사후추적": FOLLOW_FIELDS,
}

MASTER_FIELDS = ["상태", "티커", "시장", "통화", "수량", "평균단가",
                 "목표비중", "손절선", "익절목표", "진입일", "최근점검일"]

GATE_CODES = ([f"E{i}" for i in range(1, 7)] + [f"A{i}" for i in range(1, 8)]
              + [f"B{i}" for i in range(1, 7)] + [f"T{i}" for i in range(1, 7)])


def _load_maxims(path):
    """[격언] 시트를 읽는다. 없거나 못 읽으면 조용히 빈 목록 — 기록은 계속돼야 한다."""
    try:
        return MX.load(P.open_wb(path))
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="payload JSON 파일 경로 (생략 시 stdin)")
    ap.add_argument("--fields", choices=list(FIELDS), help="단계별 입력 필드 목록만 출력")
    ap.add_argument("--gates", action="store_true",
                    help="게이트·트리거·매도유형 문항 전문 출력 (사용자에게 그대로 읽어줄 것)")
    ap.add_argument("--template", action="store_true",
                    help="해당 종목·단계에서 채워야 할 엑셀 자리를 폼으로 출력")
    ap.add_argument("--questions", action="store_true",
                    help="사용자가 바로 답할 수 있는 질문 목록으로 출력 (게이트 판정 이후 단계)")
    ap.add_argument("--maxims", action="store_true",
                    help="[격언] 시트에서 해당 단계·게이트의 격언을 출력 (사용자에게 그대로 붙여넣을 것)")
    ap.add_argument("--gate", help="--maxims 용 게이트 코드 (E1~E6 / A1~A7 / B1~B6 / T1~T6)")
    ap.add_argument("--invoke", action="store_true",
                    help="② 제지 기록에 한 줄 추가 (payload는 --input 또는 stdin)")
    ap.add_argument("--stock", help="--template 용 종목명")
    ap.add_argument("--stage", choices=list(FIELDS), help="--template 용 단계")
    ap.add_argument("--workbook", default=P.DEFAULT_WB_PATH)
    args = ap.parse_args()

    if args.maxims:
        items = _load_maxims(args.workbook)
        if not items:
            print("[격언] 시트가 없거나 비어 있다. 격언 없이 진행한다.")
            return 0
        if args.gate:
            sel = MX.for_gate(items, args.gate)
            print(MX.render(sel, None) if sel
                  else f"{args.gate} 에 연결된 격언 없음")
            return 0
        print(MX.render(items, args.stage))
        return 0

    if args.invoke:
        raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
        pl = json.loads(raw)
        wb = P.open_wb(args.workbook)
        row = MX.append_invoke(
            wb,
            일시=pl.get("일시") or "",
            격언ID=pl.get("격언ID") or pl.get("격언 ID") or "",
            행동=pl.get("행동") or pl.get("내가 하려던 행동") or "",
            짚은것=pl.get("짚은것") or pl.get("Claude가 짚은 것") or "",
            결정=pl.get("결정") or pl.get("내 결정과 이유") or "",
            결과=pl.get("결과") or pl.get("결과·복기") or "",
        )
        wb.save(args.workbook)
        print(json.dumps({"결과": "제지 기록 완료", "시트": "격언",
                          "위치": f"② 제지 기록 {row}행", "파일": args.workbook},
                         ensure_ascii=False, indent=2))
        return 0

    if args.template or args.questions:
        mode = "questions" if args.questions else "template"
        if not args.stock or not args.stage:
            print(f"오류: --{mode} 에는 --stock 과 --stage 가 필요하다.", file=sys.stderr)
            return 2
        wb = P.open_wb(args.workbook)
        sname = P._safe_sheet_name(args.stock)
        if sname not in wb.sheetnames:
            # 시트가 없으면 만들어 두고(저장은 하지 않음) 동일한 폼을 낸다
            ws = P.build_stock_sheet(wb, args.stock)
        else:
            ws = wb[sname]
        print(P.render_questions(ws, args.stage, args.stock) if args.questions
              else P.render_template(ws, args.stage, args.stock))
        return 0

    if args.gates:
        items = _load_maxims(args.workbook)
        out = {
            "진입 하드게이트 6": P.ENTRY_GATES,
            "회수 A 보류게이트 7": P.EXIT_GATES_A,
            "회수 B 강제트리거 6": P.EXIT_TRIGGERS_B,
            "매도 유형 6": {k: v for k, v in P.EXIT_TYPES},
        }
        if items:
            # 문항 번호에 걸린 격언. 문항을 띄울 때 해당 격언도 함께 읽어준다.
            out["격언_연결"] = {c: [f"{m['ID']} — {m['격언']}" for m in MX.for_gate(items, c)]
                              for c in GATE_CODES if MX.for_gate(items, c)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.fields:
        print(json.dumps({"단계": args.fields,
                          "데이터_필드": FIELDS[args.fields],
                          "마스터_필드": MASTER_FIELDS},
                         ensure_ascii=False, indent=2))
        return 0

    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    payload = json.loads(raw)

    name = payload.get("종목명")
    stage = payload.get("단계")
    if not name or stage not in FIELDS:
        print(f"오류: 종목명과 단계가 필요하다. 단계는 {list(FIELDS)} 중 하나.", file=sys.stderr)
        return 2

    data = payload.get("데이터") or {}
    master = payload.get("마스터") or {}

    if not os.path.exists(args.workbook):
        print(f"오류: 워크북이 없다 — {args.workbook}", file=sys.stderr)
        return 2

    wb = P.open_wb(args.workbook)
    ws = P.build_stock_sheet(wb, name)          # 없으면 새로 만든다
    wsm = wb["보유종목"]

    # 진입 기록은 체결 후 수정 금지가 원칙이다. 이미 있으면 명시적 동의 없이 덮지 않는다.
    if stage == "진입" and not payload.get("덮어쓰기"):
        e = P.find_anchor(ws, "#ENTRY")
        prev = ws.cell(row=e + 1, column=3).value if e else None
        if prev not in (None, ""):
            print(json.dumps({
                "결과": "거부",
                "이유": "이 종목의 진입 기록이 이미 있다. 체결 후 수정 금지 규칙에 따라 덮어쓰지 않는다.",
                "기존 기록일": str(prev),
                "대안": "생각이 바뀐 것이면 '보유점검'으로 남겨라. 정말 고쳐야 하면 payload에 \"덮어쓰기\": true 를 넣어라.",
            }, ensure_ascii=False, indent=2))
            return 3

    # --- 마스터 갱신 -------------------------------------------------------
    mfields = dict(master)
    if stage == "진입":
        mfields.setdefault("상태", "보유")
        if data.get("기록일") and not mfields.get("진입일"):
            mfields["진입일"] = data["기록일"]
    elif stage == "보유점검" and data.get("점검일"):
        mfields["최근점검일"] = data["점검일"]
    elif stage == "회수":
        # 부분 매도가 훨씬 흔하다. 수량이 남았는데 '청산'으로 찍으면 그 종목이
        # 평가액·비중 집계에서 통째로 빠져 총자산이 틀어진다.
        # 상태는 touch_master 이후 **최종 수량**을 보고 정한다 —
        # 마스터를 먼저 갱신했는지 나중에 갱신했는지에 흔들리지 않게 하기 위함이다.
        pass
    P.touch_master(wsm, name, **mfields)

    if stage == "회수" and "상태" not in mfields:
        # 최종 수량이 0(또는 비어 있음)일 때만 청산. 남아 있으면 부분 매도다.
        for r in range(P.MASTER_FIRST_ROW, P.MASTER_FIRST_ROW + 40):
            if wsm.cell(row=r, column=3).value == name:
                q = wsm.cell(row=r, column=7).value
                wsm.cell(row=r, column=2,
                         value="청산" if q in (None, 0) else "보유")
                break

    # 알림설정 동기화 — 여기서 안 하면 종목 시트와 알림 판정 기준이 갈라진다
    synced = P.sync_alert_levels(wb, name, **{
        k: master.get(k) for k in ("손절선", "익절1", "익절2", "추가매수")
        if master.get(k) is not None})
    if master.get("익절목표") is not None and "익절1" not in master:
        synced.update(P.sync_alert_levels(wb, name, 익절1=master["익절목표"]))

    # --- 기록 --------------------------------------------------------------
    written_row = None            # 표 단계에서 실제로 기록된 행
    if stage == "진입":
        done = P.write_entry(ws, data)
        where = "① 진입 기록"
    elif stage == "보유점검":
        written_row = P.append_review(ws, data)
        done = [k for k in REVIEW_FIELDS if data.get(k) not in (None, "")]
        where = f"② 보유 점검 {written_row}행"
    elif stage == "회수":
        done = P.write_exit(ws, data)
        where = "③ 회수"
    elif stage == "홀드":
        written_row = P.append_hold(ws, data)
        done = [k for k in HOLD_FIELDS if data.get(k) not in (None, "")]
        where = f"③-E 홀드 기록 {written_row}행"
    else:
        written_row = P.append_follow(ws, data)
        done = [k for k in FOLLOW_FIELDS if data.get(k) not in (None, "")]
        where = f"④ 사후 추적 {written_row}행"

    wb.save(args.workbook)

    # 빈 항목은 이번 payload가 아니라 **시트의 실제 상태**로 판정한다.
    # payload 기준으로 세면 부분 갱신 때 이미 채워진 칸까지 비었다고 보고하게 된다.
    missing = [x["필드"] for x in P.block_status(ws, stage, row=written_row)
               if x["값"] in (None, "")]
    try:
        maxim_note = [f"{m['ID']} — {m['격언']}" for m in MX.for_stage(MX.load(wb), stage)]
    except Exception:
        maxim_note = []
    result = {
        "결과": "기록 완료",
        "종목": name,
        "단계": stage,
        "시트": ws.title,
        "위치": where,
        "이번에_쓴_항목수": len(done),
        "알림설정_동기화": {k: f"{v[0]} → {v[1]}" for k, v in synced.items()} or "변경 없음",
        "시트에_남은_빈_항목": missing,
        "파일": args.workbook,
    }
    if maxim_note:
        result["이_단계의_격언"] = maxim_note
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
