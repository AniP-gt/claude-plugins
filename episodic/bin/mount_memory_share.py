#!/usr/bin/env python3
"""SMB 共有を memories マウントポイントへマウントする macOS 用ヘルパー。

bash bin/mount-memory-share.sh の Python 化。

設定の優先順位: 環境変数 > secrets.env > config.toml > プレースホルダ既定。
macOS 以外、または /sbin/mount_smbfs が無ければスキップ。
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CONFIG_DIR = Path(os.environ.get("MEMORIES_CONFIG_DIR") or (Path.home() / ".config" / "episodic"))
CONFIG_TOML = CONFIG_DIR / "config.toml"
SECRETS_ENV = CONFIG_DIR / "secrets.env"
LOG_DIR = Path.home() / ".local" / "state" / "episodic" / "logs"
LOG_FILE = LOG_DIR / "smb-mount.log"


def _log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LOG_DIR, 0o700)
    except OSError:
        pass
    if not LOG_FILE.exists():
        LOG_FILE.touch()
    try:
        os.chmod(LOG_FILE, 0o600)
    except OSError:
        pass
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def _mask_smb_url(url: str) -> str:
    return re.sub(r"^(smb://)[^@/]+@", r"\1***@", url)


def _toml_get(key: str, file: Path) -> str:
    if not file.is_file():
        return ""
    try:
        for line in file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            m = re.match(rf"^\s*{re.escape(key)}\s*=\s*(.*)$", line)
            if not m:
                continue
            val = m.group(1)
            val = re.sub(r"\s*#.*$", "", val).strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            return val
    except OSError:
        pass
    return ""


def _load_secrets_env() -> dict[str, str]:
    if not SECRETS_ENV.is_file():
        return {}
    try:
        perm = SECRETS_ENV.stat().st_mode & 0o777
    except OSError:
        return {}
    if perm != 0o600:
        _log(f"warn: {SECRETS_ENV} permissions are {oct(perm)[2:]} (expected 600). Skipping load to avoid leaking secrets.")
        return {}
    out: dict[str, str] = {}
    try:
        for line in SECRETS_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            out[key] = val
    except OSError:
        pass
    return out


def run() -> int:
    if platform.system() != "Darwin":
        _log(f"skip: non-macOS platform ({platform.system()}); mount_smbfs is mac-only")
        return 0
    for req in ("/sbin/mount", "/sbin/ping", "/sbin/mount_smbfs"):
        if not (Path(req).exists() and os.access(req, os.X_OK)):
            _log(f"skip: required macOS commands not found ({req})")
            return 0

    secrets = _load_secrets_env()
    mount_point = (
        os.environ.get("MEMORIES_DIR")
        or _toml_get("memories_dir", CONFIG_TOML)
        or "/Volumes/memory"
    )
    share_base = (
        os.environ.get("MEMORIES_SMB_SHARE")
        or secrets.get("MEMORIES_SMB_SHARE")
        or _toml_get("smb_share", CONFIG_TOML)
        or "//user@server.local/share"
    )
    smb_user = os.environ.get("MEMORIES_SMB_USER") or secrets.get("MEMORIES_SMB_USER", "")
    if smb_user and "@" not in share_base:
        share = f"//{smb_user}@{share_base[2:]}"
    else:
        share = share_base

    ping_host = (
        os.environ.get("MEMORIES_SMB_PING_HOST")
        or secrets.get("MEMORIES_SMB_PING_HOST")
        or _toml_get("smb_ping_host", CONFIG_TOML)
    )
    if not ping_host:
        no_proto = share[2:] if share.startswith("//") else share
        no_user = no_proto.split("@")[-1]
        ping_host = no_user.split("/")[0]

    # 既マウントなら NoOp
    try:
        mounts = subprocess.run(
            ["/sbin/mount"], capture_output=True, text=True, check=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        mounts = ""
    if f" on {mount_point} " in mounts:
        _log(f"already mounted: {mount_point}")
        return 0

    # ping
    try:
        r = subprocess.run(
            ["/sbin/ping", "-c", "1", "-t", "5", ping_host],
            capture_output=True,
            timeout=15,
            check=False,
        )
        if r.returncode != 0:
            _log(f"host unreachable: {ping_host}")
            return 1
    except (OSError, subprocess.SubprocessError):
        _log(f"host unreachable: {ping_host}")
        return 1

    mp = Path(mount_point)
    if not mp.is_dir():
        _log(f"abort: mount point does not exist: {mount_point}")
        _log("  initial setup (one-time, requires sudo):")
        _log(f'    sudo install -d -o "$(id -un)" -g staff -m 0755 {mount_point}')
        return 4

    canary = mp / ".mount-canary"
    if not canary.exists():
        try:
            non_empty = any(mp.iterdir())
        except OSError:
            non_empty = False
        if non_empty:
            stub_backup = Path.home() / ".local" / "share" / "episodic" / f"legacy-stub-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            _log(f"abort: stale local stub detected at {mount_point} (no canary, non-empty)")
            _log("  retire the stub and recreate an empty mount point:")
            _log(f"    sudo mv {mount_point} {stub_backup} \\")
            _log(f'      && sudo install -d -o "$(id -un)" -g staff -m 0755 {mount_point}')
            return 5

    smb_url = f"smb://{share[2:]}" if share.startswith("//") else f"smb://{share}"
    masked = _mask_smb_url(smb_url)
    try:
        r = subprocess.run(
            ["/sbin/mount_smbfs", "-N", "-o", "nobrowse,nodev,nosuid", share, mount_point],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        stderr_masked = re.sub(r"(//)[^@/\s]+@", r"\1***@", r.stderr or "")
        if stderr_masked:
            _log(stderr_masked.strip())
        if r.returncode == 0:
            _log(f"mounted: {masked} -> {mount_point}")
            return 0
        _log(f"mount failed: rc={r.returncode} url={masked} (check keychain credentials and server availability)")
        return 2
    except (OSError, subprocess.SubprocessError) as e:
        _log(f"mount failed: exception {e}")
        return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
