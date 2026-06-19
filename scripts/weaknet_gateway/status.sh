#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
IFACE=""

usage() {
  echo "Usage: $0 --iface IFACE [--dry-run]" >&2
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
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

validate_iface
IFB="ifb-$IFACE"

run_cmd sysctl net.ipv4.ip_forward
run_cmd sysctl net.ipv6.conf.all.forwarding
run_cmd tc qdisc show dev "$IFACE"
run_cmd tc filter show dev "$IFACE" parent ffff:
run_cmd tc qdisc show dev "$IFB"
