[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GradleTasks = @('testDebugUnitTest', 'assembleDebug')
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ToolRoot = Join-Path $RepoRoot 'runtime\android-toolchain'
$JavaHome = Join-Path $ToolRoot 'jdk-stage\jdk-17.0.19+10'
$AndroidSdkRoot = Join-Path $ToolRoot 'android-sdk'
$AgentRoot = Join-Path $RepoRoot 'android-agent'
$GradleExecutable = Join-Path $ToolRoot 'gradle-8.13\bin\gradle.bat'
$Aapt2Executable = Join-Path $AndroidSdkRoot 'build-tools\36.0.0\aapt2.exe'
$RustSysroot = Join-Path $ToolRoot 'rust-sysroot'
$RustDownloads = Join-Path $ToolRoot 'downloads\rust'
$NdkBin = Join-Path $AndroidSdkRoot 'ndk\29.0.14206865\toolchains\llvm\prebuilt\windows-x86_64\bin'

foreach ($required in (
    (Join-Path $JavaHome 'bin\java.exe'),
    (Join-Path $AndroidSdkRoot 'platforms\android-36'),
    $Aapt2Executable,
    $GradleExecutable
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Android toolchain is incomplete. Run scripts/android_agent/bootstrap.ps1 first. Missing: $required"
    }
}

$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $AndroidSdkRoot
$env:ANDROID_SDK_ROOT = $AndroidSdkRoot
$env:GRADLE_USER_HOME = Join-Path $ToolRoot 'gradle-user-home'
$env:PATH = "$(Join-Path $JavaHome 'bin');$env:PATH"

$BuildNative = $false
$FilteredGradleTasks = @()
foreach ($task in $GradleTasks) {
    if ($task -eq 'native') {
        $BuildNative = $true
    } else {
        $FilteredGradleTasks += $task
    }
}
if ($FilteredGradleTasks.Count -eq 0) {
    $FilteredGradleTasks = @('testDebugUnitTest', 'assembleDebug')
}

function Build-NativeLibraries {
    foreach ($required in (
        (Join-Path $RustSysroot 'lib\rustlib\aarch64-linux-android\lib'),
        (Join-Path $RustSysroot 'lib\rustlib\x86_64-linux-android\lib'),
        (Join-Path $RustDownloads 'rust-std-1.93.0-aarch64-linux-android.tar.xz'),
        (Join-Path $RustDownloads 'rust-std-1.93.0-x86_64-linux-android.tar.xz'),
        (Join-Path $NdkBin 'aarch64-linux-android35-clang.cmd'),
        (Join-Path $NdkBin 'x86_64-linux-android35-clang.cmd')
    )) {
        if (-not (Test-Path -LiteralPath $required)) {
            throw "Android native toolchain is incomplete. Missing: $required"
        }
    }

    $PreviousRustFlags = $env:RUSTFLAGS
    $PreviousArm64Linker = $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER
    $PreviousX64Linker = $env:CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER
    try {
        $env:RUSTFLAGS = "--sysroot=$RustSysroot"
        $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER = Join-Path $NdkBin 'aarch64-linux-android35-clang.cmd'
        $env:CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER = Join-Path $NdkBin 'x86_64-linux-android35-clang.cmd'

        $NativeManifest = Join-Path $AgentRoot 'native\Cargo.toml'
        cargo build --manifest-path $NativeManifest --target aarch64-linux-android
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build failed for aarch64-linux-android with exit code $LASTEXITCODE"
        }
        cargo build --manifest-path $NativeManifest --target x86_64-linux-android
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build failed for x86_64-linux-android with exit code $LASTEXITCODE"
        }

        $Arm64Out = Join-Path $AgentRoot 'app\src\main\jniLibs\arm64-v8a'
        $X64Out = Join-Path $AgentRoot 'app\src\main\jniLibs\x86_64'
        New-Item -ItemType Directory -Force -Path $Arm64Out, $X64Out | Out-Null
        Copy-Item -LiteralPath (Join-Path $AgentRoot 'native\target\aarch64-linux-android\debug\libsolox_network_agent_native.so') -Destination $Arm64Out -Force
        Copy-Item -LiteralPath (Join-Path $AgentRoot 'native\target\x86_64-linux-android\debug\libsolox_network_agent_native.so') -Destination $X64Out -Force
    } finally {
        $env:RUSTFLAGS = $PreviousRustFlags
        $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER = $PreviousArm64Linker
        $env:CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER = $PreviousX64Linker
    }
}

$LocalProperties = Join-Path $AgentRoot 'local.properties'
$SdkDirForGradle = $AndroidSdkRoot.Replace('\', '/')
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($LocalProperties, "sdk.dir=$SdkDirForGradle`n", $Utf8NoBom)

if ($BuildNative) {
    Build-NativeLibraries
}

$NativeCache = Join-Path $env:GRADLE_USER_HOME 'native'
if (Test-Path -LiteralPath $NativeCache) {
    Remove-Item -LiteralPath $NativeCache -Recurse -Force
}

Push-Location $AgentRoot
try {
    & $GradleExecutable --no-daemon "-Pandroid.aapt2FromMavenOverride=$Aapt2Executable" @FilteredGradleTasks
    if ($LASTEXITCODE -ne 0) {
        throw "Android Agent Gradle build failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

