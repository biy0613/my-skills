#!/usr/bin/env python3
"""observations.json → 사람이 읽는 표(observations-table.md).

정본은 JSON이다. 이 표는 리뷰·확인용 파생물이므로 표를 고치지 말고 JSON을 고친 뒤 다시 생성한다.
산출물은 데이터 폴더에만 쓴다 — 스킬 폴더(public repo)에 쓰지 않는다.
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookup import DEFAULT_DATA_DIR, find_data_dir, freshness  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    data_dir = find_data_dir(sys.argv[1] if len(sys.argv) > 1 else None)
    if not data_dir:
        print("observations.json을 찾지 못했다. 폴더 경로를 인자로 줄 것.")
        return 2

    with open(os.path.join(data_dir, "observations.json"), encoding="utf-8") as f:
        db = json.load(f)
    today = date.today()

    L = [
        f"# 딜플로우 관찰 DB {db['db_version']} — 표 뷰",
        "",
        f"생성 {db['생성일']} · 관찰 {len(db['observations'])}건 · 출처 {db['출처_맵']} · "
        f"표 생성일 {today.isoformat()}",
        "",
        "> 정본은 `observations.json`이다. 이 파일은 파생물이므로 직접 고치지 말 것.",
        "> **내부 분석용 · 회사 실명·딜 수치 포함 · 외부 반출 금지 · 투자 권유 아님**",
        "",
    ]

    by_theme = {}
    for o in db["observations"]:
        by_theme.setdefault(o["테마"], []).append(o)

    for theme, items in by_theme.items():
        rev = sum(1 for o in items if o.get("역방향"))
        hard = sum(1 for o in items if o.get("신뢰도") == "실측")
        L += [
            f"## {theme} — {len(items)}건 (실측 {hard} · 역방향 {rev})",
            "",
            "| ID | 출처 | 일자 | 유형 | 신뢰도 | 시장유효성 | 신선도 | 실측치 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for o in items:
            fresh, _ = freshness(o.get("일자"), today)
            val = o["실측치"].replace("|", "/")
            L.append(
                f"| {o['obs_id']}{' ⚠' if o.get('역방향') else ''} | {o['출처']} | {o['일자']} | "
                f"{o['유형']} | {o['신뢰도']} | {o['시장유효성']} | {fresh} | {val} |"
            )
        L.append("")
        for o in items:
            chain = ", ".join(f"{c['이름']}({c['시장']})" for c in o.get("연결_밸류체인", [])) or "—"
            L += [f"- **{o['obs_id']}** 함의: {o['함의']}", f"  - 후보(검증 필요): {chain}"]
            if o.get("note"):
                L.append(f"  - note: {o['note']}")
        L.append("")

    out = os.path.join(data_dir, "observations-table.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"작성: {out}  ({len(db['observations'])}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
