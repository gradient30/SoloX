# QAS Network Agent Productization Acceptance Gates

Date: 2026-06-19

## Gate 0 Baseline Capture

This ledger captures the baseline repository state before continuing QAS Network Agent productization work.

Implementation continues in the current `main` workspace instead of a clean isolated worktree because the Android Agent baseline currently exists as untracked workspace content. A clean worktree would not contain that baseline and would not represent the actual implementation surface for follow-on tasks.

## Commands Run

### `git status --short --branch`

Status: succeeded

```text
## main...origin/master [ahead 18]
 M .gitignore
 M MANIFEST.in
 M docs/01-architecture/technical-architecture.md
 M docs/04-user-guides/api-documentation.md
 M docs/06-engineering/project-layout.md
 M docs/README.md
 M docs/acceptance/joint-review-2026-compatibility.md
 M pyproject.toml
 M solox/public/weak_network.py
 M solox/templates/index.html
 M solox/view/apis.py
 M tests/test_joint_acceptance.py
 M tests/test_weak_network.py
?? .cargo/
?? android-agent/
?? docs/04-user-guides/weak-network-testing.md
?? docs/06-engineering/android-agent-third-party.md
?? docs/06-engineering/weak-network-tooling.md
?? docs/plans/2026-06-14-android-vpn-weaknet-design.md
?? docs/plans/2026-06-14-android-vpn-weaknet.md
?? scripts/android_agent/
?? scripts/weaknet_gateway/
?? solox/public/android_agent/
?? solox/public/weaknet/
?? tests/integration/
?? tests/test_android_agent_control_plane.py
?? tests/test_android_agent_native_integration.py
?? tests/test_android_agent_project.py
?? tests/test_android_agent_protocol.py
?? tests/test_weaknet_agent.py
?? tests/test_weaknet_gateway_scripts.py
```

### `git worktree list`

Status: succeeded

```text
D:/workDir/githubwork/SoloX                                c6809f1 [main]
D:/workDir/githubwork/SoloX/.worktrees/android-vpn-weaknet 73601af [codex/android-vpn-weaknet]
```

### `git branch --all --verbose --no-abbrev`

Status: succeeded

```text
+ codex/android-vpn-weaknet 73601af01e806896dd1a36bc708da7ec583ae8b4 feat: integrate Android agent weak network APIs
* main                      c6809f1e0b46fa577cbca236e788053954fbec6c [ahead 18] docs: plan qas network agent productization
  remotes/origin/HEAD       -> origin/master
  remotes/origin/main       0c8970f285abc5d0ebe993eb0b3ac51995685d2b v2.9.3
  remotes/origin/master     5f2f7f260e628214139a06526c9988926a91e42e Merge branch 'solox-augment'
```

## Evidence Summary

- Current workspace is `main` at `c6809f1e0b46fa577cbca236e788053954fbec6c`, ahead of `origin/master` by 18 commits.
- Existing modified files and untracked files are present before Task 1 begins.
- Android Agent baseline content is present as untracked workspace content, including `android-agent/`, `scripts/android_agent/`, `solox/public/android_agent/`, and related tests.
- Existing worktree `D:/workDir/githubwork/SoloX/.worktrees/android-vpn-weaknet` is on `codex/android-vpn-weaknet` at `73601af01e806896dd1a36bc708da7ec583ae8b4`.

## Acceptance Criteria

- Gate 0 baseline evidence is captured.
- The exact baseline commands and their important outputs are recorded.
- The deviation from isolated worktree execution is documented.
- Only this evidence ledger is staged and committed for Task 1.

## Gate 1-2 Product Identity

Evidence:

- Commit `6d1a96c` changed public app identity to `QAS Network Agent`.
- Commit `1ff508f` completed QAS APK artifact packaging metadata.
- Commit `c59189e` rebuilt the APK from the QAS manifest and added APK badging verification.
- Commit `a5904e5` made Android Agent verification portable when local `aapt2` is unavailable.
- Commit `fc7ed87` updated public APK references in user-facing docs.
- Commit `fd287aa` updated remaining public fallback references.

Acceptance:

- Android package ID remains `io.solox.networkagent`.
- Control socket remains `solox.networkagent.control`.
- Public artifact is `qas-network-agent-0.1.0.apk`.
- `aapt2 dump badging` reports `application: label='QAS Network Agent'`.

## Gate 3 Launcher Icon

Evidence:

- Commit `e38ded7` added adaptive launcher icon resources.
- Commit `275f70c` added pre-26 launcher icon fallback resources for `minSdk = 21`.
- `aapt2 dump badging solox/public/android_agent/qas-network-agent-0.1.0.apk` reports a non-empty icon: `icon='res/BW.xml'`.

Acceptance:

- Manifest declares `android:icon="@mipmap/ic_launcher"`.
- Manifest declares `android:roundIcon="@mipmap/ic_launcher_round"`.
- `mipmap-anydpi-v26` adaptive icons and `mipmap-anydpi` fallback icons exist.
- Foreground vector documents the requested person pulling a network cable concept.

## Gate 4 Agent Logs

Evidence:

- Commit `42e478d` added traceable local logs and lifecycle logging.
- Commit `01fb1da` bounded retained log payload size and fixed JSON control-character escaping.
- `python -m pytest tests/test_android_agent_control_plane.py -q` passed with 5 tests during Gate 4 verification.

Acceptance:

- Local logs are bounded by entry count and source/message length.
- Log filtering supports exact `ERROR`, `WARN`, `INFO`, and `DEBUG` levels.
- JSON output escapes quotes, backslashes, and control characters.
- Service, dispatcher, socket, and Activity have log integration points.

## Gate 5 Professional UI And Background Operation

Evidence:

- Commit `24d3e29` replaced the demo Activity with an operational console UI.
- `python -m pytest tests/test_android_agent_control_plane.py -q` passed with 6 tests.
- `python -m pytest tests/test_android_agent_project.py tests/test_android_agent_protocol.py tests/test_android_agent_control_plane.py tests/test_android_agent_native_integration.py -q` passed with 23 tests.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 --offline assembleRelease` passed.

Acceptance:

- Main screen exposes status, VPN authorization, target package, weak-network profile, background service, log filters, and recent logs.
- Buttons exist for VPN authorization/start service, stop service, and refresh.
- Foreground service behavior remains based on `startForeground`.
- Service restart behavior remains `START_STICKY`.

## Gate 6 Weaknet Baseline Integration

Evidence:

- Commit `5d56db0` integrated the Android Agent weak-network baseline into `main`.
- `python -m pytest tests/test_weak_network.py tests/test_joint_acceptance.py tests/test_weaknet_agent.py tests/test_weaknet_gateway_scripts.py -q` passed with 72 tests.
- `python -m pytest tests/test_android_agent_project.py tests/test_android_agent_protocol.py tests/test_android_agent_control_plane.py tests/test_android_agent_native_integration.py -q` passed with 23 tests.

Acceptance:

- Weak-network engine, Android Agent controller, gateway scripts, API/UI changes, and tests are tracked on `main`.
- Runtime/toolchain and Android build outputs are ignored.
- Remaining untracked tun2proxy upstream auxiliary files are not required for the tracked build or test contracts.

## Gate 7 Main-Only Branch Integration

Evidence:

- `git merge -s ours codex/android-vpn-weaknet -m "merge: absorb android weaknet branch into main"` created merge commit `56b205a` while preserving current `main` content.
- `git worktree remove --force D:\workDir\githubwork\SoloX\.worktrees\android-vpn-weaknet` detached the old linked worktree; Windows path cleanup required a long-path `Remove-Item`.
- `git branch -d codex/android-vpn-weaknet` deleted the local development branch.
- `git worktree list` now reports only `D:/workDir/githubwork/SoloX [main]`.
- `git branch --all --verbose --no-abbrev` reports only local `main` plus remotes.

Final verification:

```text
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_protocol.py tests/test_android_agent_control_plane.py tests/test_android_agent_native_integration.py tests/test_weak_network.py tests/test_joint_acceptance.py tests/test_weaknet_agent.py tests/test_weaknet_gateway_scripts.py -q
95 passed

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 --offline assembleRelease
BUILD SUCCESSFUL

runtime/android-toolchain/android-sdk/build-tools/36.0.0/aapt2.exe dump badging solox/public/android_agent/qas-network-agent-0.1.0.apk
package: name='io.solox.networkagent'
application: label='QAS Network Agent' icon='res/BW.xml'
```

Acceptance:

- `main` contains the accepted work.
- Local `codex/android-vpn-weaknet` branch is removed.
- No linked Android weaknet worktree remains.
- The tracked APK artifact is named `qas-network-agent-0.1.0.apk`.
