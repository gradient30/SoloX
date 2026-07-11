# 解析可在 PowerShell 中直接调用的 Python 路径
function Get-SoloXPython {
    $candidate = $env:SOLOX_PYTHON
    if ($candidate) {
        if ($candidate -match '^/[a-zA-Z]') {
            # dev.ps1 可能设置 Git Bash 风格路径（/c/...），PowerShell 无法直接执行
            $winPy = Get-Command python -ErrorAction SilentlyContinue
            if ($winPy) { return $winPy.Source }
        } elseif (Test-Path $candidate) {
            return $candidate
        }
    }

    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }

    foreach ($path in @(
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )) {
        if (Test-Path $path) { return $path }
    }

    return "python"
}
