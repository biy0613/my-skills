# Auto-commit and push skill changes.
# Called from the Claude Code SessionEnd hook. Never blocks the session (always exit 0).
#
# ASCII-only on purpose: Windows PowerShell 5.1 reads unmarked files as the system
# codepage, so non-ASCII characters here would break parsing before anything runs.

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

    # Bump the patch version when skill files changed. Without this the local copy is
    # current but Cowork keeps serving the old skills, and the failure is silent.
    if ($changes -match "plugins/inyup-skills/skills/") {
        $pj = Join-Path $repo "plugins\inyup-skills\.claude-plugin\plugin.json"
        $raw = Get-Content $pj -Raw
        if ($raw -match '"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"') {
            $new = "{0}.{1}.{2}" -f $Matches[1], $Matches[2], ([int]$Matches[3] + 1)
            $raw = $raw -replace '"version"\s*:\s*"\d+\.\d+\.\d+"', ('"version": "' + $new + '"')
            [System.IO.File]::WriteAllText($pj, $raw)
            Write-Log "version bumped to $new"
        }
    }

    & git -C $repo add -A 2>$null
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git -C $repo commit -m "auto: skill sync ($stamp)" 2>&1 | Out-Null

    $pushOut = & git -C $repo push 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "PUSH FAILED (commit is saved locally): $pushOut"
    } else {
        Write-Log "pushed OK"
    }
}
catch {
    Write-Log "EXCEPTION: $_"
}

exit 0
