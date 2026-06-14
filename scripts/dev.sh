#!/usr/bin/env bash
# =============================================================================
# SoloX Dev Script — start / stop / restart / status / log
# Compatible with: Git Bash (MINGW/MSYS), WSL, Linux, macOS, PowerShell (via bash)
# =============================================================================

set -euo pipefail

# ---- defaults ---------------------------------------------------------------
HOST="${SOLOX_HOST:-0.0.0.0}"
PORT="${SOLOX_PORT:-50003}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/runtime"
PID_FILE="$RUNTIME_DIR/pids/solox.pid"
LOG_FILE="$RUNTIME_DIR/logs/solox-dev.log"
LEGACY_PID_FILE="$PROJECT_DIR/.solox.pid"
LEGACY_LOG_FILE="$PROJECT_DIR/.solox.log"
PYTHON="${SOLOX_PYTHON:-python}"

# ---- python / environment detection -----------------------------------------
_is_wsl() {
    [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null
}

_resolve_python() {
    if command -v "$PYTHON" &>/dev/null 2>&1; then
        return 0
    fi
    local candidate
    for candidate in python3 py; do
        if command -v "$candidate" &>/dev/null 2>&1; then
            PYTHON="$candidate"
            return 0
        fi
    done
    for candidate in \
        /mnt/c/Python312/python.exe \
        /mnt/c/Python311/python.exe \
        /mnt/c/Python310/python.exe \
        /c/Python312/python.exe \
        /c/Python311/python.exe; do
        if [[ -f "$candidate" ]]; then
            PYTHON="$candidate"
            return 0
        fi
    done
    return 1
}

if ! _resolve_python; then
    err "Python not found (tried: python, python3, py, Windows Python under /mnt/c)."
    if _is_wsl; then
        err "PowerShell 里的 bash 会进入 WSL，WSL 内通常没有 python。"
        err "请改用:  .\\scripts\\dev.ps1 start"
        err "或:      SOLOX_PYTHON=/mnt/c/Python312/python.exe SOLOX_PORT=50005 bash scripts/dev.sh start"
    else
        err "请设置: SOLOX_PYTHON=/c/Python312/python.exe"
    fi
    exit 1
fi

if _is_wsl && [[ "$PROJECT_DIR" == /mnt/* ]]; then
    warn "当前为 WSL 环境 ($PROJECT_DIR)。Windows 上推荐 .\\scripts\\dev.ps1 start"
fi

# ---- color helpers (degrade gracefully on dumb terminals) -------------------
if [[ -t 1 ]] && command -v tput &>/dev/null; then
    C_GREEN=$(tput setaf 2)
    C_RED=$(tput setaf 1)
    C_YELLOW=$(tput setaf 3)
    C_CYAN=$(tput setaf 6)
    C_RESET=$(tput sgr0)
else
    C_GREEN="" C_RED="" C_YELLOW="" C_CYAN="" C_RESET=""
fi

info()  { echo "${C_GREEN}[INFO]${C_RESET}  $*"; }
warn()  { echo "${C_YELLOW}[WARN]${C_RESET}  $*"; }
err()   { echo "${C_RED}[ERROR]${C_RESET} $*" >&2; }

# ---- pid helpers ------------------------------------------------------------
_read_pid() {
    for f in "$PID_FILE" "$LEGACY_PID_FILE"; do
        if [[ -f "$f" ]]; then
            cat "$f" 2>/dev/null
            return 0
        fi
    done
    echo ""
}

_is_running() {
    local pid="$1"
    [[ -z "$pid" ]] && return 1
    # Works on Git Bash (MSYS/MINGW), WSL, Linux, macOS
    if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
        # Git Bash on Windows: use tasklist
        tasklist.exe //FI "PID eq $pid" 2>/dev/null | grep -q "$pid" 2>/dev/null
    else
        kill -0 "$pid" 2>/dev/null
    fi
}

_find_solox_pids() {
    # Find all processes listening on $PORT. Returns empty string if none.
    # Note: use a subshell with pipefail disabled to prevent grep exit(1) on no-match.
    (
        set +o pipefail
        if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
            netstat.exe -ano 2>/dev/null | grep ":${PORT}" | grep "LISTENING" | awk '{print $NF}' | sort -u
        else
            if command -v ss &>/dev/null; then
                ss -tlnp "sport = :${PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u
            elif command -v lsof &>/dev/null; then
                lsof -ti ":${PORT}" -sTCP:LISTEN 2>/dev/null | sort -u
            else
                for pf in "$PID_FILE" "$LEGACY_PID_FILE"; do
                    [[ -f "$pf" ]] && cat "$pf" 2>/dev/null && break
                done
            fi
        fi
    ) 2>/dev/null || true
}

# ---- kill helper (cross-platform) -------------------------------------------
_kill_pid() {
    local pid="$1"
    [[ -z "$pid" ]] && return 0
    if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
        taskkill.exe //F //T //PID "$pid" &>/dev/null || true
    else
        kill "$pid" 2>/dev/null || true
        local i=0
        while (( i < 10 )) && kill -0 "$pid" 2>/dev/null; do
            sleep 0.5
            (( i++ ))
        done
        kill -9 "$pid" 2>/dev/null || true
    fi
}

_kill_port_occupants() {
    # Kill every process listening on $PORT
    local pids
    pids=$(_find_solox_pids)
    [[ -z "$pids" ]] && return 0
    for p in $pids; do
        warn "Killing PID $p occupying port $PORT ..."
        _kill_pid "$p"
    done
    sleep 1
    # Verify
    pids=$(_find_solox_pids)
    if [[ -n "$pids" ]]; then
        err "Failed to free port $PORT (PID $pids still listening). Kill it manually or use a different port:"
        err "  SOLOX_PORT=50005 $(basename "$0") start"
        return 1
    fi
    info "Port $PORT freed."
}

# ---- actions ----------------------------------------------------------------

do_start() {
    # If we own a previous background process, kill it
    local old_pid
    old_pid=$(_read_pid)
    if [[ -n "$old_pid" ]] && _is_running "$old_pid"; then
        warn "Stopping previous SoloX (PID $old_pid) ..."
        _kill_pid "$old_pid"
        rm -f "$PID_FILE"
    fi

    # If port is still occupied (by us or anyone), kill the occupant
    _kill_port_occupants

    mkdir -p "$RUNTIME_DIR/logs" "$RUNTIME_DIR/pids"

    info "Starting SoloX on ${HOST}:${PORT} ..."
    info "Python: $($PYTHON --version 2>&1)"
    info "Project: $PROJECT_DIR"
    info "Log: $LOG_FILE"

    cd "$PROJECT_DIR"

    # Start in background, redirect stdout+stderr to log file
    nohup $PYTHON -m solox --host="$HOST" --port="$PORT" \
        >> "$LOG_FILE" 2>&1 &
    local shell_pid=$!

    # Wait for the port to come up (up to 15 seconds)
    info "Waiting for port $PORT ..."
    local waited=0
    while [[ $waited -lt 15 ]]; do
        sleep 1
        waited=$((waited + 1))
        local real_pid
        real_pid="$(_find_solox_pids)" || true
        if [[ -n "$real_pid" ]]; then
            # Save the actual process PID (not the nohup wrapper)
            echo "$real_pid" > "$PID_FILE"
            info "SoloX started successfully (PID $real_pid)"
            info "Web UI: http://127.0.0.1:${PORT}/?platform=Android&lan=cn"
            return 0
        fi
    done

    err "SoloX failed to start within 10s. Check log: $LOG_FILE"
    tail -20 "$LOG_FILE" 2>/dev/null
    rm -f "$PID_FILE"
    return 1
}

do_stop() {
    local stopped=false

    # 1) Kill process from pid file
    local pid
    pid=$(_read_pid)
    if [[ -n "$pid" ]] && _is_running "$pid"; then
        info "Stopping SoloX (PID $pid) ..."
        _kill_pid "$pid"
        stopped=true
    fi

    # 2) Kill any process still on the port
    local port_pids
    port_pids=$(_find_solox_pids)
    if [[ -n "$port_pids" ]]; then
        for p in $port_pids; do
            info "Killing PID $p on port $PORT ..."
            _kill_pid "$p"
        done
        stopped=true
    fi

    rm -f "$PID_FILE"

    if $stopped; then
        info "SoloX stopped."
    else
        warn "SoloX is not running."
    fi
}

do_restart() {
    do_stop
    sleep 1
    do_start
}

do_status() {
    echo "${C_CYAN}=== SoloX Status ===${C_RESET}"
    echo ""

    # Process
    local pid
    pid=$(_read_pid)
    if [[ -n "$pid" ]] && _is_running "$pid"; then
        info "Process:  running (PID $pid)"
    elif [[ -n "$pid" ]]; then
        warn "Process:  dead (stale PID file: $pid)"
    else
        warn "Process:  not running"
    fi

    # Port
    local port_pids
    port_pids=$(_find_solox_pids)
    if [[ -n "$port_pids" ]]; then
        info "Port $PORT: LISTEN (PID: $port_pids)"
    else
        warn "Port $PORT: not in use"
    fi

    # HTTP health check
    local http_ok=false
    if command -v curl &>/dev/null; then
        if curl -s -o /dev/null -w '' --max-time 2 "http://127.0.0.1:${PORT}/" 2>/dev/null; then
            http_ok=true
        fi
    elif command -v wget &>/dev/null; then
        if wget -q --spider --timeout=2 "http://127.0.0.1:${PORT}/" 2>/dev/null; then
            http_ok=true
        fi
    fi
    if $http_ok; then
        info "HTTP:     http://127.0.0.1:${PORT}/ is responding"
    else
        warn "HTTP:     http://127.0.0.1:${PORT}/ is NOT responding"
    fi

    # ADB devices
    echo ""
    if command -v adb &>/dev/null || command -v adb.exe &>/dev/null; then
        info "Connected Android devices:"
        local dev_list
        dev_list="$(adb devices 2>/dev/null | tail -n +2 | grep -v '^$' || true)"
        if [[ -n "$dev_list" ]]; then
            echo "$dev_list" | sed 's/^/       /'
        else
            warn "       (none)"
        fi
    else
        warn "ADB: not found in PATH"
    fi

    # Python / SoloX version
    echo ""
    info "Python:   $($PYTHON --version 2>&1)"
    info "SoloX:    $($PYTHON -c 'from solox import __version__; print(__version__)' 2>/dev/null || echo 'not installed')"
    info "Host:     $HOST"
    info "Port:     $PORT"
    info "PID file: $PID_FILE"
    info "Log file: $LOG_FILE"
}

do_log() {
    if [[ ! -f "$LOG_FILE" ]]; then
        warn "No log file found at $LOG_FILE"
        return 1
    fi
    local lines="${1:-50}"
    info "Last $lines lines of $LOG_FILE:"
    echo "---"
    tail -n "$lines" "$LOG_FILE"
}

do_foreground() {
    # Run in foreground (interactive mode, useful for debugging)
    local old_pid
    old_pid=$(_read_pid)
    if [[ -n "$old_pid" ]] && _is_running "$old_pid"; then
        warn "Stopping previous background SoloX (PID $old_pid) ..."
        _kill_pid "$old_pid"
        rm -f "$PID_FILE"
    fi

    # Auto-kill port occupants
    _kill_port_occupants

    info "Starting SoloX in foreground on ${HOST}:${PORT} ..."
    info "Press Ctrl+C to stop."
    cd "$PROJECT_DIR"
    $PYTHON -m solox --host="$HOST" --port="$PORT"
}

# ---- usage ------------------------------------------------------------------

usage() {
    cat <<EOF
${C_CYAN}SoloX Dev Script${C_RESET} — manage SoloX development server

${C_GREEN}Usage:${C_RESET}
    $(basename "$0") <command> [options]

${C_GREEN}Commands:${C_RESET}
    start       Start SoloX in background (daemonized)
    stop        Stop SoloX
    restart     Stop then start
    status      Show process, port, HTTP health, devices, versions
    log [N]     Show last N lines of log (default: 50)
    fg          Start SoloX in foreground (interactive, Ctrl+C to stop)

${C_GREEN}Environment variables:${C_RESET}
    SOLOX_HOST    Bind address   (default: 0.0.0.0)
    SOLOX_PORT    Listen port    (default: 50003)
    SOLOX_PYTHON  Python binary  (default: python)

${C_GREEN}Examples:${C_RESET}
    $(basename "$0") start                     # start with defaults
    $(basename "$0") status                    # check everything
    SOLOX_PORT=8080 $(basename "$0") start     # start on port 8080
    $(basename "$0") log 100                   # show last 100 log lines
    $(basename "$0") fg                        # interactive/debug mode
    $(basename "$0") stop                      # stop server

${C_GREEN}PowerShell usage:${C_RESET}
    bash scripts/dev.sh start
    bash scripts/dev.sh status
    bash scripts/dev.sh stop
EOF
}

# ---- main dispatcher --------------------------------------------------------

case "${1:-}" in
    start)      do_start ;;
    stop)       do_stop ;;
    restart)    do_restart ;;
    status)     do_status ;;
    log)        do_log "${2:-50}" ;;
    fg)         do_foreground ;;
    -h|--help)  usage ;;
    "")         usage ;;
    *)
        err "Unknown command: $1"
        echo ""
        usage
        exit 1
        ;;
esac
