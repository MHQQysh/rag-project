$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskVendor = Join-Path $PSScriptRoot 'vendor/DB-GPT'
$taskCommit = 'ca9f014cb3ead157ca2ee6ce645658f5fb55138c'
if (-not (Test-Path -LiteralPath $taskVendor)) {
    git clone https://github.com/eosphoros-ai/DB-GPT.git $taskVendor
    if ($LASTEXITCODE -ne 0) { throw 'Official source download failed.' }
    git -C $taskVendor checkout $taskCommit
    if ($LASTEXITCODE -ne 0) { throw 'Cannot select pinned upstream version.' }
}
if ((git -C $taskVendor rev-parse HEAD) -ne $taskCommit) { throw 'Vendor version differs; inspect before installing.' }
$taskPatch = Join-Path $PSScriptRoot 'official-patches/registered-business-tools.patch'
git -C $taskVendor apply --reverse --check $taskPatch 2>$null
if ($LASTEXITCODE -ne 0) {
    git -C $taskVendor apply --check $taskPatch
    if ($LASTEXITCODE -ne 0) { throw 'Patch does not apply cleanly; existing checkout preserved.' }
    git -C $taskVendor apply $taskPatch
}
$taskPython = Join-Path $PSScriptRoot '.official-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    uv venv --python 3.11 (Join-Path $PSScriptRoot '.official-venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
uv pip install --python $taskPython -r (Join-Path $PSScriptRoot 'official-requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Official dependency installation failed.' }
$taskPackages = @('dbgpt-core','dbgpt-ext','dbgpt-client','dbgpt-serve','dbgpt-sandbox','dbgpt-accelerator/dbgpt-acc-auto','dbgpt-app')
foreach ($taskPackage in $taskPackages) {
    uv pip install --python $taskPython --no-deps --reinstall (Join-Path $taskVendor "packages/$taskPackage")
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed: $taskPackage" }
}
Write-Host 'Official DB-GPT installed. Run Start-DB-GPT.cmd.'
