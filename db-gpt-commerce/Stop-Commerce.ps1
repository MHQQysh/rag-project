$ErrorActionPreference = 'Stop'
$taskPidFile = Join-Path $PSScriptRoot 'server.pid'
if (-not (Test-Path -LiteralPath $taskPidFile)) { Write-Host 'No managed server PID.'; exit 0 }
$taskServerPid = [int](Get-Content -LiteralPath $taskPidFile)
$taskProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$taskServerPid"
$taskExpectedPython = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.venv/Scripts/python.exe'))
if ($taskProcessInfo -and $taskProcessInfo.ExecutablePath -eq $taskExpectedPython -and $taskProcessInfo.CommandLine -match 'commerce.main:app') {
    Stop-Process -Id $taskServerPid
    Remove-Item -LiteralPath $taskPidFile
    Write-Host 'Commerce server stopped.'
} elseif (-not $taskProcessInfo) { Remove-Item -LiteralPath $taskPidFile }
else { throw 'PID belongs to a different process; refusing to stop it.' }
