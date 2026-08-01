# 스킬 변경분을 자동 커밋·푸시한다.
# Claude Code의 SessionEnd 훅에서 호출된다. 실패해도 절대 세션을 막지 않는다 (항상 exit 0).

$ErrorActionPreference = "Continue"
$repo = "C:\Users\biy06\my-skills"
$log  = Join-Path $repo "tools\autopush.log"

function Write-Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Add-Content -Path $log -Encoding utf8
}

try {
    if (-not (Test-Path $repo)) { exit 0 }

    $changes = & git -C $repo status --porcelain 2>$null
    if (-not $changes) { exit 0 }

    # 스킬 파일이 바뀌었으면 plugin.json 의 patch 버전을 올린다.
    # 이걸 빼먹으면 로컬은 최신인데 Cowork 은 옛 스킬을 계속 쓰는 상태가 되고,
    # 증상이 조용해서 한참 뒤에야 알아채게 된다.
    if ($changes -match "plugins/inyup-skills/skills/") {
        $pj = Join-Path $repo "plugins\inyup-skills\.claude-plugin\plugin.json"
        $raw = Get-Content $pj -Raw -Encoding utf8
        if ($raw -match '"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"') {
            $new = "{0}.{1}.{2}" -f $Matches[1], $Matches[2], ([int]$Matches[3] + 1)
            $raw = $raw -replace '"version"\s*:\s*"\d+\.\d+\.\d+"', ('"version": "' + $new + '"')
            Set-Content -Path $pj -Value $raw -Encoding utf8 -NoNewline
            Write-Log "version -> $new"
        }
    }

    & git -C $repo add -A 2>$null
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git -C $repo commit -m "auto: 스킬 변경 자동 저장 ($stamp)" 2>&1 | Out-Null

    $pushOut = & git -C $repo push 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "PUSH 실패 - 커밋은 로컬에 남아 있음: $pushOut"
    } else {
        Write-Log "푸시 완료: $($changes.Count) 건 변경"
    }
}
catch {
    Write-Log "예외: $_"
}

exit 0
