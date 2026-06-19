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

run_ignore() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '%s\n' "$*"
  else
    "$@" || true
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

# dry-run output contract:
# tc qdisc del dev "$IFACE" root || true
# tc qdisc del dev "$IFACE" ingress || true
# tc qdisc del dev "$IFB" root || true
# ip link del "$IFB" || true
run_ignore tc qdisc del dev "$IFACE" root
run_ignore tc qdisc del dev "$IFACE" ingress
run_ignore tc qdisc del dev "$IFB" root
run_ignore ip link del "$IFB"
