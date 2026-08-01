# my-skills

inyup 개인 스킬 저장소. **여기가 유일한 원본**이다. 로컬 Claude Code와 Cowork/claude.ai 양쪽이 이 저장소를 바라본다.

## 구조

```
my-skills/
├── .claude-plugin/marketplace.json      # 마켓플레이스 카탈로그
└── plugins/inyup-skills/
    ├── .claude-plugin/plugin.json       # 플러그인 매니페스트 (version 올려야 업데이트 배포됨)
    └── skills/                          # ← 로컬 ~/.claude/skills 가 이 폴더를 가리킴 (junction)
        ├── daytrading/
        ├── idm/
        ├── pptx-design-system/
        ├── research-report-design-system/
        ├── startupplus/
        └── stock-finder-foreign/
```

## 설치

**로컬 Claude Code** — `~/.claude/skills`가 `skills/`를 가리키는 junction이라 별도 설치 없이 바로 뜬다.
접두사 없이 `/daytrading`, `/idm` 형태로 호출.

**Cowork / claude.ai** — 사이드바 `Customize → Plugins → Add from a repository`에 이 저장소의 git URL 입력.
`inyup-skills:daytrading` 형태로 뜬다.

## 스킬을 새로 만들거나 고칠 때 — 아무것도 안 해도 된다

`~/.claude/skills/`에서 평소대로 작업하면 파일은 자동으로 이 저장소에 들어오고(junction),
**세션이 끝날 때 `tools/autopush.ps1`이 커밋·푸시까지 자동으로 한다.**
스킬 파일이 바뀐 경우 `plugin.json`의 patch 버전도 알아서 올린다.

- 훅 설정: `~/.claude/settings.json`의 `hooks.SessionEnd`
- 실행 기록: `tools/autopush.log` (푸시 실패 시 여기에 남는다)

세션이 끝나기 전에 즉시 올리고 싶으면:

```
/skills-sync
```

푸시가 실패하면 커밋은 로컬에 남아 있으므로, 다음 세션 종료 때 함께 올라간다.

### autopush.ps1을 고칠 때 주의

파일이 **ASCII 전용**인 데는 이유가 있다. Windows PowerShell 5.1은 BOM 없는 파일을
시스템 코드페이지(CP949)로 읽기 때문에, 주석에 한글을 넣으면 스크립트가 실행되기도 전에
파싱이 깨진다. 같은 이유로 `plugin.json`을 읽고 쓸 때 UTF-8을 명시한다 —
PowerShell에 맡기면 description의 한글이 조용히 깨진 채 커밋된다.

## 스킬 목록

| 스킬 | 용도 | 번들 |
|---|---|---|
| `daytrading` | 삼성전자·SK하이닉스 외국인 수급 일일 시그널 (V0/V1/V2) → 슬랙 발송 | SKILL.md만 |
| `stock-finder-foreign` | 외국인 순매수 기반 KOSPI/KOSDAQ 종목 스크리너 → HTML 리포트 | scripts, references, evals |
| `idm` | 패스트벤처스 IDM(Initial Deal Memo) docx 생성 | scripts, references, assets(벤치마크 IDM 3종 PDF) |
| `startupplus` | 스타트업플러스 투자밋업 보고서 PDF + 투자 거절 메일 docx | scripts, references |
| `pptx-design-system` | PPTX 디자인 시스템 (웜 네이비 + 코랄) | scripts(python-pptx 헬퍼) |
| `research-report-design-system` | 리서치 리포트 디자인 시스템 (HTML/docx/pptx 공용) | SKILL.md만 |
