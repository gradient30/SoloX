# =============================================================================
# SoloX Dev Script — PowerShell wrapper for dev.sh
# Automatically locates Git Bash and forwards all arguments
# Usage: .\scripts\dev.ps1 start | stop | restart | status | log | fg
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DevSh = Join-Path $ScriptDir "dev.sh"

# --- Locate Git Bash (not WSL bash) -----------------------------------------
function Find-GitBash {
    # 1) Check git --exec-path based location
    $gitExe = Get-Command git -ErrorAction SilentlyContinue
    if ($gitExe) {
        $gitDir = Split-Path (Split-Path $gitExe.Source)
        $candidate = Join-Path $gitDir "bin\bash.exe"
        if (Test-Path $candidate) { return $candidate }
        # git might be under usr/bin
        $candidate = Join-Path $gitDir "usr\bin\bash.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    # 2) Common install paths
    $candidates = @(
        "$env:ProgramFiles\Git\bin\bash.exe",
        "$env:ProgramFiles\Git\usr\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
        "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe",
        "C:\Git\bin\bash.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }

    # 3) Search PATH, skip WSL bash (System32\bash.exe)
    $allBash = Get-Command bash.exe -All -ErrorAction SilentlyContinue
    foreach ($b in $allBash) {
        $src = $b.Source
        if ($src -notmatch 'System32' -and $src -notmatch 'WindowsApps') {
            return $src
        }
    }

    return $null
}

$GitBash = Find-GitBash

if (-not $GitBash) {
    Write-Host "[ERROR] Git Bash not found. Install Git for Windows or set GIT_BASH env var." -ForegroundColor Red
    Write-Host "        https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Allow override via env var
if ($env:GIT_BASH -and (Test-Path $env:GIT_BASH)) {
    $GitBash = $env:GIT_BASH
}

# --- Windows-friendly defaults (avoid WSL python + YunShu 50003 + 0.0.0.0 probe) ---
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
    $port50003 = netstat -ano 2>$null | Select-String ":50003\s+.*LISTENING"
    if ($port50003) {
        $env:SOLOX_PORT = "50005"
        Write-Host "[INFO]  Port 50003 is in use; defaulting to SOLOX_PORT=50005" -ForegroundColor Yellow
    }
}

# --- Convert Windows path to POSIX for bash ---------------------------------
$PosixSh = $DevSh -replace '\\','/' -replace '^([A-Za-z]):','/$1'.ToLower()
# Simpler: just let bash handle the Windows path directly — Git Bash supports it

# --- Forward to bash ---------------------------------------------------------
$allArgs = $args -join ' '

if ($args.Count -eq 0) {
    & $GitBash $DevSh
} else {
    & $GitBash $DevSh @args
}

exit $LASTEXITCODE
