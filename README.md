# my-skills

박인엽 개인 스킬 저장소. **여기가 유일한 원본**이다. 로컬 Claude Code와 Cowork/claude.ai 양쪽이 이 저장소를 바라본다.

## 구조

```
my-skills/
├── .claude-plugin/marketplace.json      # 마켓플레이스 카탈로그
└── plugins/inyeop-skills/
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
`inyeop-skills:daytrading` 형태로 뜬다.

## 스킬을 새로 만들거나 고칠 때

`~/.claude/skills/`에서 평소대로 작업하면 파일은 자동으로 이 저장소에 들어온다 (junction).
반영은 커밋/푸시가 되어야 하므로:

```
/skills-sync
```

또는 직접:

```bash
git -C ~/my-skills add -A && git -C ~/my-skills commit -m "update" && git -C ~/my-skills push
```

Cowork 쪽에 배포하려면 `plugins/inyeop-skills/.claude-plugin/plugin.json`의 `version`을 올린 뒤 푸시한다.
버전을 안 올리면 기존 설치자에게 업데이트가 가지 않는다.

## 스킬 목록

| 스킬 | 용도 | 번들 |
|---|---|---|
| `daytrading` | 삼성전자·SK하이닉스 외국인 수급 일일 시그널 (V0/V1/V2) → 슬랙 발송 | SKILL.md만 |
| `stock-finder-foreign` | 외국인 순매수 기반 KOSPI/KOSDAQ 종목 스크리너 → HTML 리포트 | scripts, references, evals |
| `idm` | 패스트벤처스 IDM(Initial Deal Memo) docx 생성 | scripts, references, assets(벤치마크 IDM 3종 PDF) |
| `startupplus` | 스타트업플러스 투자밋업 보고서 PDF + 투자 거절 메일 docx | scripts, references |
| `pptx-design-system` | PPTX 디자인 시스템 (웜 네이비 + 코랄) | scripts(python-pptx 헬퍼) |
| `research-report-design-system` | 리서치 리포트 디자인 시스템 (HTML/docx/pptx 공용) | SKILL.md만 |
