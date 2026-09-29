$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run Install-Commerce.ps1 first.' }
try {
    $health = Invoke-RestMethod 'http://127.0.0.1:5678/api/health' -TimeoutSec 2
    if ($health.framework -eq 'DB-GPT AWEL') { Write-Host 'Already running: http://127.0.0.1:5678'; exit 0 }
} catch {}
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList '-m','uvicorn','commerce.main:app','--host','127.0.0.1','--port','5678' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'server-error.log') -PassThru
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'server.pid')
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($taskProcess.HasExited) { throw 'Server exited; inspect server-error.log.' }
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:5678/api/health' -TimeoutSec 1
        if ($health.framework -eq 'DB-GPT AWEL') { Write-Host 'Ready: http://127.0.0.1:5678'; exit 0 }
    } catch {}
}
throw 'Server startup timed out; inspect server-error.log.'
