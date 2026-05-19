#!/usr/bin/env python3
"""wiki-runner の debounced launcher。

bash wiki/kick-runner.sh の Python 化。

- KICK_LOCK で重複起動を抑制（10 分超過の stale は奪取）
- detach した子プロセスで:
    1. DEBOUNCE_SECONDS sleep
    2. runner が active な間 polling
    3. queue に ready な work があれば wiki_runner.py を起動
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STATE_DIR = Path.home() / ".local" / "share" / "episodic" / "state"
QUEUE = STATE_DIR / "ingest-queue.jsonl"
RUNNER_LOCK_DIR = STATE_DIR / "lock.d"
KICK_LOCK_DIR = STATE_DIR / "wiki-runner-kick.lock.d"
LOG_DIR_LOCAL = Path.home() / ".local" / "state" / "episodic" / "logs"
LOG_FILE = LOG_DIR_LOCAL / "wiki-runner.log"


def _log(msg: str) -> None:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def _retry_epoch(value) -> float:
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


def queue_has_ready_work(queue_path: Path = QUEUE, now: float | None = None) -> bool:
    if not queue_path.is_file():
        return False
    now = now if now is not None else time.time()
    try:
        with queue_path.open(encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            lines = f.read().splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = d.get("status") or "pending"
        if status == "pending":
            ra = _retry_epoch(d.get("retry_after_epoch") or d.get("retry_after"))
            if ra <= now:
                return True
        elif status == "processing":
            ps = _retry_epoch(d.get("processing_started_epoch") or d.get("processing_started_at"))
            if now - ps >= 3600:
                return True
    return False


def is_runner_active() -> bool:
    if not RUNNER_LOCK_DIR.is_dir():
        return False
    try:
        pid_str = (RUNNER_LOCK_DIR / "pid").read_text().strip()
        pid = int(pid_str)
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        # stale
        try:
            import shutil

            shutil.rmtree(RUNNER_LOCK_DIR, ignore_errors=True)
        except OSError:
            pass
        return False


def _try_acquire_kick_lock() -> bool:
    # 10 分以上経過した stale を撤去
    if KICK_LOCK_DIR.is_dir():
        try:
            age = time.time() - KICK_LOCK_DIR.stat().st_mtime
            if age > 600:
                import shutil

                shutil.rmtree(KICK_LOCK_DIR, ignore_errors=True)
        except OSError:
            pass
    try:
        KICK_LOCK_DIR.parent.mkdir(parents=True, exist_ok=True)
        KICK_LOCK_DIR.mkdir()
    except (FileExistsError, OSError):
        return False
    try:
        (KICK_LOCK_DIR / "pid").write_text(f"{os.getpid()}\n")
    except OSError:
        pass
    return True


def _resolve_runner() -> list[str] | None:
    py_runner = REPO_ROOT / "wiki" / "wiki_runner.py"
    sh_runner = REPO_ROOT / "wiki" / "wiki-runner.sh"
    if py_runner.is_file():
        return [sys.executable, str(py_runner)]
    if sh_runner.is_file() and os.access(sh_runner, os.X_OK):
        return [str(sh_runner)]
    return None


def _debounce_and_launch(debounce_seconds: int) -> None:
    time.sleep(debounce_seconds)
    while is_runner_active():
        time.sleep(debounce_seconds)
    try:
        import shutil

        shutil.rmtree(KICK_LOCK_DIR, ignore_errors=True)
    except OSError:
        pass
    cmd = _resolve_runner()
    if cmd is None:
        _log("kick: wiki-runner not found")
        return
    if not queue_has_ready_work():
        _log("kick: no ready queue entry")
        return
    _log("kick: starting wiki-runner")
    try:
        with LOG_FILE.open("ab") as f:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except (OSError, FileNotFoundError) as e:
        _log(f"kick: launch failed: {e}")


def main(argv: list[str] | None = None) -> int:
    debounce_env = os.environ.get("MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS", "5")
    debounce_seconds = int(debounce_env) if debounce_env.isdigit() else 5

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(STATE_DIR, 0o700)
        os.chmod(LOG_DIR_LOCAL, 0o700)
    except OSError:
        pass

    if not _try_acquire_kick_lock():
        _log("kick skipped: debounced")
        return 0

    # 親プロセスから切り離して debounce + launch を実行（double-fork 相当）。
    if os.fork() == 0:
        try:
            os.setsid()
        except OSError:
            pass
        if os.fork() == 0:
            try:
                _debounce_and_launch(debounce_seconds)
            finally:
                os._exit(0)
        else:
            os._exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
