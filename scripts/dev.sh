#!/usr/bin/env bash
# =============================================================================
# SoloX 开发服务脚本 — start / stop / restart / status / log / fg
# 兼容: Git Bash (MINGW/MSYS)、WSL、Linux、macOS；Windows 推荐 dev.ps1
# =============================================================================

set -euo pipefail

HOST="${SOLOX_HOST:-0.0.0.0}"
PORT="${SOLOX_PORT:-50003}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/runtime"
PID_FILE="$RUNTIME_DIR/pids/solox.pid"
LOG_FILE="$RUNTIME_DIR/logs/solox-dev.log"
LEGACY_PID_FILE="$PROJECT_DIR/.solox.pid"
PYTHON="${SOLOX_PYTHON:-python}"

if [[ -t 1 ]] && command -v tput &>/dev/null; then
    C_GREEN=$(tput setaf 2)
    C_RED=$(tput setaf 1)
    C_YELLOW=$(tput setaf 3)
    C_CYAN=$(tput setaf 6)
    C_RESET=$(tput sgr0)
else
    C_GREEN="" C_RED="" C_YELLOW="" C_CYAN="" C_RESET=""
fi

info()  { echo "${C_GREEN}[信息]${C_RESET}  $*"; }
warn()  { echo "${C_YELLOW}[警告]${C_RESET}  $*"; }
err()   { echo "${C_RED}[错误]${C_RESET} $*" >&2; }

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
    err "未找到 Python（已尝试 python / python3 / py 及常见 Windows 路径）。"
    if _is_wsl; then
        err "PowerShell 中直接运行 bash 可能进入 WSL，WSL 内通常没有 Windows 版 Python。"
        err "请改用:  .\\scripts\\dev.ps1 start"
        err "或设置:  SOLOX_PYTHON=/mnt/c/Python312/python.exe bash scripts/dev.sh start"
    else
        err "请设置环境变量 SOLOX_PYTHON 指向 Python 可执行文件。"
    fi
    exit 1
fi

if _is_wsl && [[ "$PROJECT_DIR" == /mnt/* ]]; then
    warn "当前为 WSL 路径 ($PROJECT_DIR)。在 Windows 上推荐使用 .\\scripts\\dev.ps1"
fi

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
    if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
        tasklist.exe //FI "PID eq $pid" 2>/dev/null | grep -q "$pid" 2>/dev/null
    else
        kill -0 "$pid" 2>/dev/null
    fi
}

_find_solox_pids() {
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
            (( i++ )) || true
        done
        kill -9 "$pid" 2>/dev/null || true
    fi
}

_kill_port_occupants() {
    local pids
    pids=$(_find_solox_pids)
    [[ -z "$pids" ]] && return 0
    for p in $pids; do
        warn "正在终止占用端口 ${PORT} 的进程 PID ${p} …"
        _kill_pid "$p"
    done
    sleep 1
    pids=$(_find_solox_pids)
    if [[ -n "$pids" ]]; then
        err "无法释放端口 ${PORT}（仍有进程 ${pids} 在监听）。请手动结束或换端口:"
        err "  SOLOX_PORT=50005 $(basename "$0") start"
        return 1
    fi
    info "端口 ${PORT} 已释放。"
}

do_start() {
    local old_pid
    old_pid=$(_read_pid)
    if [[ -n "$old_pid" ]] && _is_running "$old_pid"; then
        warn "正在停止上一次 SoloX 进程 (PID ${old_pid}) …"
        _kill_pid "$old_pid"
        rm -f "$PID_FILE"
    fi

    _kill_port_occupants

    mkdir -p "$RUNTIME_DIR/logs" "$RUNTIME_DIR/pids"

    info "正在启动 SoloX：${HOST}:${PORT}"
    info "Python: $($PYTHON --version 2>&1)"
    info "项目目录: $PROJECT_DIR"
    info "日志文件: $LOG_FILE"

    cd "$PROJECT_DIR"
    nohup $PYTHON -m solox --host="$HOST" --port="$PORT" \
        >> "$LOG_FILE" 2>&1 &
    local _shell_pid=$!

    info "等待端口 ${PORT} 就绪 …"
    local waited=0
    while [[ $waited -lt 15 ]]; do
        sleep 1
        waited=$((waited + 1))
        local real_pid
        real_pid="$(_find_solox_pids)" || true
        if [[ -n "$real_pid" ]]; then
            echo "$real_pid" > "$PID_FILE"
            info "SoloX 启动成功 (PID ${real_pid})"
            info "Web 界面: http://127.0.0.1:${PORT}/?platform=Android&lan=cn"
            info "健康检查: http://127.0.0.1:${PORT}/health"
            return 0
        fi
    done

    err "SoloX 在 15 秒内未能启动，请查看日志: $LOG_FILE"
    tail -20 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    return 1
}

do_stop() {
    local stopped=false
    local pid
    pid=$(_read_pid)
    if [[ -n "$pid" ]] && _is_running "$pid"; then
        info "正在停止 SoloX (PID ${pid}) …"
        _kill_pid "$pid"
        stopped=true
    fi

    local port_pids
    port_pids=$(_find_solox_pids)
    if [[ -n "$port_pids" ]]; then
        for p in $port_pids; do
            info "正在终止端口 ${PORT} 上的进程 PID ${p} …"
            _kill_pid "$p"
        done
        stopped=true
    fi

    rm -f "$PID_FILE"

    if $stopped; then
        info "SoloX 已停止。"
    else
        warn "SoloX 当前未在运行。"
    fi
}

do_restart() {
    do_stop
    sleep 1
    do_start
}

_http_health_ok() {
    local url="http://127.0.0.1:${PORT}/health"
    if command -v curl &>/dev/null; then
        curl -sf --max-time 2 "$url" | grep -q '"status"' 2>/dev/null
        return $?
    fi
    if command -v wget &>/dev/null; then
        wget -q --timeout=2 -O - "$url" 2>/dev/null | grep -q '"status"'
        return $?
    fi
    return 1
}

do_status() {
    echo "${C_CYAN}=== SoloX 运行状态 ===${C_RESET}"
    echo ""

    local pid
    pid=$(_read_pid)
    if [[ -n "$pid" ]] && _is_running "$pid"; then
        info "进程:     运行中 (PID ${pid})"
    elif [[ -n "$pid" ]]; then
        warn "进程:     已退出（PID 文件过期: ${pid}）"
    else
        warn "进程:     未运行"
    fi

    local port_pids
    port_pids=$(_find_solox_pids)
    if [[ -n "$port_pids" ]]; then
        info "端口 ${PORT}: 监听中 (PID: ${port_pids})"
    else
        warn "端口 ${PORT}: 未占用"
    fi

    if _http_health_ok; then
        info "HTTP:     /health 正常 — http://127.0.0.1:${PORT}/health"
    else
        warn "HTTP:     /health 无响应 — http://127.0.0.1:${PORT}/health"
    fi

    echo ""
    if command -v adb &>/dev/null || command -v adb.exe &>/dev/null; then
        info "已连接 Android 设备:"
        local dev_list
        dev_list="$(adb devices 2>/dev/null | tail -n +2 | grep -v '^$' || true)"
        if [[ -n "$dev_list" ]]; then
            echo "$dev_list" | sed 's/^/       /'
        else
            warn "       （无）"
        fi
    else
        warn "ADB: 未在 PATH 中找到"
    fi

    echo ""
    info "Python:   $($PYTHON --version 2>&1)"
    info "SoloX:    $($PYTHON -c 'from solox import __version__; print(__version__)' 2>/dev/null || echo '未安装')"
    info "监听地址: ${HOST}"
    info "端口:     ${PORT}"
    info "PID 文件: ${PID_FILE}"
    info "日志文件: ${LOG_FILE}"
}

do_log() {
    if [[ ! -f "$LOG_FILE" ]]; then
        warn "未找到日志文件: $LOG_FILE"
        return 1
    fi
    local lines="${1:-50}"
    info "日志末尾 ${lines} 行 ($LOG_FILE):"
    echo "---"
    tail -n "$lines" "$LOG_FILE"
}

do_foreground() {
    local old_pid
    old_pid=$(_read_pid)
    if [[ -n "$old_pid" ]] && _is_running "$old_pid"; then
        warn "正在停止后台 SoloX (PID ${old_pid}) …"
        _kill_pid "$old_pid"
        rm -f "$PID_FILE"
    fi

    _kill_port_occupants

    info "前台启动 SoloX：${HOST}:${PORT}（Ctrl+C 停止）"
    cd "$PROJECT_DIR"
    $PYTHON -m solox --host="$HOST" --port="$PORT"
}

usage() {
    cat <<EOF
${C_CYAN}SoloX 开发服务脚本${C_RESET}

${C_GREEN}用法:${C_RESET}
    $(basename "$0") <命令> [选项]

${C_GREEN}命令:${C_RESET}
    start       后台启动服务
    stop        停止服务
    restart     重启服务
    status      查看进程、端口、/health、设备与版本
    log [N]     查看日志末尾 N 行（默认 50）
    fg          前台启动（调试）

${C_GREEN}环境变量:${C_RESET}
    SOLOX_HOST    监听地址（默认 0.0.0.0）
    SOLOX_PORT    端口（默认 50003）
    SOLOX_PYTHON  Python 可执行文件（默认 python）

${C_GREEN}示例:${C_RESET}
    $(basename "$0") start
    $(basename "$0") status
    SOLOX_PORT=50005 $(basename "$0") start
    $(basename "$0") log 100

${C_GREEN}Windows:${C_RESET} 推荐使用 .\\scripts\\dev.ps1（自动选择 Git Bash 与 Python）
EOF
}

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
        err "未知命令: $1"
        echo ""
        usage
        exit 1
        ;;
esac
