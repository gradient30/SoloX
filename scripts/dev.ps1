# =============================================================================
# SoloX 开发服务 — Windows PowerShell 入口（转发至 dev.sh + Git Bash）
# 用法: .\scripts\dev.ps1 start | stop | restart | status | log | fg
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path $ScriptDir "lib"
. (Join-Path $LibDir "git_bash.ps1")

$DevSh = Join-Path $ScriptDir "dev.sh"
$GitBash = Get-SoloXGitBash

if (-not $GitBash) {
    Write-Host "[错误] 未找到 Git Bash。请安装 Git for Windows，或设置环境变量 GIT_BASH。" -ForegroundColor Red
    Write-Host "       https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

if (-not $env:SOLOX_PYTHON) {
    $winPy = $null
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) { $winPy = $pyCmd.Source }
    elseif (Test-Path "C:\Python312\python.exe") { $winPy = "C:\Python312\python.exe" }
    if ($winPy) {
        $escaped = $winPy -replace "'", "''"
        $env:SOLOX_PYTHON = & $GitBash -lc "cygpath -u '$escaped'"
        if (-not $env:SOLOX_PYTHON) { $env:SOLOX_PYTHON = $winPy }
    }
}

if (-not $env:SOLOX_HOST) {
    $env:SOLOX_HOST = "127.0.0.1"
}

if (-not $env:SOLOX_PORT) {
    $cmd = if ($args.Count -gt 0) { $args[0].ToLower() } else { "" }
    if ($cmd -eq "start" -or $cmd -eq "restart" -or $cmd -eq "fg") {
        $port50003 = netstat -ano 2>$null | Select-String ":50003\s+.*LISTENING"
        if ($port50003) {
            $env:SOLOX_PORT = "50005"
            Write-Host "[信息]  端口 50003 已被占用，启动时将使用 SOLOX_PORT=50005" -ForegroundColor Yellow
        }
    }
}

if ($args.Count -eq 0) {
    & $GitBash $DevSh
} else {
    & $GitBash $DevSh @args
}

exit $LASTEXITCODE
