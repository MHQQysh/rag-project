param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$taskSshKey = Join-Path $env:USERPROFILE '.ssh/deerflow_ecs_ed25519'
if (-not (Test-Path -LiteralPath $taskSshKey)) { throw 'SSH key not found. Use the computer configured for this server.' }
$taskPort = 25670
$taskListener = Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue
if (-not $taskListener) {
    $taskSsh = (Get-Command ssh.exe).Source
    $taskArguments = @('-N', '-L', '127.0.0.1:25670:127.0.0.1:5670', '-i', ('"' + $taskSshKey + '"'), '-o', 'StrictHostKeyChecking=yes', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30', '-o', 'ConnectTimeout=15', 'root@39.105.124.8')
    $taskProcess = Start-Process -FilePath $taskSsh -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
    for ($taskAttempt=0; $taskAttempt -lt 20; $taskAttempt++) {
        Start-Sleep -Milliseconds 500
        if ($taskProcess.HasExited) { throw 'SSH connection failed. Check the server connection first.' }
        if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) { break }
    }
} else {
    $taskOwner = Get-Process -Id $taskListener[0].OwningProcess
    if ($taskOwner.ProcessName -ne 'ssh') { throw 'Port 25670 is occupied by another program.' }
}
$taskResponse = Invoke-WebRequest -Uri 'http://127.0.0.1:25670/' -TimeoutSec 30
if ($taskResponse.StatusCode -ne 200 -or $taskResponse.Content -notmatch 'DB-GPT') { throw 'The remote DB-GPT interface is not ready yet.' }
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:25670/' }
Write-Host 'Cloud DB-GPT opened. Keep the server running; no local Python environment is needed.'
