# -*- coding: utf-8 -*-
"""보유 종목 주당단가를 받아 [시세기록]에 쌓고 [대시보드] 스냅샷을 갱신한다.

사용법
  # 1) 지금 무엇을 입력해야 하는지 확인 (보유 종목 + 직전 시세)
  python update_prices.py --list

  # 2) 반영
  python update_prices.py --input snapshot.json

snapshot.json 형식
{
  "날짜": "2026-08-02",
  "환율": 1385,                       # USD/KRW. 생략하면 설정 시트의 기존 값 사용
  "보유현금": 5000000,
  "입출금": 0,                        # 이번 회차 신규 입금(+) / 출금(-)
  "메모": "",
  "시세": { "가나전자": 102000, "ACME": 51.0, ... }      # 현지통화 주당단가 (예시는 가상 값)
}

같은 날짜로 다시 실행하면 덮어쓴다 (중복 행이 생기지 않는다).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.normpath(os.path.join(_HERE, "..", "..", "stock-record", "scripts"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

try:
    import portfolio as P
except ImportError:
    print(f"오류: 공용 라이브러리를 찾지 못했다 — {_LIB}\\portfolio.py\n"
          "stock-record 스킬이 함께 설치돼 있어야 한다.", file=sys.stderr)
    raise

FX_ROW = 5          # 설정 시트 USD/KRW 환율
FX_DATE_ROW = 6     # 설정 시트 환율 기준일


def _fx(wb) -> float:
    v = wb["설정"].cell(row=FX_ROW, column=3).value
    return float(v) if v else 1.0


def cmd_list(wb, path: str) -> int:
    ws = wb["시세기록"]
    last = {}
    for r in range(P.PRICE_FIRST_ROW, P.MAXR + 1):
        nm = ws.cell(row=r, column=3).value
        if nm:
            last[nm] = {"날짜": str(P._norm_date(ws.cell(row=r, column=2).value) or ""),
                        "주당단가": ws.cell(row=r, column=5).value}

    rows = []
    for h in P.read_holdings(path, only_active=True):
        prev = last.get(h["종목명"], {})
        rows.append({
            "종목명": h["종목명"], "티커": h["티커"], "통화": h["통화"],
            "수량": h["수량"], "평균단가": h["평균단가"],
            "직전기록일": prev.get("날짜", ""), "직전단가": prev.get("주당단가", ""),
        })
    print(json.dumps({"환율": _fx(wb), "보유종목": rows}, ensure_ascii=False, indent=2))
    return 0


def _find_price_row(ws, d, name: str) -> int | None:
    for r in range(P.PRICE_FIRST_ROW, P.MAXR + 1):
        if ws.cell(row=r, column=3).value == name and \
           P._norm_date(ws.cell(row=r, column=2).value) == d:
            return r
    return None


def _first_free_price_row(ws) -> int:
    for r in range(P.PRICE_FIRST_ROW, P.MAXR + 1):
        if not ws.cell(row=r, column=3).value:
            return r
    raise RuntimeError("시세기록 행이 가득 찼다")


def _snapshot_row(ws, d) -> int:
    for r in range(P.SNAP_FIRST_ROW, P.MAXR + 1):
        v = ws.cell(row=r, column=2).value
        if v in (None, ""):
            return r
        if P._norm_date(v) == d:
            return r
    raise RuntimeError("대시보드 스냅샷 행이 가득 찼다")


def cmd_apply(wb, path: str, snap: dict) -> int:
    d = P._norm_date(snap.get("날짜")) or P._norm_date(P._today())
    prices = snap.get("시세") or {}
    if not prices:
        print("오류: 시세가 비었다.", file=sys.stderr)
        return 2

    if snap.get("환율"):
        wb["설정"].cell(row=FX_ROW, column=3, value=float(snap["환율"]))
        wb["설정"].cell(row=FX_DATE_ROW, column=3, value=d)
    fx = _fx(wb)

    holdings = {h["종목명"]: h for h in P.read_holdings(path, only_active=True)}
    unknown = [n for n in prices if n not in holdings]

    wsp = wb["시세기록"]
    written, skipped = [], []
    for name, price in prices.items():
        h = holdings.get(name)
        if h is None:
            continue
        if h["수량"] in (None, "", 0):
            skipped.append(name)
        r = _find_price_row(wsp, d, name) or _first_free_price_row(wsp)
        P._write_price_row_format(wsp, r)
        wsp.cell(row=r, column=2, value=d)
        wsp.cell(row=r, column=3, value=name)
        wsp.cell(row=r, column=4, value=h["통화"])
        wsp.cell(row=r, column=5, value=float(price))
        wsp.cell(row=r, column=6, value=h["수량"])
        wsp.cell(row=r, column=7, value=fx if h["통화"] == "USD" else 1)
        # 8열은 평가액 수식 자리다. 입력경로는 9열.
        wsp.cell(row=r, column=9, value=snap.get("입력경로", "수동"))
        written.append(name)

    missing = [n for n in holdings if n not in prices]

    wsd = wb["대시보드"]
    sr = _snapshot_row(wsd, d)
    P._write_snapshot_row_format(wsd, sr)
    wsd.cell(row=sr, column=2, value=d)
    if snap.get("보유현금") is not None:
        wsd.cell(row=sr, column=4, value=float(snap["보유현금"]))
    # 입출금은 payload에 명시됐을 때만 쓴다. 같은 날짜로 재실행할 때
    # 이미 기록한 입금액이 0으로 덮이면 순입금누계 전체가 틀어진다.
    if snap.get("입출금") is not None:
        wsd.cell(row=sr, column=6, value=float(snap["입출금"]))
    elif wsd.cell(row=sr, column=6).value in (None, ""):
        wsd.cell(row=sr, column=6, value=0)
    if snap.get("메모"):
        wsd.cell(row=sr, column=11, value=snap["메모"])
    for col, formula in P.snapshot_row_formulas(sr).items():
        wsd[f"{col}{sr}"] = formula

    wb.save(path)
    print(json.dumps({
        "결과": "반영 완료",
        "기록일": str(d),
        "환율": fx,
        "시세_기록": written,
        "스냅샷_행": sr,
        "수량_미입력": skipped,
        "시세_누락": missing,
        "마스터에_없는_종목": unknown,
        "파일": path,
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="보유 종목과 직전 시세를 출력")
    ap.add_argument("--input", help="snapshot JSON 파일 경로 (생략 시 stdin)")
    ap.add_argument("--workbook", default=P.DEFAULT_WB_PATH)
    args = ap.parse_args()

    if not os.path.exists(args.workbook):
        print(f"오류: 워크북이 없다 — {args.workbook}", file=sys.stderr)
        return 2

    wb = P.open_wb(args.workbook)
    if args.list:
        return cmd_list(wb, args.workbook)

    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    return cmd_apply(wb, args.workbook, json.loads(raw))


if __name__ == "__main__":
    raise SystemExit(main())
