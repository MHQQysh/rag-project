$ErrorActionPreference = 'Stop'
$taskPidFile = Join-Path $PSScriptRoot 'official-server.pid'
if (-not (Test-Path -LiteralPath $taskPidFile)) { Write-Host 'No managed DB-GPT PID.'; exit 0 }
$taskServerPid = [int](Get-Content -LiteralPath $taskPidFile)
$taskProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$taskServerPid"
$taskExpectedPython = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.official-venv/Scripts/python.exe'))
if ($taskProcessInfo -and $taskProcessInfo.ExecutablePath -eq $taskExpectedPython -and $taskProcessInfo.CommandLine -match 'run_official.py') {
    Stop-Process -Id $taskServerPid
    Remove-Item -LiteralPath $taskPidFile
    Write-Host 'DB-GPT stopped.'
} elseif (-not $taskProcessInfo) { Remove-Item -LiteralPath $taskPidFile }
else { throw 'PID belongs to a different process; refusing to stop it.' }
