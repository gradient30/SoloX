# 查找 Git for Windows 自带的 bash.exe（排除 WSL / WindowsApps）
function Get-SoloXGitBash {
    if ($env:GIT_BASH -and (Test-Path $env:GIT_BASH)) {
        return $env:GIT_BASH
    }

    $gitExe = Get-Command git -ErrorAction SilentlyContinue
    if ($gitExe) {
        $gitDir = Split-Path (Split-Path $gitExe.Source)
        foreach ($rel in @("bin\bash.exe", "usr\bin\bash.exe")) {
            $candidate = Join-Path $gitDir $rel
            if (Test-Path $candidate) { return $candidate }
        }
    }

    foreach ($path in @(
        "$env:ProgramFiles\Git\bin\bash.exe",
        "$env:ProgramFiles\Git\usr\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
        "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe",
        "C:\Git\bin\bash.exe"
    )) {
        if (Test-Path $path) { return $path }
    }

    foreach ($b in (Get-Command bash.exe -All -ErrorAction SilentlyContinue)) {
        $src = $b.Source
        if ($src -notmatch 'System32' -and $src -notmatch 'WindowsApps') {
            return $src
        }
    }

    return $null
}
