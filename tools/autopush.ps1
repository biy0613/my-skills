# Auto-commit and push skill changes.
# Called from the Claude Code SessionEnd hook. Never blocks the session (always exit 0).
#
# ASCII-only on purpose: Windows PowerShell 5.1 reads unmarked files as the system
# codepage, so non-ASCII characters here would break parsing before anything runs.
# For the same reason every file read/write below names UTF-8 explicitly -- letting
# PowerShell guess silently corrupts the Korean text in plugin.json.

$ErrorActionPreference = "Continue"
$repo = "C:\Users\biy06\my-skills"
$log  = Join-Path $repo "tools\autopush.log"
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg`r`n"
    [System.IO.File]::AppendAllText($log, $line, $utf8)
}

try {
    if (-not (Test-Path $repo)) { exit 0 }

    $changes = & git -C $repo status --porcelain 2>$null
    if (-not $changes) { exit 0 }

    # Bump the patch version when skill files changed. Without this the local copy is
    # current but Cowork keeps serving the old skills, and the failure is silent.
    if ($changes -match "plugins/inyup-skills/skills/") {
        $pj = Join-Path $repo "plugins\inyup-skills\.claude-plugin\plugin.json"
        $raw = [System.IO.File]::ReadAllText($pj, $utf8)
        if ($raw -match '"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"') {
            $new = "{0}.{1}.{2}" -f $Matches[1], $Matches[2], ([int]$Matches[3] + 1)
            $out = $raw -replace '"version"\s*:\s*"\d+\.\d+\.\d+"', ('"version": "' + $new + '"')
            [System.IO.File]::WriteAllText($pj, $out, $utf8)
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

    # Rebuild the uploadable .skill bundles. Cowork cannot sync a private repo unless the
    # Claude GitHub App is installed on it, so hand-uploading these is the working
    # fallback -- and a stale bundle silently uploads an old version of the skill.
    $dist = Join-Path $repo "dist"
    if (-not (Test-Path $dist)) { New-Item -ItemType Directory -Path $dist -Force | Out-Null }
    $skillRoot = Join-Path $repo "plugins\inyup-skills\skills"
    foreach ($d in Get-ChildItem $skillRoot -Directory) {
        $zip = Join-Path $dist ($d.Name + ".zip")
        $out = Join-Path $dist ($d.Name + ".skill")
        if (Test-Path $zip) { Remove-Item $zip -Force }
        if (Test-Path $out) { Remove-Item $out -Force }
        Compress-Archive -Path $d.FullName -DestinationPath $zip -Force
        Rename-Item $zip ($d.Name + ".skill")
    }
    # Whole-plugin bundle: one upload installs all skills at once on the Cowork
    # Plugins page. Kept in sync for the same reason as the .skill bundles above.
    $pzip = Join-Path $dist "inyup-skills.zip"
    $pout = Join-Path $dist "inyup-skills.plugin"
    if (Test-Path $pzip) { Remove-Item $pzip -Force }
    if (Test-Path $pout) { Remove-Item $pout -Force }
    Compress-Archive -Path (Join-Path $repo "plugins\inyup-skills") -DestinationPath $pzip -Force
    Rename-Item $pzip "inyup-skills.plugin"

    Write-Log "rebuilt dist bundles"
}
catch {
    Write-Log "EXCEPTION: $_"
}

exit 0
