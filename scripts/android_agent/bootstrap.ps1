[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ToolRoot = Join-Path $RepoRoot 'runtime\android-toolchain'
$DownloadRoot = Join-Path $ToolRoot 'downloads'
$JavaHome = Join-Path $ToolRoot 'jdk-stage\jdk-17.0.19+10'
$AndroidSdkRoot = Join-Path $ToolRoot 'android-sdk'
$GradleHome = Join-Path $ToolRoot 'gradle-8.13'
$AgentRoot = Join-Path $RepoRoot 'android-agent'

$JdkName = 'microsoft-jdk-17.0.19-windows-x64.zip'
$JdkUrl = 'https://aka.ms/download-jdk/' + $JdkName
$JdkSha256 = '394d1d8253d58b462300f15f9c81369478cf8813f82dca914c3b5dfdef080f9f'

$CommandLineToolsName = 'commandlinetools-win-14742923_latest.zip'
$CommandLineToolsUrl = 'https://dl.google.com/android/repository/' + $CommandLineToolsName
# Google currently labels this published 40-hex digest as SHA-256; it is SHA-1.
$CommandLineToolsSha1 = '16b3f45ddb3d85ea6bbe6a1c0b47146daf0db450'
$CommandLineToolsSha256 = 'cc610ccbe83faddb58e1aa68e8fc8743bb30aa5e83577eceb4cc168dae95f9ee'

$GradleName = 'gradle-8.13-bin.zip'
$GradleUrl = 'https://services.gradle.org/distributions/' + $GradleName
$GradleSha256 = '20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78'

$PlatformToolsName = 'platform-tools_r37.0.0-win.zip'
$PlatformToolsUrl = 'https://dl.google.com/android/repository/' + $PlatformToolsName
$PlatformToolsSha1 = 'f29bfb58d0d6f9a57d7dbcba6cc259f9ca6f58f1'
$PlatformToolsSha256 = '4fe305812db074cea32903a489d061eb4454cbc90a49e8fea677f4b7af764918'

$Platform36Name = 'platform-36_r02.zip'
$Platform36Url = 'https://dl.google.com/android/repository/' + $Platform36Name
$Platform36Sha1 = '2c1a80dd4d9f7d0e6dd336ec603d9b5c55a6f576'
$Platform36Sha256 = '37607369a28c5b640b3a7998868d45898ebcb777565a0e85f9acf36f29631d2e'

$BuildTools36Name = 'build-tools_r36_windows.zip'
$BuildTools36Url = 'https://dl.google.com/android/repository/' + $BuildTools36Name
$BuildTools36Sha1 = 'f16ccffd34de8790dede813a6c7d8e2c11a27b50'
$BuildTools36Sha256 = 'aa1095cb14d83e483818a748a2c06faaeb8e601561b06a356a119a1b2ca280d3'

$Ndk29Name = 'android-ndk-r29-windows.zip'
$Ndk29Url = 'https://dl.google.com/android/repository/' + $Ndk29Name
$Ndk29Sha1 = 'ab3bb30fbb9e6903666d60c55d11e78b04e07472'
$Ndk29Sha256 = '4f83a1a87ea0d33ae2b43812ce27b768be949bc78acf90b955134d19e3068f1c'

function Assert-PathUnderToolRoot {
    param([Parameter(Mandatory = $true)][string]$Path)
    $rootTrimmed = [IO.Path]::GetFullPath($ToolRoot).TrimEnd('\')
    $rootWithSeparator = $rootTrimmed + '\'
    $candidateTrimmed = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if (
        $candidateTrimmed -ne $rootTrimmed -and
        -not $candidateTrimmed.StartsWith(
            $rootWithSeparator,
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Refusing to modify path outside Android tool root: $candidateTrimmed"
    }
}

function Assert-PathUnderDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Directory
    )
    $directoryTrimmed = [IO.Path]::GetFullPath($Directory).TrimEnd('\')
    $directoryWithSeparator = $directoryTrimmed + '\'
    $candidateTrimmed = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if (
        $candidateTrimmed -ne $directoryTrimmed -and
        -not $candidateTrimmed.StartsWith(
            $directoryWithSeparator,
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Refusing to extract outside destination: $candidateTrimmed"
    }
}

function Assert-FileHash {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Algorithm,
        [Parameter(Mandatory = $true)][string]$Expected
    )
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm $Algorithm).Hash.ToLowerInvariant()
    if ($actual -ne $Expected.ToLowerInvariant()) {
        throw "$Algorithm mismatch for $Path. Expected $Expected, got $actual"
    }
}

function Expand-ZipPrefix {
    param(
        [Parameter(Mandatory = $true)][string]$Archive,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$ExpectedChild
    )
    Assert-PathUnderToolRoot $Destination
    if (Test-Path -LiteralPath (Join-Path $Destination $ExpectedChild)) {
        return
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $normalizedPrefix = $Prefix.TrimEnd('/') + '/'
    $archiveHandle = [System.IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        foreach ($entry in $archiveHandle.Entries) {
            if (-not $entry.FullName.StartsWith(
                $normalizedPrefix,
                [StringComparison]::Ordinal
            )) {
                continue
            }
            $relativePath = $entry.FullName.Substring($normalizedPrefix.Length)
            if ([string]::IsNullOrWhiteSpace($relativePath)) {
                continue
            }
            $relativePath = $relativePath.Replace('/', [IO.Path]::DirectorySeparatorChar)
            $target = Join-Path $Destination $relativePath
            Assert-PathUnderDirectory -Path $target -Directory $Destination
            if ($entry.FullName.EndsWith('/')) {
                New-Item -ItemType Directory -Force -Path $target | Out-Null
                continue
            }
            New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile(
                $entry,
                $target,
                $true
            )
        }
    } finally {
        $archiveHandle.Dispose()
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Destination $ExpectedChild))) {
        throw "Archive $Archive did not install expected file: $ExpectedChild"
    }
}

function Get-VerifiedDownload {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Sha256,
        [string]$Sha1
    )
    $destination = Join-Path $DownloadRoot $Name
    $partial = "$destination.partial"
    Assert-PathUnderToolRoot $destination
    if (-not (Test-Path -LiteralPath $destination)) {
        if (Test-Path -LiteralPath $partial) {
            Remove-Item -LiteralPath $partial -Force
        }
        & curl.exe -L --fail --retry 3 --output $partial $Url
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed: $Url"
        }
        Move-Item -LiteralPath $partial -Destination $destination
    }
    Assert-FileHash -Path $destination -Algorithm SHA256 -Expected $Sha256
    if ($Sha1) {
        Assert-FileHash -Path $destination -Algorithm SHA1 -Expected $Sha1
    }
    return $destination
}

function Install-VerifiedZipPrefix {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Sha1,
        [Parameter(Mandatory = $true)][string]$Sha256,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$ExpectedChild
    )
    $archive = Get-VerifiedDownload `
        -Url $Url `
        -Name $Name `
        -Sha256 $Sha256 `
        -Sha1 $Sha1
    Expand-ZipPrefix `
        -Archive $archive `
        -Prefix $Prefix `
        -Destination $Destination `
        -ExpectedChild $ExpectedChild
}

function Expand-VerifiedArchive {
    param(
        [Parameter(Mandatory = $true)][string]$Archive,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$ExpectedChild
    )
    Assert-PathUnderToolRoot $Destination
    if (Test-Path -LiteralPath (Join-Path $Destination $ExpectedChild)) {
        return
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force
}

New-Item -ItemType Directory -Force -Path $DownloadRoot | Out-Null

$jdkArchive = Get-VerifiedDownload -Url $JdkUrl -Name $JdkName -Sha256 $JdkSha256
if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) {
    $jdkStage = Join-Path $ToolRoot 'jdk-stage'
    Assert-PathUnderToolRoot $jdkStage
    New-Item -ItemType Directory -Force -Path $jdkStage | Out-Null
    Expand-Archive -LiteralPath $jdkArchive -DestinationPath $jdkStage -Force
    if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) {
        throw "JDK archive did not contain the expected directory: $JavaHome"
    }
}

$toolsArchive = Get-VerifiedDownload `
    -Url $CommandLineToolsUrl `
    -Name $CommandLineToolsName `
    -Sha256 $CommandLineToolsSha256 `
    -Sha1 $CommandLineToolsSha1
$commandLineTools = Join-Path $ToolRoot 'cmdline-tools-stage\cmdline-tools'
if (-not (Test-Path -LiteralPath (Join-Path $commandLineTools 'bin\sdkmanager.bat'))) {
    $toolsStage = Join-Path $ToolRoot 'cmdline-tools-stage'
    Assert-PathUnderToolRoot $toolsStage
    New-Item -ItemType Directory -Force -Path $toolsStage | Out-Null
    Expand-Archive -LiteralPath $toolsArchive -DestinationPath $toolsStage -Force
    if (-not (Test-Path -LiteralPath (Join-Path $commandLineTools 'bin\sdkmanager.bat'))) {
        throw "Command-line tools archive did not contain: $commandLineTools"
    }
}

$gradleArchive = Get-VerifiedDownload -Url $GradleUrl -Name $GradleName -Sha256 $GradleSha256
Expand-VerifiedArchive `
    -Archive $gradleArchive `
    -Destination $ToolRoot `
    -ExpectedChild 'gradle-8.13\bin\gradle.bat'

$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $AndroidSdkRoot
$env:ANDROID_SDK_ROOT = $AndroidSdkRoot
$env:PATH = "$(Join-Path $JavaHome 'bin');$env:PATH"

$licenses = Join-Path $AndroidSdkRoot 'licenses'
New-Item -ItemType Directory -Force -Path $licenses | Out-Null
Set-Content `
    -LiteralPath (Join-Path $licenses 'android-sdk-license') `
    -Encoding ASCII `
    -Value @(
        '8933bad161af4178b1185d1a37fbf41ea5269c55',
        'd56f5187479451eabf01fb78af6dfcb131a6481e'
    )

Install-VerifiedZipPrefix `
    -Name $PlatformToolsName `
    -Url $PlatformToolsUrl `
    -Sha1 $PlatformToolsSha1 `
    -Sha256 $PlatformToolsSha256 `
    -Prefix 'platform-tools/' `
    -Destination (Join-Path $AndroidSdkRoot 'platform-tools') `
    -ExpectedChild 'adb.exe'

Install-VerifiedZipPrefix `
    -Name $Platform36Name `
    -Url $Platform36Url `
    -Sha1 $Platform36Sha1 `
    -Sha256 $Platform36Sha256 `
    -Prefix 'android-36/' `
    -Destination (Join-Path $AndroidSdkRoot 'platforms\android-36') `
    -ExpectedChild 'android.jar'

Install-VerifiedZipPrefix `
    -Name $BuildTools36Name `
    -Url $BuildTools36Url `
    -Sha1 $BuildTools36Sha1 `
    -Sha256 $BuildTools36Sha256 `
    -Prefix 'android-16/' `
    -Destination (Join-Path $AndroidSdkRoot 'build-tools\36.0.0') `
    -ExpectedChild 'aapt2.exe'

Install-VerifiedZipPrefix `
    -Name $Ndk29Name `
    -Url $Ndk29Url `
    -Sha1 $Ndk29Sha1 `
    -Sha256 $Ndk29Sha256 `
    -Prefix 'android-ndk-r29/' `
    -Destination (Join-Path $AndroidSdkRoot 'ndk\29.0.14206865') `
    -ExpectedChild 'ndk-build.cmd'

$escapedSdk = $AndroidSdkRoot.Replace('\', '\\')
Set-Content -LiteralPath (Join-Path $AgentRoot 'local.properties') `
    -Encoding ASCII `
    -Value "sdk.dir=$escapedSdk"

& (Join-Path $GradleHome 'bin\gradle.bat') -p $AgentRoot wrapper
if ($LASTEXITCODE -ne 0) {
    throw 'Gradle wrapper generation failed'
}

Write-Host "Android Agent toolchain ready at $ToolRoot"
