# SoloX 依赖安装 — 调用跨平台 Python 脚本
# 用法: .\scripts\install_dependencies.ps1 [-Dev]
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path $ScriptDir "lib"
. (Join-Path $LibDir "python.ps1")
$Py = Get-SoloXPython

$argsList = @("--user")
if ($Dev) { $argsList += "--dev" }

& $Py (Join-Path $ScriptDir "install_dependencies.py") @argsList
exit $LASTEXITCODE
