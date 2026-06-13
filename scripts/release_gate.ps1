# SoloX release gate — matrix validation + full pytest (Windows)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

$Python = if ($env:SOLOX_PYTHON) { $env:SOLOX_PYTHON } else { "python" }

Write-Host "==> [1/2] validate_compatibility_matrix"
& $Python scripts/validate_compatibility_matrix.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [2/2] pytest tests/"
& $Python -m pytest tests/ -q --disable-warnings --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: release gate passed"
