# SoloX 发版门禁（Windows）— 与 release_gate.sh 等价
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path $ScriptDir "lib"
. (Join-Path $LibDir "python.ps1")
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

$Python = Get-SoloXPython

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SoloX 发版门禁" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "▶ [1/3] 校验 setup.py 依赖版本" -ForegroundColor Yellow
& $Python scripts/verify_setup.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "▶ [2/3] 校验兼容矩阵" -ForegroundColor Yellow
& $Python scripts/validate_compatibility_matrix.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "▶ [3/3] 运行全量测试" -ForegroundColor Yellow
& $Python -m pytest tests/ -q --disable-warnings --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "✅ 发版门禁通过" -ForegroundColor Green
