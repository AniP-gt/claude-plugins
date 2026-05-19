"""bin/mount_memory_share.py の単体テスト。"""
from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MEMORIES_CONFIG_DIR", str(tmp_path / "config"))
    sys.modules.pop("mount_memory_share", None)
    m = importlib.import_module("mount_memory_share")
    importlib.reload(m)
    return m


def test_non_macos_skips(mod, monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    assert mod.run() == 0


def test_required_command_missing(mod, monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    # /sbin/mount_smbfs が無い前提で os.access を強制 False に
    monkeypatch.setattr(mod.os, "access", lambda p, m: False)
    assert mod.run() == 0


def test_toml_get_basic(mod, tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text('memories_dir = "/x/y"\nsmb_share = "//u@h/s"\n')
    assert mod._toml_get("memories_dir", p) == "/x/y"
    assert mod._toml_get("smb_share", p) == "//u@h/s"
    assert mod._toml_get("missing", p) == ""


def test_mask_smb_url(mod) -> None:
    assert mod._mask_smb_url("smb://user@host/share") == "smb://***@host/share"
    assert mod._mask_smb_url("smb://host/share") == "smb://host/share"
