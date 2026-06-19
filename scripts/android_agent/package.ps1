[CmdletBinding()]
param(
    [switch]$Offline = $true
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$AgentRoot = Join-Path $RepoRoot 'android-agent'
$OutputDir = Join-Path $RepoRoot 'solox\public\android_agent'
$BuildScript = Join-Path $PSScriptRoot 'build.ps1'
$AppBuild = Join-Path $AgentRoot 'app\build.gradle.kts'

$buildText = Get-Content -LiteralPath $AppBuild -Raw
$version = [regex]::Match($buildText, 'versionName\s*=\s*"([^"]+)"').Groups[1].Value
$versionCode = [int][regex]::Match($buildText, 'versionCode\s*=\s*(\d+)').Groups[1].Value
$packageId = [regex]::Match($buildText, 'applicationId\s*=\s*"([^"]+)"').Groups[1].Value
if (-not $version -or -not $versionCode -or -not $packageId) {
    throw "Cannot parse Android Agent version metadata from $AppBuild"
}

$buildArgs = @('native', 'assembleRelease')
if ($Offline) {
    $buildArgs = @('--offline') + $buildArgs
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $BuildScript @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Android Agent release build failed with exit code $LASTEXITCODE"
}

$releaseApk = Join-Path $AgentRoot 'app\build\outputs\apk\release\app-release.apk'
if (-not (Test-Path -LiteralPath $releaseApk)) {
    $releaseApk = Join-Path $AgentRoot 'app\build\outputs\apk\release\app-release-unsigned.apk'
}
if (-not (Test-Path -LiteralPath $releaseApk)) {
    throw "Release APK not found under android-agent/app/build/outputs/apk/release"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$apkName = "qas-network-agent-$version.apk"
$destApk = Join-Path $OutputDir $apkName
Copy-Item -LiteralPath $releaseApk -Destination $destApk -Force

$sha256 = (Get-FileHash -LiteralPath $destApk -Algorithm SHA256).Hash.ToLowerInvariant()
$metadata = [ordered]@{
    version = $version
    version_code = $versionCode
    package_id = $packageId
    min_protocol_version = 1
    apk = $apkName
    sha256 = $sha256
}
$json = $metadata | ConvertTo-Json -Depth 4
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $OutputDir 'checksums.json'), "$json`n", $Utf8NoBom)

Write-Host "Packaged $apkName"
Write-Host "SHA256 $sha256"
