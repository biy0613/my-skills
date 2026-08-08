#!/usr/bin/env python3
"""딜플로우 관찰 DB 대조.

이 스크립트는 후보 관찰만 골라준다. 지지/반박 문장은 사람(또는 Claude)이 쓴다.
결과가 비면 그것이 정상 출력이다 — 억지로 연결하지 말 것.

  python lookup.py --market KR --q 펌텍코리아 --q 용기 --q 색조
  python lookup.py --list
"""

import argparse
import json
import os
import re
import sys
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_DATA_DIR = r"C:\Users\biy06\OneDrive\바탕 화면\클로드실습\주식\종목분석툴"

# (시장유효성, 조회시장) → 적용가능
APPLICABILITY = {
    "KR": {"KR": "예", "US": "주의"},
    "US": {"KR": "주의", "US": "예"},
    "양쪽": {"KR": "예", "US": "예"},
    "KR실패-US유효": {"KR": "금지", "US": "예"},
    "US선행-KR도착중": {"KR": "주의", "US": "예"},
}

APPLICABILITY_NOTE = {
    "예": "",
    "주의": "다른 시장 실측 — 시차·시장 차이를 문장에 반드시 적을 것",
    "금지": "지지 근거로 쓰지 말 것. 반례로만 언급 가능",
    "미판정": "--market 미지정. 지리적 비대칭 검사가 안 됨",
}

_PUNCT = re.compile(r"[\s·,()\[\]{}·/\-_'\"]+")


def norm(s):
    return _PUNCT.sub("", str(s)).lower()


def find_data_dir(explicit):
    for cand in (explicit, os.getcwd(), DEFAULT_DATA_DIR):
        if cand and os.path.isfile(os.path.join(cand, "observations.json")):
            return cand
    return None


def freshness(일자, today):
    """일자 문자열에서 마지막 YYYY-MM을 뽑아 신선도를 계산한다."""
    months = re.findall(r"(\d{4})-(\d{2})", str(일자))
    if not months:
        return "판정불가", None
    y, m = int(months[-1][0]), int(months[-1][1])
    elapsed = (today.year - y) * 12 + (today.month - m)
    if elapsed < 0:
        elapsed = 0
    if elapsed <= 6:
        label = "신선"
    elif elapsed <= 18:
        label = "유효"
    else:
        label = "노후"
    return f"{label}({elapsed}개월)", elapsed


def score_obs(obs, terms):
    """관찰 1건 점수. (점수, 매칭근거리스트)"""
    total, why = 0, []
    chain_names = [c.get("이름", "") for c in obs.get("연결_밸류체인", [])]
    keywords = obs.get("키워드", [])
    body = " ".join(
        str(obs.get(f, "")) for f in ("실측치", "함의", "출처", "note")
    )
    nbody, ntheme = norm(body), norm(obs.get("테마", ""))

    for raw in terms:
        t = norm(raw)
        if not t:
            continue
        min_partial = 3 if t.isascii() else 2
        hit = 0

        for name in chain_names:
            n = norm(name)
            if n and (t == n or (len(t) >= min_partial and (t in n or n in t))):
                hit = max(hit, 4)
                why.append(f"밸류체인:{name}")
                break

        if hit < 4:
            for kw in keywords:
                n = norm(kw)
                if not n:
                    continue
                if t == n:
                    hit = max(hit, 3)
                    why.append(f"키워드:{kw}")
                    break
                if len(t) >= min_partial and (t in n or n in t):
                    hit = max(hit, 2)
                    why.append(f"키워드~{kw}")

        if hit < 2 and len(t) >= min_partial and t in ntheme:
            hit = max(hit, 2)
            why.append(f"테마:{obs.get('테마')}")

        if hit < 1 and len(t) >= min_partial and t in nbody:
            hit = 1
            why.append("본문")

        total += hit
    return total, why


def render(obs, sc, why, market, today, indent=""):
    fresh, _ = freshness(obs.get("일자"), today)
    valid = obs.get("시장유효성", "?")
    appl = APPLICABILITY.get(valid, {}).get(market, "미판정") if market else "미판정"
    note = APPLICABILITY_NOTE.get(appl, "")
    out = []
    flag = " ⚠역방향" if obs.get("역방향") else ""
    out.append(
        f"{indent}■ {obs['obs_id']} · {obs.get('출처')} · {obs.get('일자')} "
        f"· {obs.get('유형')} · {obs.get('신뢰도')} · 신선도 {fresh}{flag}"
    )
    out.append(f"{indent}  실측치: {obs.get('실측치')}")
    out.append(
        f"{indent}  시장: 관찰 {obs.get('관찰시장')} / 유효성 {valid} → 적용가능 {appl}"
        + (f"  ({note})" if note else "")
    )
    out.append(f"{indent}  함의: {obs.get('함의')}")
    chain = obs.get("연결_밸류체인", [])
    if chain:
        out.append(
            f"{indent}  후보(전부 검증 필요): "
            + ", ".join(f"{c['이름']}[{c['시장']}·{c['역할']}]" for c in chain)
        )
    if obs.get("note"):
        out.append(f"{indent}  note: {obs['note']}")
    out.append(f"{indent}  사용처: {', '.join(obs.get('사용처') or ['-'])} · 매칭 {sc}점 ({', '.join(dict.fromkeys(why))})")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="딜플로우 관찰 DB 대조")
    ap.add_argument("--q", action="append", default=[], help="검색어(여러 번 가능)")
    ap.add_argument("--market", choices=["KR", "US"], help="조회 대상 종목 시장(US는 미장·유럽 포함)")
    ap.add_argument("--data-dir", help="observations.json이 있는 폴더")
    ap.add_argument("--min-score", type=int, default=3)
    ap.add_argument("--all", action="store_true", help="약한 일치도 표시")
    ap.add_argument("--list", action="store_true", help="전체 관찰 목록")
    ap.add_argument("--json", action="store_true", help="기계 판독용 출력")
    ap.add_argument("--asof", help="신선도 기준일 YYYY-MM-DD (기본: 오늘)")
    args = ap.parse_args()

    today = date.fromisoformat(args.asof) if args.asof else date.today()

    data_dir = find_data_dir(args.data_dir)
    if not data_dir:
        print("관찰 DB를 찾지 못했다. observations.json이 있는 폴더를 --data-dir로 주거나,")
        print("사용자에게 프로젝트 폴더 경로를 물어라. 다른 곳을 임의로 뒤지지 말 것.")
        return 2

    with open(os.path.join(data_dir, "observations.json"), encoding="utf-8") as f:
        db = json.load(f)
    obs_all = db["observations"]

    if args.list:
        print(f"관찰 DB {db['db_version']} · {len(obs_all)}건 · 생성 {db['생성일']} · {data_dir}")
        by_theme = {}
        for o in obs_all:
            by_theme.setdefault(o["테마"], []).append(o)
        for theme, items in by_theme.items():
            print(f"\n[{theme}] {len(items)}건")
            for o in items:
                fresh, _ = freshness(o.get("일자"), today)
                rev = " ⚠" if o.get("역방향") else "  "
                print(f" {rev}{o['obs_id']} {o['유형']:<5} {o['신뢰도']:<3} {o['시장유효성']:<14} {fresh:<10} {o['출처']}")
                print(f"     {o['실측치'][:110]}")
        print("\n내부 분석용 · 투자 권유 아님")
        return 0

    if not args.q:
        ap.error("--q 검색어가 필요하다 (또는 --list)")
    if not args.market:
        print("⚠ --market 미지정: 지리적 비대칭 검사가 수행되지 않는다. KR/US를 지정할 것.\n")

    scored = []
    for o in obs_all:
        sc, why = score_obs(o, args.q)
        if sc > 0:
            scored.append((sc, o, why))
    scored.sort(key=lambda x: (-x[0], x[1]["obs_id"]))

    strong = [s for s in scored if s[0] >= args.min_score]
    weak = [s for s in scored if s[0] < args.min_score]

    if args.json:
        print(json.dumps({
            "query": args.q, "market": args.market, "db_version": db["db_version"],
            "hits": [{"score": s, "why": w, **o} for s, o, w in strong],
            "weak": [{"score": s, "why": w, "obs_id": o["obs_id"], "실측치": o["실측치"]} for s, o, w in weak],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"딜플로우 대조 — 질의 {args.q} · 시장 {args.market or '미지정'} · DB {db['db_version']}({len(obs_all)}건)")
    print("=" * 78)

    if not strong:
        print("\n해당 없음 — 관찰 DB에 이 종목의 밸류체인·수요 구조와 겹치는 실측치가 없다.")
        print("억지로 연결하지 말 것. 판정은 나머지 문항으로만 한다.")
    else:
        print(f"\n해당 있음 {len(strong)}건\n")
        for sc, o, why in strong:
            print(render(o, sc, why, args.market, today))
            print()

    if weak and (args.all or not strong):
        print("-" * 78)
        print("약한 일치 — 참고용이며 엣지가 아니다. 별도 근거 없이 인용하지 말 것.")
        for sc, o, why in weak[:8]:
            print(f"  {o['obs_id']} ({sc}점, {', '.join(dict.fromkeys(why))}) {o['실측치'][:80]}")
        print()

    print("=" * 78)
    print("모든 상장 매핑은 후보다(검증 필요). 내부 분석용 · 투자 권유 아님.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
