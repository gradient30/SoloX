# SoloX Linux gateway weak-network calibration

These scripts configure a Linux gateway as the calibration baseline for Android
Agent weak-network validation. They are intended for a lab gateway or OpenWrt-
like host, not for the Windows machine running SoloX.

The apply script shapes both directions:

- egress: root `tc netem` on the selected interface.
- ingress: redirect ingress traffic to an IFB device, then apply separate
  `tc netem` rules on that IFB device.
- forwarding: requires IPv4 and IPv6 forwarding to be enabled.

Use `--dry-run` before touching a gateway:

```bash
sudo ./apply.sh --dry-run --iface eth0 --delay 100 --jitter 20 --loss 1 --rate 5mbit
sudo ./apply.sh --iface eth0 --delay 100 --jitter 20 --loss 1 --rate 5mbit
sudo ./status.sh --iface eth0
sudo ./clear.sh --iface eth0
```

The scripts refuse empty, `lo`, or `loopback` interfaces and do not use `eval`.
`clear.sh` is idempotent and may be run during cleanup even if apply failed.
