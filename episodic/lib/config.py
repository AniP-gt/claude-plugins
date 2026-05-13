"""memory プラグイン共通設定ローダー。

設定の優先順位（先勝ち）:
  1. 環境変数（MEMORIES_DIR / MEMORIES_FALLBACK_DIR / MEMORIES_AUTO_REMOUNT 等）
  2. ~/.config/episodic/config.toml
  3. 既定値（/Volumes/memory, ~/.local/share/episodic/raw-staging）

公開 API:
  - load_config()                  -> dict
  - resolve_memories_dir()         -> Path
  - resolve_fallback_dir()         -> Path
  - is_mount_active(memories_dir)  -> bool   # canary ファイルの実在で判定
  - effective_raw_root()           -> tuple[Path, bool]  # (raw_root, is_staged)
  - host_hash(length=8)            -> str
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import]
else:  # pragma: no cover - Python 3.10 互換用フォールバック
    import tomli as tomllib  # type: ignore[no-redef]

from .plugin_root import plugin_root


CONFIG_PATH = Path.home() / ".config" / "episodic" / "config.toml"


def _default_remount_script() -> str:
    # source repo / codex-hook-runtime いずれも bin/mount-memory-share.sh で統一済み。
    return str(plugin_root() / "bin" / "mount-memory-share.sh")

DEFAULTS: dict[str, Any] = {
    "memories_dir": "/Volumes/memory",
    "fallback_dir": "~/.local/share/episodic/raw-staging",
    "auto_remount": True,
    "remount_script": _default_remount_script(),
    "mount_canary_filename": ".mount-canary",
    "hostname_hash_length": 8,
    "stop_debounce_seconds": 60,
}


def _expand(path_str: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """config.toml を読み、環境変数オーバーライドを適用したマージ済み dict を返す。"""
    cfg: dict[str, Any] = dict(DEFAULTS)

    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("rb") as f:
                user_cfg = tomllib.load(f) or {}
            for k, v in user_cfg.items():
                if k in DEFAULTS:
                    cfg[k] = v
        except (OSError, tomllib.TOMLDecodeError):
            pass

    env_map = {
        "memories_dir": "MEMORIES_DIR",
        "fallback_dir": "MEMORIES_FALLBACK_DIR",
        "auto_remount": "MEMORIES_AUTO_REMOUNT",
        "remount_script": "MEMORIES_REMOUNT_SCRIPT",
        "mount_canary_filename": "MEMORIES_MOUNT_CANARY",
    }
    for key, env_name in env_map.items():
        val = os.environ.get(env_name)
        if val is None or val == "":
            continue
        if key == "auto_remount":
            cfg[key] = val.lower() in ("1", "true", "yes", "on")
        else:
            cfg[key] = val

    hash_env = os.environ.get("MEMORIES_HOSTNAME_HASH_LENGTH")
    if hash_env and hash_env.isdigit():
        n = int(hash_env)
        if 4 <= n <= 40:
            cfg["hostname_hash_length"] = n

    debounce_env = os.environ.get("MEMORIES_STOP_DEBOUNCE_SECONDS")
    if debounce_env and debounce_env.isdigit():
        n = int(debounce_env)
        if 0 <= n <= 600:
            cfg["stop_debounce_seconds"] = n

    return cfg


def resolve_memories_dir() -> Path:
    return _expand(str(load_config()["memories_dir"])).resolve()


def resolve_fallback_dir() -> Path:
    return _expand(str(load_config()["fallback_dir"])).resolve()


def resolve_remount_script() -> Path:
    return _expand(str(load_config()["remount_script"]))


def mount_canary_path(memories_dir: Path | None = None) -> Path:
    base = memories_dir or resolve_memories_dir()
    return base / str(load_config()["mount_canary_filename"])


def is_mount_active(memories_dir: Path | None = None) -> bool:
    """Canary ファイルの実在のみを真の判定根拠にする。

    `${MEMORIES_DIR}` ディレクトリ自体は OS が自動生成し得るため存在チェックでは不十分。
    SMB 共有のルート直下に固定で置いた canary が見えていればマウント成立とみなす。
    """
    canary = mount_canary_path(memories_dir)
    try:
        return canary.is_file()
    except OSError:
        return False


def effective_raw_root() -> tuple[Path, bool]:
    """session レポートの実書き込み先 raw ルートと staged フラグを返す。

    session 専用（web / minutes は別経路で保存される）。

    Returns:
        (raw_root, is_staged)
        マウント成立: (memories_dir/raw/session, False)
        未成立     : (fallback_dir, True)
    """
    if is_mount_active():
        return resolve_memories_dir() / "raw" / "session", False
    return resolve_fallback_dir(), True


def effective_snapshot_root() -> tuple[Path, bool]:
    """session の元 JSONL snapshot 保存先 root と staged フラグを返す。

    raw/session レポートが派生物（codex 要約）であるのに対し、本 root には
    元 JSONL の不変コピーを置く。再要約・検証時の source of truth。

    Returns:
        (snapshot_root, is_staged)
        マウント成立: (memories_dir/raw/session-source, False)
        未成立     : (fallback_dir/session-source, True)
    """
    if is_mount_active():
        return resolve_memories_dir() / "raw" / "session-source", False
    return resolve_fallback_dir() / "session-source", True


def resolve_stop_debounce_seconds() -> int:
    """Stop hook 起動から Codex 要約までの debounce 秒数。範囲 0-600（既定 60）。"""
    return int(load_config().get("stop_debounce_seconds", 60))


@lru_cache(maxsize=1)
def _machine_id() -> str:
    """macOS の IOPlatformUUID をマシン固有 ID として返す。

    socket.gethostname() は Wi-Fi / DHCP / mDNS の状態によって動的に変動し、
    同一マシン内でも値が揺れる（例: MacBookPro.local ↔ 別形式）。揺れると
    host_hash も変わり、report_path のパス重複検知が空振りする。
    IOPlatformUUID はハードウェア固有の不変値なので、これをハッシュ元にする。
    """
    try:
        proc = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"failed to invoke ioreg: {exc}") from exc
    for line in proc.stdout.splitlines():
        if "IOPlatformUUID" in line:
            parts = line.split('"')
            if len(parts) >= 4 and parts[3]:
                return parts[3]
    raise RuntimeError("IOPlatformUUID not found in ioreg output")


@lru_cache(maxsize=1)
def host_hash(length: int | None = None) -> str:
    """machine id (macOS IOPlatformUUID) の SHA-1 先頭 N 文字（小文字 hex）を返す。

    複数マシンが同じ MEMORIES_DIR を共有しても session_id 衝突に巻き込まれない。
    socket.gethostname() ベースだと値が動的に揺れて report_path の重複検知が
    壊れるため、ハードウェア固有 ID を採用する。
    """
    n = length or int(load_config()["hostname_hash_length"])
    digest = hashlib.sha1(_machine_id().encode("utf-8")).hexdigest()
    return digest[:n]
