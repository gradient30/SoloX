# Android 录屏真机验收 — Windows（与 accept_record.sh 等价）
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path $ScriptDir "lib"
. (Join-Path $LibDir "python.ps1")
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

$Python = Get-SoloXPython

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Android 录屏真机验收" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
    Write-Host "❌ 未找到 adb，请先安装 Android platform-tools" -ForegroundColor Red
    exit 1
}

$deviceCount = & $Python -c @"
import sys
sys.path.insert(0, 'scripts')
from accept_record_gate import list_android_device_ids
print(len(list_android_device_ids()))
"@

if ([int]$deviceCount -lt 1) {
    Write-Host "❌ 无已连接的 Android 设备（adb devices）" -ForegroundColor Red
    exit 1
}

Write-Host "▶ 已连接 Android 设备数: $deviceCount"
Write-Host "▶ 请确保 SoloX 已启动（默认 http://127.0.0.1:50003）"
Write-Host ""

& $Python scripts/accept_record_gate.py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
