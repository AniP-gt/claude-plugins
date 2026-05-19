#!/usr/bin/env python3
"""Codex セッション要約失敗のリトライキューを消化する。

bash session/retry-pending.sh の Python 化。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.lockfile import MkdirLock  # noqa: E402
from lib.log_rotate import rotate_log_if_needed  # noqa: E402
from lib.notify import Notifier, default_notifier  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = REPO_ROOT
LOG_DIR_LOCAL = Path.home() / ".local" / "state" / "episodic" / "logs"
LOG_FILE = LOG_DIR_LOCAL / "session-retry.log"
STATE_DIR = Path.home() / ".local" / "share" / "episodic" / "state"
LOCK_DIR = STATE_DIR / "retry-pending.lock.d"
RETRY_QUEUE_PY = SCRIPTS_DIR / "retry_queue.py"
HOOK_PY = SCRIPTS_DIR / "hook.py"

import re

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _log(msg: str) -> None:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def run(notifier: Notifier | None = None) -> int:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LOG_DIR_LOCAL, 0o700)
    except OSError:
        pass
    rotate_log_if_needed(LOG_FILE)

    if not RETRY_QUEUE_PY.is_file():
        _log(f"retry_queue.py not found: {RETRY_QUEUE_PY}")
        return 0
    if not HOOK_PY.is_file():
        _log(f"hook.py not found: {HOOK_PY}")
        return 0

    max_attempts_env = os.environ.get("MEMORIES_RETRY_MAX_ATTEMPTS", "5")
    max_attempts = int(max_attempts_env) if max_attempts_env.isdigit() else 5

    lock = MkdirLock(LOCK_DIR)
    if not lock.acquire():
        _log("skip: another retry-pending is running")
        return 0

    try:
        _log(f"retry-pending start: pid={os.getpid()} max_attempts={max_attempts}")
        try:
            result = subprocess.run(
                [sys.executable, str(RETRY_QUEUE_PY), "list", "--max-attempts", "9999"],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            entries_text = result.stdout
        except (OSError, subprocess.SubprocessError) as e:
            _log(f"warn: retry_queue list failed: {e}")
            return 0

        if not entries_text.strip():
            _log("skip: queue empty")
            return 0

        dead_letter_batch = 0
        spawned = 0
        dropped_report = 0
        dropped_transcript = 0

        for line in entries_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            sid = entry.get("session_id", "")
            cwd = entry.get("cwd", "")
            transcript = entry.get("transcript_path", "")
            report_path = entry.get("report_path", "")
            attempt = int(entry.get("attempt_count", 0) or 0)

            if not sid:
                _log(f"warn: malformed entry (no session_id), skipping: {line}")
                continue
            if not UUID_RE.match(sid):
                _log(f"warn: skip entry (invalid session_id): {sid}")
                continue

            if report_path and Path(report_path).is_file():
                _log(f"drop (report exists): session={sid} path={report_path}")
                _retry_remove(sid)
                dropped_report += 1
                continue

            if not transcript or not Path(transcript).is_file():
                _log(f"drop (transcript missing): session={sid} transcript={transcript}")
                _retry_remove(sid)
                dropped_transcript += 1
                continue

            if attempt >= max_attempts:
                _log(f"promote dead_letter: session={sid} attempt={attempt}")
                _retry_promote_dead_letter(sid)
                dead_letter_batch += 1
                continue

            _log(f"spawn retry: session={sid} attempt={attempt} cwd={cwd}")
            payload = json.dumps({
                "session_id": sid,
                "cwd": cwd,
                "transcript_path": transcript,
                "source": "retry",
            })
            try:
                env = dict(os.environ)
                env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
                subprocess.run(
                    [sys.executable, str(HOOK_PY)],
                    input=payload,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                    env=env,
                )
            except (OSError, subprocess.SubprocessError) as e:
                _log(f"warn: hook.py invocation failed for session={sid}: {e}")
            spawned += 1

        _log(
            f"retry-pending done: spawned={spawned} dropped_report={dropped_report} "
            f"dropped_transcript={dropped_transcript} dead_letter={dead_letter_batch}"
        )

        if dead_letter_batch > 0:
            notifier = notifier or default_notifier("Episodic Recording")
            notifier.notify(
                "失敗",
                f"{dead_letter_batch} 件のセッション要約が {max_attempts} 回失敗し dead_letter に移送されました。詳細: {STATE_DIR}/session-retry-deadletter.jsonl",
                sound="Basso",
            )

        return 0
    finally:
        lock.release()


def _retry_remove(sid: str) -> None:
    try:
        subprocess.run(
            [sys.executable, str(RETRY_QUEUE_PY), "remove", "--", sid],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _retry_promote_dead_letter(sid: str) -> None:
    try:
        subprocess.run(
            [sys.executable, str(RETRY_QUEUE_PY), "promote-dead-letter", "--", sid],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv: list[str] | None = None) -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
