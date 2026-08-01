# 투자밋업 보고서 사양 (build_report.py)

A4 1페이지 단일 표. 견본(스타트업플러스 온라인 투자밋업 보고서)을 픽셀 단위로 재현. 폰트 Noto Sans CJK KR.

## 실행
```bash
python3 scripts/build_report.py data.json "투자밋업 보고서(회사명).docx"
# → 같은 폴더에 "투자밋업 보고서(회사명).pdf" 생성 (LibreOffice 변환)
```
필요 패키지: python-docx, PyMuPDF(fitz), Pillow, LibreOffice(soffice). data.json은 python/heredoc으로 기록(Write 툴 금지: 작업폴더 FS 불안정).

## data.json 스키마 (회사별 가변값만)
| 키 | 설명 |
|----|------|
| meet_date | 밋업일시 예 "2026.6.5. (금)" |
| company | 기업명 예 "주식회사 폴미" |
| ceo | 담당자명/직급 예 "송진욱 대표" |
| item_overview | 아이템 개요 (2줄) |
| diff_feature | 차별화 특징 (2줄) |
| market_fit | 시장 적합성 (2줄) |
| tech_diff | 기술 차별성 (2줄) |
| finance | 재무 현황 (2줄) |
| intent | 투자 의향 정수 1~5 (5=매우높음…1=매우낮음) |
| positive | 긍정적 검토의견 (2줄) |
| negative | 부정적 검토의견 (2줄) |
| photos | 사진 2장 경로 리스트 ["…/회사명1.png","…/회사명2.png"] (없으면 null → "(사진)" 자리표시) |

7개 본문 항목(item_overview/diff_feature/market_fit/tech_diff/finance/positive/negative)은 **보고서 상 각 2줄**이 되도록 약 65~70자로 작성. 값 칸 폭 약 355pt 기준.

## 고정 필드 (build_report.py의 FIXED — 회사마다 바꾸지 않음)
- 투자기관명: 패스트벤처스 주식회사 / 담당자: 박인엽 팀장
- 관심사업분야: IT/운영관리/라이프스타일/미디어/엔터테인먼트/바이오/에너지/프롭테크/하드웨어
- 관심기술분야: AI/데이터/로보틱스/사물인터넷/신소재/전고체배터리/제조/클라우드
- 투자밋업 희망대상: 무관 / 보유펀드명: 패스트 Core-1 투자조합, 패스트 2022 Seed 투자조합
- 투자기관구분: ▣창업투자회사 / 밋업형식: 온라인 미팅 / 계좌: 우리은행(번호는 스크립트에 기재)
> 다른 투자사/담당자가 쓰려면 scripts/build_report.py 상단 FIXED dict만 수정.

## 표 구조
밋업정보 → 투자자정보 → 스타트업정보 → 밋업내용(사업아이템: 아이템개요·차별화특징 / 투자검토 의견: 시장적합성·기술차별성·재무현황 / 종합검토 의견: 투자의향 5점척도·긍정적·부정적 검토의견) → 밋업 사진(2장+캡션 "밋업 진행 사진") → 계좌 번호. 좌측 섹션 라벨 음영 #BFBFBF, 필드명/서브라벨 #F2F2F2, 밋업내용 필드명 열은 흰색+볼드. 가운데 라벨은 단어 단위 2줄로 자동 처리(vlabel).

## 사진 처리
- 사용자가 연결 폴더에 `회사명1.png`·`회사명2.png`로 저장하는 방식이 가장 확실. 채팅 붙여넣기 이미지는 같은 턴에 파일로 접근 불가(세션 transcript도 스냅샷 고정되어 당일 턴 미반영일 수 있음) → 폴더 저장을 요청.
- 가로형 화면캡처(약 1670×900) 기준 photo_block의 max_h=108pt로 자동 축소돼 1페이지 유지. PNG/JPG 무관.
- OneDrive 동기화 폴더라 bash에서 안 보이면 클라우드 전용 → Read 툴로 한 번 열면 로컬로 내려와 접근 가능.

## 검증 (생성 후 권장)
```python
import fitz
doc=fitz.open("투자밋업 보고서(회사명).pdf")
assert doc.page_count==1                       # 1페이지
p=doc[0]
assert len(p.get_image_info())==2              # 사진 2장
assert "(사진)" not in p.get_text()            # 자리표시 없음
# 투자의향 ■ 위치가 점수와 일치하는지 '■ N점' 확인
# 7개 검토 항목이 각 2줄인지: 값 칸(x0>205, y 246~560) 텍스트 줄 수 = 14
```
