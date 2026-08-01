---
name: idm
description: 패스트벤처스(FV) 박인엽의 IDM(Initial Deal Memo)을 Word(.docx)로 작성한다. 회사의 사업소개서/IR 자료와 미팅록 raw data를 입력으로 받아 Miils·숨빗AI·낭만상회 벤치마크와 동일한 8개 섹션 구조·용어·개조식 음슴체 톤·5~6p 길이로 생성한다. 모르는 정보는 추측하지 않고 공란으로 남기며, 시장 분석과 글로벌 경쟁사는 직접 웹 리서치해 수치와 함께 채운다. 트리거 "IDM 작성", "IDM 초안 만들어줘", "OOO IDM", "이 회사 IDM 써줘", "딜 메모", "투자 검토 메모", "사업소개서로 IDM", "initial deal memo".
---

# IDM (Initial Deal Memo) 작성

회사의 **사업소개서/IR 자료**와 **미팅록 raw data**를 읽고, 패스트벤처스 박인엽의 기존 IDM과 동일한 템플릿·용어·톤·길이로 **IDM Word(.docx)** 를 생성한다. 벤치마크는 `assets/`의 3개 IDM(Miils·숨빗AI·낭만상회)이며, 새 IDM은 이 셋과 최대한 닮아야 한다.

## 입력 (사용자 제공)
- **사업소개서/IR 자료** (PDF·이미지·텍스트 등) — 회사가 무엇을 하는지의 1차 출처.
- **미팅록 raw data** (대화체/메모) — 대표 발언, 숫자, 라운드 상황 등. IR에 없는 디테일이 여기 많음.
- 두 입력은 상호 보완·교차검증한다. IR은 공식 수치, 미팅록은 맥락·구두 정보(밸류 목표, 우려점 등).

## 핵심 원칙 (반드시 준수)
1. **모르면 비운다 — 추측 금지.** 표의 필드나 본문에 들어갈 정보를 입력에서 확인할 수 없으면 **공란**으로 둔다(표 값은 빈 문자열 `""`). "협의 필요" 같은 추정 라벨도 넣지 말고 비운다. 단 `소싱한 사람`은 기본값 **박인엽**.
2. **시장·경쟁사는 직접 리서치한다.** `Market & Competition`과 시장 규모(TAM)는 입력에 없어도 **WebSearch로 직접 조사**해 채운다. 벤치마크처럼 글로벌·국내 경쟁/비교 기업의 **펀딩 라운드·기업가치·M&A(인수)액·매출** 같은 구체 수치를 검증해 적는다. 출처가 불확실한 수치는 적지 않는다.
3. **벤치마크를 모사한다.** 단어 선택, 8개 섹션 구조, 개조식 음슴체, 한·영 혼용 용어, 분량(A4 5~6p)을 `assets/`의 3개 IDM과 최대한 일치시킨다. 상세 규칙은 `references/template-guide.md`.

## 작업 순서
1. **벤치마크 학습** — 처음이거나 감을 잡을 때 `references/template-guide.md`를 읽고, 필요시 `references/benchmarks/*.md`(3개 IDM 본문)로 실제 어투·디테일을 확인한다.
2. **입력 정독** — 사업소개서/IR과 미팅록을 모두 읽는다. PDF는 `pdftotext -layout`로 추출하고, 이미지 슬라이드면 페이지를 PNG로 렌더해 Read로 직접 본다. 사업·팀·BM·지표·라운드 조건·대표 발언을 빠짐없이 뽑는다. IR과 미팅록의 **수치 불일치**(밸류·자금용처 등)는 메모해 본문에 양쪽 다 표기하거나 플래그한다.
3. **8개 섹션으로 매핑** — 아래 구조에 맞춰 내용을 배치. 모르는 칸은 공란.
4. **시장·경쟁사 리서치** — 섹터를 규정하고 비교/경쟁 기업 3~5곳(국내+글로벌)과 TAM을 WebSearch로 조사. 각 사는 `회사명` + 하위 불릿에 펀딩/인수/매출/밸류 수치를 적는다(숨빗AI IDM의 경쟁사 파트가 모범).
5. **Good Points / Risk Factors 작성** — 박인엽 1인칭 관점의 개조식 음슴체로, 공격적이되 사실 기반 균형. Good Points는 번호 thesis + 근거. 물질적 리스크가 있으면 Risk Factors도 넣는다(숨빗AI엔 있고 낭만상회엔 없음 — 딜에 맞춰 판단).
6. **빌드** — data JSON을 만들어 스크립트로 docx 생성(아래 "빌드" 참조).
7. **검증** — docx를 PDF로 렌더해 (a) 분량 5~6p, (b) 표 7행·공란 필드가 빈칸인지, (c) Good/Risk 번호·강조, (d) 음슴체·용어가 벤치마크와 유사한지 확인.
8. **저장·제시** — 연결 폴더에 `회사명 IDM.docx` 저장 후 present_files로 제시. 만든 것과 공란·리서치 출처·수치 플래그를 1~3문장으로 요약.

## IDM 구조 (8개 섹션)
순서 고정. 상세·예시는 `references/template-guide.md`.
1. **제목** — `회사명 IDM` + 부제 `Initial Deal Memo`
2. **1. Company Name** — 7행 표. 좌측: 분야 / 제품·서비스 / 대표 / 설립연월 / 임직원수 / 주주구성 / 소싱한 사람. 우측: 투자유형 / 펀딩단계 / 펀딩규모 / 기업가치 / FV검토규모 / 투자유치 내역 / 소싱 경로.
3. **Deal Structure** — "~사에 대한 [단계] 투자 검토의 건" + 라운드 현황(밸류·raise·리드·커밋·잔여 룸).
4. **People** — 대표·핵심팀 이력(전 직장·성과·관계).
5. **Business & Product** — 분량 핵심. 문제/페인포인트 → 솔루션 → BM·지표 → Unit Economics → 인허가·확장 등(딜별 가변).
6. **Market & Competition** — 비교/경쟁사 + TAM. 펀딩·인수·매출·밸류·exit 수치 중심(직접 리서치).
7. **Good Points** — 번호(1·2·3) 투자 thesis + 근거.
8. **Risk Factors** — (해당 시) 번호 리스크. 강조 색으로 라벨 표기.

## 톤·문체 (요약)
- 본문은 **개조식 음슴체**: "~함 / 임 / 음 / 보임 / 판단됨 / 사료됨 / 인상적임". 1인칭 판단을 드러낸다.
- **숫자 구체적으로**($, 억 원, %, 배수). 비교기업은 exit/인수/밸류로 규모를 보여준다.
- **한·영 용어 혼용**: 룸·커밋·raise·리드투자, Unit Economics·공헌이익률, BM·지표·MRR·AOV·YoY·이탈률, PMF·레퍼런스·교두보·빅샷, D2C·B2B 등.
- 투자 검토는 사용자 선호상 **다소 공격적 시각**(업사이드·$1B 잠재력)으로 쓰되, 우려점("가장 걸렸던 부분")도 솔직히 적어 균형을 맞춘다.

## 빌드 (스크립트)
docx는 `scripts/build_idm.py`로 생성한다. 매번 레이아웃을 재작성하지 말 것.
1. `references/`와 입력을 근거로 **data JSON**을 작성한다. 스키마와 채운 예시는 `scripts/example_data.json`(수에르테 실제 예시) 참조.
   - `table`은 7행 `[좌라벨, 좌값, 우라벨, 우값]`. 모르는 값은 `""`.
   - 각 섹션 `items`는 `{"t": 문장, "lv": 0|1|2}`. `lv` 0/1/2 = 불릿 • / ◦ / ▪.
   - `Good Points`·`Risk Factors`는 `"ordered": true`(lv0이 "1)"로 자동 번호). 각 번호 라벨은 `"bold": true`. `Risk Factors`는 `"accent": true`로 라벨을 강조색 처리.
   - 본문 문장에 `" : "`가 있으면 앞 라벨이 자동 굵게 된다(예: `"BM : ..."`).
2. 실행:
   ```bash
   pip install python-docx --break-system-packages -q   # 최초 1회
   python3 scripts/build_idm.py data.json "회사명 IDM.docx"
   ```
3. 검증용 PDF 렌더(선택):
   ```bash
   soffice --headless --convert-to pdf "회사명 IDM.docx"
   ```

## 반드시 지킬 것
- **공란 원칙**을 어기지 말 것. 모르는 칸을 그럴듯하게 채우면 안 된다 — 비운다.
- **시장·경쟁사 수치는 반드시 출처 있는 리서치 결과**만. 환각 수치 금지.
- 길이는 벤치마크 수준(5~6p). 너무 짧으면 Business & Product의 디테일·지표를, 너무 길면 군더더기를 조정.
- 표의 가운데 정렬·음영·번호 등 레이아웃은 스크립트가 처리하므로 **내용에만 집중**한다.
- data JSON은 한글이 많으므로 UTF-8로 저장하고, 작성 후 `python3 -c "import json;json.load(open('data.json'))"`로 파싱을 확인한다.

## 참고 파일
- `references/template-guide.md` — 8개 섹션 상세 구조·필드 정의·톤·용어 사전·길이 기준·작성 체크리스트.
- `references/benchmarks/miils.md`, `sumbit-ai.md`, `nangmang-sanghoe.md` — 3개 IDM 본문(어투·디테일 모사용).
- `assets/Miils IDM.pdf`, `숨빗AI IDM.pdf`, `낭만상회(토더) IDM.pdf` — 원본 벤치마크(레이아웃 확인용).
- `scripts/build_idm.py` — docx 생성기. `scripts/example_data.json` — data 스키마 + 수에르테 예시.
