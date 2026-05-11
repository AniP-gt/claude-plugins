#!/usr/bin/env bash
# Debounced launcher for wiki-runner.sh.
# Multiple enqueue events within MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS are folded
# into one runner launch. If a runner is already active, this waits until the
# active lock clears and then starts a new runner only when queue still has work.
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIKI_RUNNER="${SCRIPT_DIR}/wiki-runner.sh"
STATE_DIR="${HOME}/.local/share/episodic/state"
QUEUE="$STATE_DIR/ingest-queue.jsonl"
RUNNER_LOCK_DIR="$STATE_DIR/lock.d"
KICK_LOCK_DIR="$STATE_DIR/wiki-runner-kick.lock.d"
LOG_DIR_LOCAL="$HOME/.local/state/episodic/logs"
LOG_FILE="$LOG_DIR_LOCAL/wiki-runner.log"
DEBOUNCE_SECONDS="${MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS:-5}"

mkdir -p "$STATE_DIR" "$LOG_DIR_LOCAL"
chmod 700 "$STATE_DIR" "$LOG_DIR_LOCAL" 2>/dev/null || true

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

is_runner_active() {
    local pid
    [[ ! -d "$RUNNER_LOCK_DIR" ]] && return 1
    pid=$(cat "$RUNNER_LOCK_DIR/pid" 2>/dev/null || echo "")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    rm -rf "$RUNNER_LOCK_DIR"
    return 1
}

queue_has_ready_work() {
    QUEUE_PATH="$QUEUE" python3 -c '
import fcntl, json, os, sys, time
from datetime import datetime
from pathlib import Path

q = Path(os.environ["QUEUE_PATH"])
if not q.exists():
    sys.exit(1)
now = time.time()

def retry_epoch(value):
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0

with q.open(encoding="utf-8") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
    lines = f.read().splitlines()
for line in lines:
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        continue
    status = d.get("status") or "pending"
    if status == "pending" and retry_epoch(d.get("retry_after_epoch") or d.get("retry_after")) <= now:
        sys.exit(0)
    if status == "processing" and now - retry_epoch(d.get("processing_started_epoch") or d.get("processing_started_at")) >= 3600:
        sys.exit(0)
sys.exit(1)
'
}

if ! [[ "$DEBOUNCE_SECONDS" =~ ^[0-9]+$ ]]; then
    DEBOUNCE_SECONDS=5
fi

if [[ -d "$KICK_LOCK_DIR" ]] && [[ -n "$(find "$KICK_LOCK_DIR" -prune -mmin +10 -print 2>/dev/null)" ]]; then
    rm -rf "$KICK_LOCK_DIR"
fi

if mkdir "$KICK_LOCK_DIR" 2>/dev/null; then
    echo $$ > "$KICK_LOCK_DIR/pid"
else
    log "kick skipped: debounced"
    exit 0
fi

(
    sleep "$DEBOUNCE_SECONDS"
    while is_runner_active; do
        sleep "$DEBOUNCE_SECONDS"
    done
    rm -rf "$KICK_LOCK_DIR"
    if [[ -x "$WIKI_RUNNER" ]] && queue_has_ready_work; then
        log "kick: starting wiki-runner"
        nohup "$WIKI_RUNNER" >> "$LOG_FILE" 2>&1 &
    else
        log "kick: no ready queue entry"
    fi
) >/dev/null 2>&1 &

exit 0
