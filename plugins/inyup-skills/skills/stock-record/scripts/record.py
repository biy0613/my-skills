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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="payload JSON 파일 경로 (생략 시 stdin)")
    ap.add_argument("--fields", choices=list(FIELDS), help="단계별 입력 필드 목록만 출력")
    ap.add_argument("--gates", action="store_true",
                    help="게이트·트리거·매도유형 문항 전문 출력 (사용자에게 그대로 읽어줄 것)")
    ap.add_argument("--workbook", default=P.DEFAULT_WB_PATH)
    args = ap.parse_args()

    if args.gates:
        print(json.dumps({
            "진입 하드게이트 6": P.ENTRY_GATES,
            "회수 A 보류게이트 7": P.EXIT_GATES_A,
            "회수 B 강제트리거 6": P.EXIT_TRIGGERS_B,
            "매도 유형 5": {k: v for k, v in P.EXIT_TYPES},
        }, ensure_ascii=False, indent=2))
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
        mfields.setdefault("상태", "청산")
    P.touch_master(wsm, name, **mfields)

    # --- 기록 --------------------------------------------------------------
    if stage == "진입":
        done = P.write_entry(ws, data)
        where = "① 진입 기록"
    elif stage == "보유점검":
        row = P.append_review(ws, data)
        done = [k for k in REVIEW_FIELDS if data.get(k) not in (None, "")]
        where = f"② 보유 점검 {row}행"
    elif stage == "회수":
        done = P.write_exit(ws, data)
        where = "③ 회수"
    elif stage == "홀드":
        row = P.append_hold(ws, data)
        done = [k for k in HOLD_FIELDS if data.get(k) not in (None, "")]
        where = f"③-E 홀드 기록 {row}행"
    else:
        row = P.append_follow(ws, data)
        done = [k for k in FOLLOW_FIELDS if data.get(k) not in (None, "")]
        where = f"④ 사후 추적 {row}행"

    wb.save(args.workbook)

    missing = [f for f in FIELDS[stage] if f not in done]
    print(json.dumps({
        "결과": "기록 완료",
        "종목": name,
        "단계": stage,
        "시트": ws.title,
        "위치": where,
        "기록된_항목수": len(done),
        "빈_항목": missing,
        "파일": args.workbook,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
