$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$shell = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
if (-not $shell) {
    $shell = (Get-Command powershell.exe).Source
}

$basicScript = '"' + (Join-Path $projectRoot "run-basic-offline.ps1") + '"'
$adaptiveScript = '"' + (Join-Path $projectRoot "run-adaptive-offline.ps1") + '"'

Start-Process -FilePath $shell `
    -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $basicScript) `
    -WorkingDirectory $projectRoot `
    -WindowStyle Normal

Start-Process -FilePath $shell `
    -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $adaptiveScript) `
    -WorkingDirectory $projectRoot `
    -WindowStyle Normal
