$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskCommit = 'ca9f014cb3ead157ca2ee6ce645658f5fb55138c'
$taskVendor = Join-Path $PSScriptRoot 'vendor/DB-GPT'
if (-not (Test-Path -LiteralPath $taskVendor)) {
    git clone https://github.com/eosphoros-ai/DB-GPT.git $taskVendor
    if ($LASTEXITCODE -ne 0) { throw 'Official source download failed.' }
    git -C $taskVendor checkout $taskCommit
    if ($LASTEXITCODE -ne 0) { throw 'Cannot select pinned upstream version.' }
}
$taskActualCommit = git -C $taskVendor rev-parse HEAD
if ($taskActualCommit -ne $taskCommit) { throw 'Existing vendor checkout differs from pinned version; preserve it and inspect manually.' }
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    uv venv --python 3.11 (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
uv pip install --python $taskPython -r (Join-Path $PSScriptRoot 'requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
# Build a regular wheel: editable .pth paths in Chinese directories fail on this Windows Python build.
uv pip install --python $taskPython --no-deps (Join-Path $taskVendor 'packages/dbgpt-core')
if ($LASTEXITCODE -ne 0) { throw 'DB-GPT core installation failed.' }
Push-Location $PSScriptRoot
try {
    & $taskPython -m commerce.cli --mode reference
    if ($LASTEXITCODE -ne 0) { throw 'Reference workflow failed.' }
} finally { Pop-Location }
Write-Host 'Installed and verified. Run Start-Commerce.cmd.'
