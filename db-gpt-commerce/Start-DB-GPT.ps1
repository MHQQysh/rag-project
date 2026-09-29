$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskPython = Join-Path $PSScriptRoot '.official-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run Install-Official.ps1 first.' }
try {
    $taskModels = Invoke-RestMethod 'http://127.0.0.1:5670/api/controller/models' -TimeoutSec 2
    if ($taskModels | Where-Object { $_.model_name -eq 'deepseek-flash@llm' -and $_.healthy }) {
        Write-Host 'DB-GPT is ready: http://127.0.0.1:5670'
        exit 0
    }
} catch {}
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList 'run_official.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'official-server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'official-error.log') -PassThru
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'official-server.pid')
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($taskProcess.HasExited) { throw 'DB-GPT exited; inspect official-error.log.' }
    try {
        $taskModels = Invoke-RestMethod 'http://127.0.0.1:5670/api/controller/models' -TimeoutSec 1
        if ($taskModels | Where-Object { $_.model_name -eq 'deepseek-flash@llm' -and $_.healthy }) {
            Write-Host 'DB-GPT is ready: http://127.0.0.1:5670'
            exit 0
        }
    } catch {}
}
throw 'Startup timed out; inspect official-error.log.'
