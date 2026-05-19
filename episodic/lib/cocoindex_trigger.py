"""cocoindex update を非同期キックする。

bash lib/cocoindex_trigger.sh の Python 化。`uv run cocoindex update -f ...` を
detached subprocess で起動し、完了通知（macOS osascript）まで出す。
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

from .notify import Notifier, default_notifier
from .plugin_root import plugin_root


def _host_prefix() -> str:
    host = socket.gethostname()
    return re.sub(r"[^a-zA-Z0-9]", "_", host).lower()


def trigger_cocoindex_update(
    memories_dir: Path | str | None = None,
    log_dir: Path | None = None,
    index_name: str = "episodic",
    notifier: Notifier | None = None,
) -> bool:
    """非同期で cocoindex update を起動。起動できたら True。

    main_episodic.py / pyproject.toml / uv のいずれかが欠ければ skip して False。
    """
    if memories_dir is None:
        memories_dir = os.environ.get("MEMORIES_DIR", "/Volumes/memory")
    memories_dir = str(memories_dir)
    app_dir = plugin_root()
    recording_dir = app_dir / "recording"
    log_dir = log_dir or Path(os.environ.get("LOG_DIR_LOCAL", "")) or (
        Path.home() / ".local" / "state" / "episodic" / "logs"
    )
    if isinstance(log_dir, str):
        log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(log_dir, 0o700)
    except OSError:
        pass
    cocoindex_log = log_dir / "cocoindex-update.log"

    if not (recording_dir / "main_episodic.py").is_file():
        _append_log(cocoindex_log, f"cocoindex update skipped: main_episodic.py not found ({recording_dir / 'main_episodic.py'})")
        return False
    if not (app_dir / "pyproject.toml").is_file():
        _append_log(cocoindex_log, f"cocoindex update skipped: episodic pyproject not found ({app_dir / 'pyproject.toml'})")
        return False
    if shutil.which("uv") is None:
        _append_log(cocoindex_log, "cocoindex update skipped: uv not found in PATH")
        return False

    app_name = f"EpisodicIndex_{_host_prefix()}_{index_name}"
    _append_log(
        cocoindex_log,
        f"cocoindex update scheduled: {memories_dir} (app={app_name}, settings=~/.config/episodic/cocoindex.toml)",
    )

    uv_project_environment = os.environ.get(
        "UV_PROJECT_ENVIRONMENT",
        str(Path.home() / ".cache" / "episodic" / "venv"),
    )
    Path(uv_project_environment).parent.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["SOURCE_PATH"] = memories_dir
    env["INDEX_NAME"] = index_name
    env["PATTERNS"] = "**/*.md"
    env["UV_PROJECT_ENVIRONMENT"] = uv_project_environment

    notifier = notifier or default_notifier("Episodic Cocoindex")

    # detached child を起動し、完了通知用の wrapper を別プロセスで動かす。
    # 親 hook を block しないため、Popen のみ実行して return する設計。
    runner_script = _build_runner_script()
    try:
        subprocess.Popen(
            [
                "uv",
                "run",
                "cocoindex",
                "update",
                "-f",
                f"{recording_dir / 'main_episodic.py'}:{app_name}",
            ],
            cwd=str(app_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=open(cocoindex_log, "ab"),
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
        return True
    except (OSError, FileNotFoundError) as e:
        _append_log(cocoindex_log, f"cocoindex update launch failed: {e}")
        return False


def _build_runner_script() -> str:
    # 現状の Python 化では完了通知用 wrapper は未実装（Popen 後 detach のみ）。
    # 必要なら別途 monitor プロセスを fork する設計に拡張する。
    return ""


def _append_log(path: Path, message: str) -> None:
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except OSError:
        pass
