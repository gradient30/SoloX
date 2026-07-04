[CmdletBinding()]
param()

Set-StrictMode -Version Latest

function Get-ProjectAndroidToolchainRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return Join-Path $RepoRoot 'runtime\android-toolchain'
}

function Get-DefaultSharedAndroidToolchainRoot {
    if (-not $env:LOCALAPPDATA) {
        return $null
    }
    return Join-Path $env:LOCALAPPDATA 'SoloX\toolchains\android-rust'
}

function Get-AndroidToolchainLayout {
    param([Parameter(Mandatory = $true)][string]$ToolRoot)

    $resolvedRoot = [IO.Path]::GetFullPath($ToolRoot)
    return @{
        ToolRoot = $resolvedRoot
        DownloadRoot = Join-Path $resolvedRoot 'downloads'
        JavaHome = Join-Path $resolvedRoot 'jdk-stage\jdk-17.0.19+10'
        AndroidSdkRoot = Join-Path $resolvedRoot 'android-sdk'
        GradleHome = Join-Path $resolvedRoot 'gradle-8.13'
        RustSysroot = Join-Path $resolvedRoot 'rust-sysroot'
        RustDownloads = Join-Path $resolvedRoot 'downloads\rust'
        CargoVendorRoot = Join-Path $resolvedRoot 'downloads\cargo-vendor'
    }
}

function Test-AndroidToolchainRoot {
    param(
        [Parameter(Mandatory = $true)][string]$ToolRoot,
        [switch]$RequireCargoVendor,
        [switch]$RequireRust
    )

    if (-not $ToolRoot) {
        return $false
    }

    $layout = Get-AndroidToolchainLayout -ToolRoot $ToolRoot
    $required = @(
        (Join-Path $layout.JavaHome 'bin\java.exe'),
        (Join-Path $layout.AndroidSdkRoot 'platforms\android-36\android.jar'),
        (Join-Path $layout.AndroidSdkRoot 'build-tools\36.0.0\aapt2.exe'),
        (Join-Path $layout.AndroidSdkRoot 'ndk\29.0.14206865\toolchains\llvm\prebuilt\windows-x86_64\bin\aarch64-linux-android35-clang.cmd'),
        (Join-Path $layout.AndroidSdkRoot 'ndk\29.0.14206865\toolchains\llvm\prebuilt\windows-x86_64\bin\x86_64-linux-android35-clang.cmd'),
        (Join-Path $layout.GradleHome 'bin\gradle.bat')
    )

    if ($RequireRust) {
        $required += @(
            (Join-Path $layout.RustSysroot 'lib\rustlib\aarch64-linux-android\lib'),
            (Join-Path $layout.RustSysroot 'lib\rustlib\x86_64-linux-android\lib'),
            (Join-Path $layout.RustDownloads 'rust-std-1.93.0-aarch64-linux-android.tar.xz'),
            (Join-Path $layout.RustDownloads 'rust-std-1.93.0-x86_64-linux-android.tar.xz')
        )
    }

    if ($RequireCargoVendor) {
        $required += $layout.CargoVendorRoot
    }

    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            return $false
        }
    }

    return $true
}

function Resolve-AndroidToolchainRoot {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [switch]$SkipValidation,
        [switch]$RequireCargoVendor,
        [switch]$RequireRust,
        [switch]$UseDefaultSharedToolRoot
    )

    $projectRoot = Get-ProjectAndroidToolchainRoot -RepoRoot $RepoRoot
    $sharedRoot = $null
    if ($env:SOLOX_SHARED_TOOLROOT) {
        $sharedRoot = [IO.Path]::GetFullPath($env:SOLOX_SHARED_TOOLROOT)
    } elseif ($UseDefaultSharedToolRoot) {
        $defaultShared = Get-DefaultSharedAndroidToolchainRoot
        if ($defaultShared) {
            $sharedRoot = [IO.Path]::GetFullPath($defaultShared)
        }
    }

    if ($sharedRoot) {
        if (
            $SkipValidation -or
            (Test-AndroidToolchainRoot `
                -ToolRoot $sharedRoot `
                -RequireCargoVendor:$RequireCargoVendor `
                -RequireRust:$RequireRust)
        ) {
            return $sharedRoot
        }

        Write-Warning (
            "Configured SOLOX_SHARED_TOOLROOT is incomplete: $sharedRoot. " +
            "Falling back to project toolchain."
        )
    }

    return $projectRoot
}
