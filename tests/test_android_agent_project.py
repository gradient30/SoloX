# -*- coding: utf-8 -*-
"""Build and manifest contracts for the bundled Android weak-network Agent."""

from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / 'android-agent'


def read(relative_path: str) -> str:
    return (AGENT / relative_path).read_text(encoding='utf-8')


def test_android_project_pins_supported_toolchain():
    root_build = read('build.gradle.kts')
    app_build = read('app/build.gradle.kts')
    wrapper = read('gradle/wrapper/gradle-wrapper.properties')

    assert 'com.android.application") version "8.13.0"' in root_build
    assert 'org.jetbrains.kotlin.android") version "2.1.20"' in root_build
    assert 'compileSdk = 36' in app_build
    assert 'buildToolsVersion = "36.0.0"' in app_build
    assert 'targetSdk = 36' in app_build
    assert 'minSdk = 21' in app_build
    assert 'ndkVersion = "29.0.14206865"' in app_build
    assert 'gradle-8.13-bin.zip' in wrapper
    assert (
        'distributionSha256Sum='
        '20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78'
        in wrapper
    )


def test_android_empty_shell_does_not_pull_unneeded_runtime_dependencies():
    app_build = read('app/build.gradle.kts')

    assert 'id("org.jetbrains.kotlin.android")' not in app_build
    assert 'kotlinOptions' not in app_build
    assert 'junit:junit' not in app_build


def test_android_project_has_expected_identity_and_abis():
    app_build = read('app/build.gradle.kts')

    assert 'namespace = "io.solox.networkagent"' in app_build
    assert 'applicationId = "io.solox.networkagent"' in app_build
    assert '"arm64-v8a"' in app_build
    assert '"x86_64"' in app_build
    assert 'signingConfig = signingConfigs.getByName("debug")' in app_build


def test_android_agent_uses_qas_product_identity():
    manifest = read('app/src/main/AndroidManifest.xml')
    notification = read(
        'app/src/main/java/io/solox/networkagent/notification/AgentNotification.java',
    )
    activity = read('app/src/main/java/io/solox/networkagent/MainActivity.java')

    assert 'android:label="QAS Network Agent"' in manifest
    assert 'QAS Network Agent' in notification
    assert 'QAS Network Agent' in activity


def test_manifest_declares_only_required_vpn_and_foreground_permissions():
    manifest = read('app/src/main/AndroidManifest.xml')

    assert 'android.permission.INTERNET' in manifest
    assert 'android.permission.FOREGROUND_SERVICE' in manifest
    assert 'android.permission.FOREGROUND_SERVICE_SPECIAL_USE' in manifest
    assert 'android.permission.QUERY_ALL_PACKAGES' in manifest
    assert 'android.permission.BIND_VPN_SERVICE' in manifest
    assert 'android.net.VpnService' in manifest
    assert 'android:launchMode="singleTop"' in manifest
    assert 'android:exported="false"' in manifest
    for unrelated in (
        'READ_CONTACTS',
        'READ_SMS',
        'ACCESS_FINE_LOCATION',
        'READ_EXTERNAL_STORAGE',
        'WRITE_EXTERNAL_STORAGE',
    ):
        assert unrelated not in manifest


def test_windows_build_scripts_use_isolated_runtime_toolchain():
    bootstrap = (ROOT / 'scripts/android_agent/bootstrap.ps1').read_text(
        encoding='utf-8',
    )
    build = (ROOT / 'scripts/android_agent/build.ps1').read_text(
        encoding='utf-8',
    )

    assert 'runtime/android-toolchain' in bootstrap.replace('\\', '/')
    assert 'Get-FileHash' in bootstrap
    assert 'SHA256' in bootstrap
    assert 'SHA1' in bootstrap
    assert 'microsoft-jdk-17.0.19-windows-x64.zip' in bootstrap
    assert (
        '394d1d8253d58b462300f15f9c81369478cf8813f82dca914c3b5dfdef080f9f'
        in bootstrap
    )
    assert "jdk-stage\\jdk-17.0.19+10" in bootstrap
    assert "cmdline-tools-stage\\cmdline-tools" in bootstrap
    assert "Move-Item -LiteralPath (Join-Path $toolsStage" not in bootstrap
    assert 'github.com/adoptium' not in bootstrap
    assert 'JAVA_HOME' in build
    assert 'ANDROID_SDK_ROOT' in build
    assert "gradle-8.13\\bin\\gradle.bat" in build
    assert 'gradlew.bat' not in build
    assert "$NativeCache = Join-Path $env:GRADLE_USER_HOME 'native'" in build
    assert 'Remove-Item -LiteralPath $NativeCache -Recurse -Force' in build
    assert "build-tools\\36.0.0\\aapt2.exe" in build
    assert 'android.aapt2FromMavenOverride' in build
    assert 'local.properties' in build
    assert ".Replace('\\', '/')" in build
    assert 'SetEnvironmentVariable' not in bootstrap
    assert 'SetEnvironmentVariable' not in build


def test_bootstrap_path_guard_allows_tool_root_itself():
    bootstrap = (ROOT / 'scripts/android_agent/bootstrap.ps1').read_text(
        encoding='utf-8',
    )

    assert '$rootTrimmed = [IO.Path]::GetFullPath($ToolRoot).TrimEnd' in bootstrap
    assert '$candidateTrimmed = [IO.Path]::GetFullPath($Path).TrimEnd' in bootstrap
    assert '$candidateTrimmed -ne $rootTrimmed' in bootstrap


def test_bootstrap_uses_verified_offline_android_sdk_archives():
    bootstrap = (ROOT / 'scripts/android_agent/bootstrap.ps1').read_text(
        encoding='utf-8',
    )

    expected = {
        'platform-tools_r37.0.0-win.zip': (
            'f29bfb58d0d6f9a57d7dbcba6cc259f9ca6f58f1',
            '4fe305812db074cea32903a489d061eb4454cbc90a49e8fea677f4b7af764918',
        ),
        'platform-36_r02.zip': (
            '2c1a80dd4d9f7d0e6dd336ec603d9b5c55a6f576',
            '37607369a28c5b640b3a7998868d45898ebcb777565a0e85f9acf36f29631d2e',
        ),
        'build-tools_r36_windows.zip': (
            'f16ccffd34de8790dede813a6c7d8e2c11a27b50',
            'aa1095cb14d83e483818a748a2c06faaeb8e601561b06a356a119a1b2ca280d3',
        ),
        'android-ndk-r29-windows.zip': (
            'ab3bb30fbb9e6903666d60c55d11e78b04e07472',
            '4f83a1a87ea0d33ae2b43812ce27b768be949bc78acf90b955134d19e3068f1c',
        ),
    }
    for filename, hashes in expected.items():
        assert filename in bootstrap
        for digest in hashes:
            assert digest in bootstrap

    assert 'Expand-ZipPrefix' in bootstrap
    assert "Join-Path $AndroidSdkRoot 'platform-tools'" in bootstrap
    assert "build-tools\\36.0.0" in bootstrap
    assert "ndk\\29.0.14206865" in bootstrap
    assert "'platform-tools' `" not in bootstrap
    assert "'ndk;29.0.14206865'" not in bootstrap


def test_gradle_wrapper_launchers_are_tracked():
    assert (AGENT / 'gradlew').is_file()
    assert (AGENT / 'gradlew.bat').is_file()
    assert (AGENT / 'gradle/wrapper/gradle-wrapper.jar').is_file()


def test_android_agent_package_metadata_contract():
    package_script = ROOT / 'scripts' / 'android_agent' / 'package.ps1'
    metadata_path = ROOT / 'solox' / 'public' / 'android_agent' / 'checksums.json'
    manifest = (ROOT / 'MANIFEST.in').read_text(encoding='utf-8')
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')

    assert package_script.is_file()
    script = package_script.read_text(encoding='utf-8')
    assert 'qas-network-agent-' in script
    assert 'solox-network-agent-' not in script
    assert 'checksums.json' in script
    assert 'SHA256' in script
    assert 'app-release.apk' in script

    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    assert metadata['package_id'] == 'io.solox.networkagent'
    assert metadata['min_protocol_version'] == 1
    assert metadata['version']
    assert metadata['version_code'] >= 1
    assert metadata['apk'].startswith('qas-network-agent-')
    assert metadata['apk'].endswith('.apk')
    assert len(metadata['sha256']) == 64
    assert 'solox/public/android_agent *' in manifest
    assert 'public/android_agent/**/*' in pyproject


def test_public_android_agent_apk_matches_qas_identity():
    aapt2 = (
        ROOT
        / 'runtime'
        / 'android-toolchain'
        / 'android-sdk'
        / 'build-tools'
        / '36.0.0'
        / 'aapt2.exe'
    )
    apk = ROOT / 'solox' / 'public' / 'android_agent' / 'qas-network-agent-0.1.0.apk'

    result = subprocess.run(
        [str(aapt2), 'dump', 'badging', str(apk)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "package: name='io.solox.networkagent'" in result.stdout
    assert "application: label='QAS Network Agent'" in result.stdout






