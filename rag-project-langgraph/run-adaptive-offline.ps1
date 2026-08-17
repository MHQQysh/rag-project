$ErrorActionPreference = "Stop"
$env:RAG_OFFLINE_MODE = "1"
$env:PYTHONUTF8 = "1"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:HF_HOME = "$PSScriptRoot\.cache\huggingface"
$env:TORCH_HOME = "$PSScriptRoot\.cache\torch"
$env:XDG_CACHE_HOME = "$PSScriptRoot\.cache"
$env:TEMP = "$PSScriptRoot\.tmp"
$env:TMP = "$PSScriptRoot\.tmp"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
& "$PSScriptRoot\.venv\Scripts\python.exe" -m graph2.graph_2
