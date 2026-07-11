#!/usr/bin/env bash
# 一键管理平台本地开发环境：Hermes、后端 FastAPI 和前端 Vite。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
WEB_DIR="$ROOT_DIR/web"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1}"

BACKEND_PID="$RUNTIME_DIR/backend.pid"
WEB_PID="$RUNTIME_DIR/web.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
WEB_LOG="$LOG_DIR/web.log"
HERMES_PROFILE="${HERMES_PROFILE:-aiplatform}"
HERMES_WRAPPER="${HERMES_WRAPPER:-$HOME/.local/bin/$HERMES_PROFILE}"
HERMES_PID="$RUNTIME_DIR/hermes-${HERMES_PROFILE}.pid"
HERMES_LOG="$LOG_DIR/hermes-${HERMES_PROFILE}.log"

mkdir -p "$LOG_DIR"

usage() {
  cat <<EOF
Usage: ./platform-dev.sh <start|stop|restart|status|logs>

Commands:
  start     启动 Hermes API Server、后端 FastAPI 和前端 Vite
  stop      关闭前端、后端和本平台专用 Hermes profile
  restart   重启 Hermes、后端和前端
  status    查看 Hermes、后端和前端进程状态
  logs      跟随查看 Hermes、后端和前端日志

Environment overrides:
  HERMES_PROFILE=$HERMES_PROFILE
  BACKEND_HOST=$BACKEND_HOST
  BACKEND_PORT=$BACKEND_PORT
  WEB_HOST=$WEB_HOST
  WEB_PORT=$WEB_PORT
  VITE_API_BASE_URL=$VITE_API_BASE_URL
EOF
}

is_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

pid_from_file() {
  local file="$1"
  [[ -f "$file" ]] && tr -d '[:space:]' < "$file" || true
}

env_value() {
  local key="$1"
  local file="$BACKEND_DIR/.env"
  [[ -f "$file" ]] || return 0
  awk -F= -v key="$key" '$1 == key {print substr($0, length(key) + 2); exit}' "$file"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local pid_file="$3"
  local attempts="${4:-40}"
  local i
  local pid

  for ((i = 1; i <= attempts; i += 1)); do
    pid="$(pid_from_file "$pid_file")"
    if ! is_running "$pid"; then
      echo "$name 进程已退出，查看日志：$LOG_DIR" >&2
      return 1
    fi
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name 已就绪：$url"
      return 0
    fi
    sleep 0.5
  done

  echo "$name 启动后未在预期时间内就绪：$url" >&2
  return 1
}

wait_for_hermes() {
  local key
  local header_args=()
  key="$(env_value AI_PLATFORM_HERMES_API_KEY)"
  if [[ -n "$key" ]]; then
    header_args=(-H "Authorization: Bearer $key")
  fi

  local i
  local pid
  for ((i = 1; i <= 80; i += 1)); do
    pid="$(pid_from_file "$HERMES_PID")"
    if ! is_running "$pid"; then
      echo "Hermes 进程已退出，查看日志：$HERMES_LOG" >&2
      return 1
    fi
    if curl -fsS "${header_args[@]}" "http://127.0.0.1:8642/health" >/dev/null 2>&1; then
      echo "Hermes API Server 已就绪：http://127.0.0.1:8642"
      return 0
    fi
    sleep 0.5
  done

  echo "Hermes API Server 启动后未在预期时间内就绪：http://127.0.0.1:8642" >&2
  return 1
}

start_hermes() {
  local pid
  pid="$(pid_from_file "$HERMES_PID")"
  if is_running "$pid"; then
    echo "Hermes 已运行：profile $HERMES_PROFILE，PID $pid"
    return 0
  fi
  if [[ ! -x "$HERMES_WRAPPER" ]]; then
    echo "Hermes profile wrapper 不存在或不可执行：$HERMES_WRAPPER" >&2
    return 1
  fi

  echo "启动 Hermes：profile $HERMES_PROFILE，API Server http://127.0.0.1:8642"
  setsid "$HERMES_WRAPPER" gateway run > "$HERMES_LOG" 2>&1 < /dev/null &
  echo $! > "$HERMES_PID"
  wait_for_hermes
}

start_backend() {
  local pid
  pid="$(pid_from_file "$BACKEND_PID")"
  if is_running "$pid"; then
    echo "后端已运行：PID $pid"
    return 0
  fi

  echo "启动后端：http://${BACKEND_HOST}:${BACKEND_PORT}"
  (
    cd "$BACKEND_DIR"
    setsid "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! > "$BACKEND_PID"
  )
  wait_for_http "后端" "http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1/system/dependencies" "$BACKEND_PID" 60
}

start_web() {
  local pid
  pid="$(pid_from_file "$WEB_PID")"
  if is_running "$pid"; then
    echo "前端已运行：PID $pid"
    return 0
  fi

  echo "启动前端：http://${WEB_HOST}:${WEB_PORT}"
  (
    cd "$WEB_DIR"
    VITE_API_BASE_URL="$VITE_API_BASE_URL" setsid "$WEB_DIR/node_modules/.bin/vite" --host "$WEB_HOST" --port "$WEB_PORT" --strictPort > "$WEB_LOG" 2>&1 < /dev/null &
    echo $! > "$WEB_PID"
  )
  wait_for_http "前端" "http://${WEB_HOST}:${WEB_PORT}/" "$WEB_PID" 60
}

fallback_pids() {
  local service="$1"
  case "$service" in
    backend)
      pgrep -f "uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT}" || true
      ;;
    web)
      pgrep -f "${WEB_DIR}/node_modules/.bin/vite --host ${WEB_HOST} --port ${WEB_PORT}" || true
      ;;
    hermes)
      pgrep -f "hermes -p ${HERMES_PROFILE} gateway run" || true
      pgrep -f "${HERMES_WRAPPER} gateway run" || true
      ;;
  esac
}

stop_pid() {
  local label="$1"
  local pid="$2"

  if ! is_running "$pid"; then
    return 0
  fi

  echo "关闭${label}：PID $pid"
  kill "$pid" >/dev/null 2>&1 || true

  local i
  for ((i = 1; i <= 20; i += 1)); do
    if ! is_running "$pid"; then
      return 0
    fi
    sleep 0.25
  done

  echo "${label}未正常退出，强制结束：PID $pid"
  kill -9 "$pid" >/dev/null 2>&1 || true
}

stop_service() {
  local service="$1"
  local label="$2"
  local pid_file="$3"
  local pid

  pid="$(pid_from_file "$pid_file")"
  stop_pid "$label" "$pid"
  while read -r pid; do
    [[ -n "$pid" ]] && stop_pid "$label" "$pid"
  done < <(fallback_pids "$service")
  rm -f "$pid_file"
}

status_service() {
  local service="$1"
  local label="$2"
  local pid_file="$3"
  local url="$4"
  local pid

  pid="$(pid_from_file "$pid_file")"
  if is_running "$pid"; then
    echo "${label}：运行中，PID $pid，$url"
    return 0
  fi

  local fallback
  fallback="$(fallback_pids "$service" | paste -sd ',' -)"
  if [[ -n "$fallback" ]]; then
    echo "${label}：运行中，PID $fallback，$url"
  else
    echo "${label}：未运行"
  fi
}

case "${1:-}" in
  start)
    start_hermes
    start_backend
    start_web
    echo
    echo "前端：http://${WEB_HOST}:${WEB_PORT}/"
    echo "后端：http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1"
    echo "Hermes API Server：http://127.0.0.1:8642"
    echo "日志：$LOG_DIR"
    ;;
  stop)
    stop_service web "前端" "$WEB_PID"
    stop_service backend "后端" "$BACKEND_PID"
    stop_service hermes "Hermes" "$HERMES_PID"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    status_service hermes "Hermes" "$HERMES_PID" "http://127.0.0.1:8642"
    status_service backend "后端" "$BACKEND_PID" "http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1"
    status_service web "前端" "$WEB_PID" "http://${WEB_HOST}:${WEB_PORT}/"
    ;;
  logs)
    touch "$HERMES_LOG" "$BACKEND_LOG" "$WEB_LOG"
    tail -f "$HERMES_LOG" "$BACKEND_LOG" "$WEB_LOG"
    ;;
  *)
    usage
    exit 1
    ;;
esac
