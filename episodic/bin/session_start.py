#!/usr/bin/env python3
"""SessionStart hook: SMB マウント試行 → 取り残された debounce セッションの finalize → staging 移送。

bash bin/session-start.sh の Python 化。失敗してもセッション開始を妨げない（常に exit 0）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
BIN_DIR = Path(__file__).resolve().parent
LOG_DIR_LOCAL = Path.home() / ".local" / "state" / "episodic" / "logs"


def _is_pid_alive(pid_str: str) -> bool:
    if not pid_str:
        return False
    try:
        pid = int(pid_str)
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def _respawn_finalize(hook_py: Path, sid: str, log_file: Path) -> None:
    try:
        with log_file.open("ab") as f:
            subprocess.Popen(
                [sys.executable, str(hook_py), "--finalize", sid],
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except (OSError, FileNotFoundError):
        pass


def _detect_pending_sessions() -> None:
    pending_root = Path.home() / ".local" / "state" / "episodic" / "pending"
    hook_py = BIN_DIR.parent / "session" / "hook.py"
    if not pending_root.is_dir() or not hook_py.is_file():
        return
    log_file = LOG_DIR_LOCAL / "session-hook.log"

    for session_dir in pending_root.iterdir():
        if not session_dir.is_dir():
            continue
        sid = session_dir.name
        if not UUID_RE.match(sid):
            continue

        lock_pid_file = session_dir / ".lock" / "pid"
        if lock_pid_file.is_file():
            try:
                pid_str = lock_pid_file.read_text().strip()
            except OSError:
                pid_str = ""
            if _is_pid_alive(pid_str):
                continue

        debounce_pid_file = session_dir / ".debounce.pid"
        if debounce_pid_file.is_file():
            try:
                pid_str = debounce_pid_file.read_text().strip()
            except OSError:
                pid_str = ""
            if _is_pid_alive(pid_str):
                continue

        # debounce 中のシャットダウン等で未消費の Stop payload が残っている場合は、
        # 重処理（Markdown 変換・meta 生成）ごと finalize に委ねる。
        payloads = sorted(session_dir.glob("*.payload.json"))
        if payloads:
            _respawn_finalize(hook_py, sid, log_file)
            continue

        metas = sorted(session_dir.glob("*.codex.meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not metas:
            shutil.rmtree(session_dir, ignore_errors=True)
            continue
        meta = metas[0]
        try:
            with meta.open(encoding="utf-8") as f:
                data = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            continue
        report_path = data.get("report_path", "")
        if not report_path:
            continue
        if Path(report_path).is_file():
            shutil.rmtree(session_dir, ignore_errors=True)
        else:
            _respawn_finalize(hook_py, sid, log_file)


def _mount_attempt() -> None:
    py_mount = BIN_DIR / "mount_memory_share.py"
    sh_mount = BIN_DIR / "mount-memory-share.sh"
    cmd: list[str] | None = None
    if py_mount.is_file():
        cmd = [sys.executable, str(py_mount)]
    elif sh_mount.is_file() and os.access(sh_mount, os.X_OK):
        cmd = [str(sh_mount)]
    if cmd is None:
        return
    try:
        subprocess.run(cmd, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def _sync_pending() -> None:
    py_sync = BIN_DIR / "sync_pending.py"
    sh_sync = BIN_DIR / "sync-pending.sh"
    cmd: list[str] | None = None
    if py_sync.is_file():
        cmd = [sys.executable, str(py_sync)]
    elif sh_sync.is_file() and os.access(sh_sync, os.X_OK):
        cmd = [str(sh_sync)]
    if cmd is None:
        return
    try:
        subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LOG_DIR_LOCAL, 0o700)
    except OSError:
        pass
    _mount_attempt()
    _detect_pending_sessions()
    _sync_pending()
    return 0


if __name__ == "__main__":
    sys.exit(main())
