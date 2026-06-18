"""lib/log_rotate.py の単体テスト。"""
from __future__ import annotations

import gzip
import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.log_rotate import rotate_log_if_needed  # noqa: E402


def test_below_threshold_noop(tmp_path: Path) -> None:
    log = tmp_path / "x.log"
    log.write_text("hello")
    assert rotate_log_if_needed(log, threshold_bytes=10_000) is False
    assert log.read_text() == "hello"


def test_above_threshold_rotates(tmp_path: Path) -> None:
    log = tmp_path / "x.log"
    log.write_bytes(b"X" * 2000)
    assert rotate_log_if_needed(log, threshold_bytes=1000, keep_generations=3) is True
    assert log.exists()
    assert log.stat().st_size == 0
    gz = list(tmp_path.glob("x.log.*.gz"))
    assert len(gz) == 1
    assert gzip.decompress(gz[0].read_bytes()) == b"X" * 2000


def test_keeps_generations(tmp_path: Path) -> None:
    log = tmp_path / "x.log"
    # 既存の古い世代を 5 つ作る
    for i in range(5):
        p = tmp_path / f"x.log.2026010{i}0000.gz"
        p.write_bytes(b"old")
        os.utime(p, (1000 + i, 1000 + i))
    log.write_bytes(b"Y" * 2000)
    rotate_log_if_needed(log, threshold_bytes=1000, keep_generations=2)
    gz = sorted(tmp_path.glob("x.log.*.gz"), key=lambda p: p.stat().st_mtime)
    # 古い世代は削除され、トータル 2 件に切詰
    assert len(gz) == 2


def test_zero_threshold_skips(tmp_path: Path) -> None:
    log = tmp_path / "x.log"
    log.write_bytes(b"X" * 100)
    assert rotate_log_if_needed(log, threshold_bytes=0) is False
    assert log.read_bytes() == b"X" * 100


def test_missing_file_noop(tmp_path: Path) -> None:
    assert rotate_log_if_needed(tmp_path / "nope.log", threshold_bytes=1) is False
