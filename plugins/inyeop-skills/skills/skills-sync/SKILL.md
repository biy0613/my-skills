---
name: skills-sync
description: my-skills 저장소(개인 스킬 원본)의 변경분을 커밋하고 푸시한다. 스킬을 새로 만들거나 고친 뒤 Cowork·다른 기기에 반영할 때 사용.
argument-hint: "[커밋 메시지 (생략 가능)]"
disable-model-invocation: true
allowed-tools: Bash(git -C C:/Users/biy06/my-skills *)
---

# 스킬 저장소 동기화

`~/.claude/skills`는 `C:/Users/biy06/my-skills/plugins/inyeop-skills/skills`를 가리키는 junction이다.
즉 로컬에서 스킬을 만들거나 고치면 파일은 이미 저장소 안에 있고, **커밋·푸시만 남아 있다.**

## 실행

### 1. 변경분 확인

```bash
git -C C:/Users/biy06/my-skills status --short
```

변경이 없으면 "동기화할 변경 없음"이라고만 알리고 끝낸다.

새로 추가된 스킬 폴더가 있으면 **SKILL.md가 있는지 먼저 확인**한다. 없으면 스킬이 아니라 작업 산출물일 가능성이 높으므로, 커밋에 포함할지 사용자에게 묻는다. 스킬 폴더로 위장한 실행 결과물이 저장소에 쌓이면 나중에 무엇이 진짜 스킬인지 구분할 수 없게 된다.

### 2. 새 스킬이 추가됐다면 version 올리기

`plugins/inyeop-skills/.claude-plugin/plugin.json`의 `version`을 올린다.
**이걸 빼먹으면 Cowork 쪽에 업데이트가 가지 않는다** — 로컬에서만 잘 되고 Cowork에선 옛날 스킬이 도는 상태가 되는데, 증상이 조용해서 알아채기 어렵다.

- 스킬 내용만 고침 → patch (1.0.0 → 1.0.1)
- 스킬 추가/삭제 → minor (1.0.0 → 1.1.0)

### 3. 커밋 & 푸시

```bash
git -C C:/Users/biy06/my-skills add -A
git -C C:/Users/biy06/my-skills commit -m "<메시지>"
git -C C:/Users/biy06/my-skills push
```

커밋 메시지는 인자로 받은 것을 쓰고, 없으면 변경 내용을 보고 한 줄로 직접 작성한다.

`push`가 remote 없음으로 실패하면 아직 GitHub에 연결하지 않은 상태다. 커밋까지만 된 것을 알리고, remote 추가 명령을 안내한다:

```bash
git -C C:/Users/biy06/my-skills remote add origin <URL>
git -C C:/Users/biy06/my-skills push -u origin main
```

## 완료 후

Cowork·claude.ai 쪽은 세션 시작 시점에 동기화된다. 이미 열려 있는 Cowork 세션에는 즉시 반영되지 않으니, 바로 확인하려면 새 세션을 열어야 한다.
