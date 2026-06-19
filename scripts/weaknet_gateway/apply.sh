#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
IFACE=""
DELAY_MS=0
JITTER_MS=0
LOSS_PCT=0
RATE=""

usage() {
  echo "Usage: $0 --iface IFACE [--delay MS] [--jitter MS] [--loss PCT] [--rate RATE] [--dry-run]" >&2
}

validate_iface() {
  case "$IFACE" in
    "") echo "interface is required" >&2; exit 2 ;;
    "lo"|"loopback") echo "loopback interface is not allowed" >&2; exit 2 ;;
  esac
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '%s\n' "$*"
  else
    "$@"
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --iface) IFACE="${2:-}"; shift 2 ;;
    --delay) DELAY_MS="${2:-0}"; shift 2 ;;
    --jitter) JITTER_MS="${2:-0}"; shift 2 ;;
    --loss) LOSS_PCT="${2:-0}"; shift 2 ;;
    --rate) RATE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

validate_iface
IFB="ifb-$IFACE"
NETEM=(delay "${DELAY_MS}ms" "${JITTER_MS}ms" loss "${LOSS_PCT}%")
if [ -n "$RATE" ]; then
  NETEM+=(rate "$RATE")
fi

run_cmd sysctl -w net.ipv4.ip_forward=1
run_cmd sysctl -w net.ipv6.conf.all.forwarding=1
run_cmd modprobe ifb
run_cmd ip link add "$IFB" type ifb
run_cmd ip link set "$IFB" up
run_cmd tc qdisc replace dev "$IFACE" root handle 1: netem "${NETEM[@]}"
run_cmd tc qdisc replace dev "$IFACE" ingress
run_cmd tc filter replace dev "$IFACE" parent ffff: protocol all u32 match u32 0 0 action mirred egress redirect dev "$IFB"
run_cmd tc qdisc replace dev "$IFB" root handle 1: netem "${NETEM[@]}"
