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
