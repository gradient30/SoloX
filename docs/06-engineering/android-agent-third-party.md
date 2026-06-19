# Android Agent Third-Party Components

## tun2proxy

- Source: https://github.com/tun2proxy/tun2proxy
- License: MIT
- Pinned revision: eed123fbbec06295bf83f9be36d5a0f64ed9a8cb
- Local archive: `runtime/android-toolchain/downloads/tun2proxy/tun2proxy-eed123fbbec06295bf83f9be36d5a0f64ed9a8cb.zip`
- Vendored source: `android-agent/native/third_party/tun2proxy`
- Android adapter contract: the vendored runtime exposes `pub async fn run<D>`
  where the VPN device type implements `AsyncRead/AsyncWrite`, `Unpin`, `Send`,
  and a static lifetime. The Agent passes the detached VPN fd through this typed
  path instead of shelling out to a tun2proxy process.

The Android native bridge is wired with bounded arguments (`--tun-fd`,
`--proxy=socks5://127.0.0.1:1080`, `--dns=over-tcp`, `--ipv6-enabled`,
`--max-sessions=256`, `--close-fd-on-drop=true`) and passes profile values
through JNI without shell command construction.

At runtime SoloX overrides the placeholder proxy address with a loopback
SOCKS5 listener bound by native code. tun2proxy owns the Android VPN fd and
parses TCP/UDP traffic from the target app. The in-process SOCKS5 shaper then
applies deterministic uplink/downlink delay, jitter, loss, and bandwidth
limits before opening real network sockets outside the VPN allow-list.

The Agent was validated on a real Android device by applying weak network to
`com.lyjz.chqsy.vivo`; Android `dumpsys connectivity` showed the VPN network
bound only to that app UID (`UIDs: [10241-10241]`), and `clear` removed the
`tun0` network without residue.
