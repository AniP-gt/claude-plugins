"""lib/lockfile.py の単体テスト。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.lockfile import MkdirLock  # noqa: E402


def test_acquire_success(tmp_path: Path) -> None:
    lock = MkdirLock(tmp_path / "lock.d")
    assert lock.acquire() is True
    assert (tmp_path / "lock.d" / "pid").read_text().strip() == str(os.getpid())
    lock.release()
    assert not (tmp_path / "lock.d").exists()


def test_double_acquire_skips(tmp_path: Path) -> None:
    lock_dir = tmp_path / "lock.d"
    a = MkdirLock(lock_dir)
    b = MkdirLock(lock_dir)
    assert a.acquire() is True
    assert b.acquire() is False
    a.release()


def test_pid_empty_treated_as_busy(tmp_path: Path) -> None:
    lock_dir = tmp_path / "lock.d"
    lock_dir.mkdir(parents=True)
    (lock_dir / "pid").write_text("")
    lock = MkdirLock(lock_dir)
    assert lock.acquire() is False


def test_stale_lock_is_reaped(tmp_path: Path) -> None:
    lock_dir = tmp_path / "lock.d"
    lock_dir.mkdir(parents=True)
    # 存在しない PID を書き込む（PID 1 は init、PID 999999 は不在想定）
    (lock_dir / "pid").write_text("999999\n")
    lock = MkdirLock(lock_dir)
    assert lock.acquire() is True
    assert (lock_dir / "pid").read_text().strip() == str(os.getpid())
    lock.release()


def test_release_only_when_owned(tmp_path: Path) -> None:
    """別 PID が握っているロックは release で消さない。"""
    lock_dir = tmp_path / "lock.d"
    lock_dir.mkdir(parents=True)
    (lock_dir / "pid").write_text("1\n")  # init PID 想定（生存中）
    lock = MkdirLock(lock_dir)
    # acquire していない release は no-op
    lock.release()
    assert (lock_dir / "pid").exists()


def test_context_manager(tmp_path: Path) -> None:
    lock_dir = tmp_path / "lock.d"
    with MkdirLock(lock_dir) as ok:
        assert ok is True
        assert lock_dir.exists()
    assert not lock_dir.exists()
