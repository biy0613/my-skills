# -*- coding: utf-8 -*-
"""
가격대 점검 — 종목 1개를 '대화로 정한 내 가정'으로 계산한다 (멍거버거 5~7단계용).

pricezone.py 는 컨센서스를 그대로 넣는 전 종목 훑기다. 이 파일은 사용자와 정한 가정 파일 하나를 읽어
  ① 시나리오별 적정가·분류  ② 확률 가중  ③ 컨센서스 기준 결과와의 차이
  ④ 역산(지금 주가가 요구하는 정상 이익·배수)  ⑤ 분류 경계가 되는 주가
를 낸다. 읽기만 한다 — 가정 파일은 Claude 가 대화 결과로 쓴다.

가정 파일 (JSON, 보통 `종목분석툴/리포트/_소스/<종목>/_가격대가정.json`):
{
  "name": "SK하이닉스", "code": "000660",          # 국장 6자리 또는 미장 티커
  "price": null,                                   # 비우면 최신 종가를 받는다
  "discount": 0.10,                                # 연 할인율
  "shares": null,                                  # 주식 수(주). 넣으면 시나리오를 순이익 총액("ni")으로 적을 수 있다
  "unit": "원",                                    # 표시용
  "scenarios": [
    {"name": "기본", "prob": 0.5,
     "eps": [537506, 601777, 601777],              # 이례적 이익 구간 — 연도 수는 자유(1~6년). 총액이면 "ni"
     "normal": 67188, "multiple": 10,              # 그 뒤 정상 이익(주당 또는 총액)과 배수
     "why": "공급 부족 2029년까지 · 정상 이익은 장기공급계약 반영 연 50조"}
  ],
  "ledger": [ {"가정": "호황 종료 시점", "값": "2029년 말", "근거": "3분기 콘퍼런스콜", "확정": "2026-11-15 사용자"} ]
}

사용:
  python myzone.py <가정파일.json>
  python myzone.py --template 000660 "SK하이닉스"      # 컨센서스를 채운 초안을 stdout 으로 (파일은 직접 저장)
"""
import sys, os, json, argparse

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pricezone as Z


def get_price(code):
    if code.isdigit():
        return Z.kr_close(code)
    return Z.us_closes([code]).get(code, (None, None))


def consensus(code, root):
    sys.path.insert(0, root)
    import _경로 as P
    rows, stamp, cyc, T = Z.load_consensus(P)
    r = rows.get(code)
    if not r:
        return None
    e0, e1, e2 = Z.fl(r["eps_0"]), Z.fl(r["eps_a"]), Z.fl(r["eps_b"])
    if e1 is None or e2 is None or e1 <= 0 or e2 <= 0:
        return None
    base = Z.BASE_KR if (code.isdigit() or code in Z.CHINA) else Z.BASE_US
    g1 = e2 / e1 - 1
    if code in Z.MEM:
        kind, M, N = "메모리", 10, Z.MEM_NORMAL * e1
    elif code in cyc or code in Z.CYC_EXTRA:
        kind, M, N = "AI연동", base, Z.CYC_NORMAL * e2
    else:
        kind, M, N = "일반", base * next((m for c, m in Z.TIERS if g1 > c or (c == 0.10 and g1 >= c)), 1.0), e2
    return dict(stamp=stamp, y1=T - 1, T=T, e0=e0, e1=e1, e2=e2, kind=kind, M=M, N=N)


def fair(eps, normal, mult, disc):
    n = len(eps)
    return (sum(eps) + normal * mult) / (1 + disc) ** n


def template(code, name, root):
    c = consensus(code, root)
    eps = [round(c["e1"], 2), round(c["e2"], 2), round(c["e2"], 2)] if c else [None, None, None]
    d = {"name": name, "code": code, "price": None, "discount": 0.10, "shares": None, "unit": "원" if code.isdigit() else "달러",
         "scenarios": [
             {"name": "좋은 경우", "prob": 0.25, "eps": eps, "normal": None, "multiple": None, "why": "(대화로 정한다)"},
             {"name": "기본", "prob": 0.5, "eps": eps, "normal": round(c["N"], 2) if c else None, "multiple": c["M"] if c else None,
              "why": f"출발점 = 컨센서스({c['stamp']}) + 스킬 기본 가정 — 대화로 하나씩 바꾼다" if c else "(컨센서스 없음 — 전부 대화로 정한다)"},
             {"name": "나쁜 경우", "prob": 0.25, "eps": eps, "normal": None, "multiple": None, "why": "(대화로 정한다)"}],
         "ledger": [{"가정": "", "값": "", "근거": "", "확정": ""}]}
    print(json.dumps(d, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--template", nargs=2, metavar=("CODE", "NAME"))
    ap.add_argument("--root", default=Z.ROOT_DEFAULT)
    a = ap.parse_args()
    if a.template:
        return template(a.template[0].upper(), a.template[1], a.root)
    if not a.file:
        ap.error("가정 파일 경로가 필요합니다")

    d = json.load(open(a.file, encoding="utf-8"))
    code, name = str(d["code"]).upper(), d.get("name") or d["code"]
    disc, sh, unit = d.get("discount", 0.10), d.get("shares"), d.get("unit", "")
    p, pdate = (d["price"], "가정 파일") if d.get("price") else get_price(code)
    if p is None:
        sys.exit("종가를 받지 못했습니다 — 가정 파일에 price 를 넣으세요")

    def per_share(s, key_eps="eps", key_ni="ni"):
        if s.get(key_eps) is not None:
            return s[key_eps]
        if s.get(key_ni) is not None and sh:
            v = s[key_ni]
            return [x / sh for x in v] if isinstance(v, list) else v / sh
        return None

    print(f"# {name} 가격대 점검 — 내 가정 기준 · 종가 {p:,.2f}{unit} ({pdate}) · 할인율 연 {disc*100:g}%")
    print("\n## 시나리오\n| 시나리오 | 확률 | 이례적 구간 이익 | 정상 이익 × 배수 | 적정가 | 적정÷주가 | 분류 | 근거 |\n|---|--:|---|---|--:|--:|---|---|")
    rows, wsum, psum = [], 0.0, 0.0
    for s in d["scenarios"]:
        eps = per_share(s)
        normal = s.get("normal") if s.get("normal") is not None else (s["normal_ni"] / sh if (s.get("normal_ni") is not None and sh) else None)
        mult = s.get("multiple")
        if not eps or any(x is None for x in eps) or normal is None or mult is None:
            print(f"| {s['name']} | {s.get('prob','')} | — | — | — | — | 가정 미정 | {s.get('why','')} |"); continue
        fv = fair(eps, normal, mult, disc)
        r = fv / p
        rows.append((s, eps, normal, mult, fv, r))
        pr = s.get("prob")
        if pr:
            wsum += pr * fv; psum += pr
        print(f"| {s['name']} | {'' if pr is None else f'{pr*100:g}%'} | {' · '.join(f'{x:,.0f}' if abs(x) >= 100 else f'{x:,.2f}' for x in eps)} ({len(eps)}년) | "
              f"{normal:,.2f} × {mult:g} | {fv:,.0f} | {r:.2f} | {Z.cls(r)} | {s.get('why','')} |")
    if psum > 0 and len(rows) > 1:
        wf = wsum / psum
        print(f"| 확률 가중 | {psum*100:g}% | | | {wf:,.0f} | {wf/p:.2f} | {Z.cls(wf/p)} | 확률은 사용자와 정한 값 |")

    c = consensus(code, a.root)
    print("\n## 컨센서스 기준과 비교")
    if c:
        cf = fair([c["e1"], c["e2"], c["e2"]], c["N"], c["M"], 0.10)
        print(f"- 컨센서스({c['stamp']}) + 스킬 기본 가정({c['kind']}, 정상 {c['N']:,.2f} × {c['M']:g}): 적정가 {cf:,.0f} · 적정÷주가 {cf/p:.2f} · {Z.cls(cf/p)}")
        for s, eps, normal, mult, fv, r in rows:
            diff = []
            if len(eps) >= 2:
                diff.append(f"{c['y1']}E {eps[0]/c['e1']-1:+.0%} · {c['T']}E {eps[1]/c['e2']-1:+.0%}")
            diff.append(f"구간 {len(eps)}년(컨센 3년)")
            diff.append(f"정상 이익 {normal/c['N']-1:+.0%}")
            diff.append(f"배수 {mult:g}(기본 {c['M']:g})")
            print(f"- [{s['name']}] 컨센서스 대비: " + " · ".join(diff) + f" → 적정가 {fv/cf-1:+.0%}")
    else:
        print("- 성장률PER지도 기록에 이 종목 컨센서스가 없습니다 — 비교 생략")

    base = next((x for x in rows if x[0]["name"] == "기본"), rows[0] if rows else None)
    if base:
        s, eps, normal, mult, fv, r = base
        n = len(eps); D = (1 + disc) ** n
        need_tv = p * D - sum(eps)
        print(f"\n## 역산 — 지금 주가가 요구하는 것 ([{s['name']}] 시나리오의 구간 이익을 그대로 둘 때)")
        print(f"- {n}년 이익 합 {sum(eps):,.0f} vs 주가×할인 {p*D:,.0f} → 구간 뒤에 남아야 하는 가치 {need_tv:,.0f}" + (" (음수: 구간 이익만으로 주가가 설명된다 = 시장이 그 이익을 안 믿는다)" if need_tv < 0 else ""))
        print(f"- 배수 {mult:g} 유지 시 필요한 정상 이익: {need_tv/mult:,.2f} (내 가정 {normal:,.2f}의 {need_tv/mult/normal:.0%})")
        print(f"- 정상 이익 {normal:,.2f} 유지 시 필요한 배수: {need_tv/normal:.1f}배 (내 가정 {mult:g}배)")
        cut = (p * D - normal * mult) / sum(eps) - 1
        print(f"- 정상 이익·배수 유지 시 구간 이익이 {cut:+.0%} 달라져야 지금 주가가 딱 적정가")
        print(f"\n## 분류 경계 주가 ([{s['name']}] 기준 적정가 {fv:,.0f})")
        print("| 경계 | 주가 |\n|---|--:|")
        print(f"| 매우 싸다 ↔ 싸다 (1.5) | {fv/1.5:,.0f} |\n| 싸다 ↔ 보통 (1.15) | {fv/1.15:,.0f} |\n| 보통 ↔ 비싸다 (0.85) | {fv/0.85:,.0f} |")
        print("- 이 표는 손절·진입 라인이 아니다. 라인은 판정 카드(9단계)에서 따로 정한다.")

    if d.get("ledger"):
        L = [x for x in d["ledger"] if x.get("가정")]
        if L:
            print("\n## 가정 원장\n| 가정 | 값 | 근거 | 확정 |\n|---|---|---|---|")
            for x in L:
                print(f"| {x.get('가정','')} | {x.get('값','')} | {x.get('근거','')} | {x.get('확정','')} |")
    print("\n내부 분석용 · 투자 권유 아님")


if __name__ == "__main__":
    main()
