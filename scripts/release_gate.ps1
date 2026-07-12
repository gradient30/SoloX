# SoloX 发版门禁（Windows）— 与 release_gate.sh 等价
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path $ScriptDir "lib"
. (Join-Path $LibDir "python.ps1")
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

$Python = Get-SoloXPython
$RecordAccept = if ($env:SOLOX_RECORD_ACCEPT) { $env:SOLOX_RECORD_ACCEPT } else { "0" }
$Total = if ($RecordAccept -eq "1") { 4 } else { 3 }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SoloX 发版门禁" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "▶ [1/$Total] 校验 pyproject.toml 依赖版本" -ForegroundColor Yellow
& $Python scripts/verify_setup.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "▶ [2/$Total] 校验兼容矩阵" -ForegroundColor Yellow
& $Python scripts/validate_compatibility_matrix.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "▶ [3/$Total] 运行全量测试" -ForegroundColor Yellow
& $Python -m pytest tests/ -q --disable-warnings --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RecordAccept -eq "1") {
    Write-Host ""
    Write-Host "▶ [4/$Total] Android 录屏真机验收（SOLOX_RECORD_ACCEPT=1）" -ForegroundColor Yellow
    & (Join-Path $ScriptDir "accept_record.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host ""
    Write-Host "ℹ️  跳过录屏真机验收（动过录屏链路时请: `$env:SOLOX_RECORD_ACCEPT='1'; .\scripts\release_gate.ps1" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "✅ 发版门禁通过" -ForegroundColor Green
