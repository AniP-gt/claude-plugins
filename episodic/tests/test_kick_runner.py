"""wiki/kick_runner.py の単体テスト（detach 経路は除き、判定関数中心）。"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "wiki"))


@pytest.fixture
def kick_mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sys.modules.pop("kick_runner", None)
    mod = importlib.import_module("kick_runner")
    importlib.reload(mod)
    return mod


def test_queue_empty(tmp_path: Path, kick_mod) -> None:
    q = tmp_path / "q.jsonl"
    assert kick_mod.queue_has_ready_work(q) is False


def test_queue_pending_ready(tmp_path: Path, kick_mod) -> None:
    q = tmp_path / "q.jsonl"
    q.write_text(json.dumps({"status": "pending", "retry_after_epoch": 0}) + "\n")
    assert kick_mod.queue_has_ready_work(q) is True


def test_queue_pending_not_ready(tmp_path: Path, kick_mod) -> None:
    q = tmp_path / "q.jsonl"
    future = time.time() + 3600
    q.write_text(json.dumps({"status": "pending", "retry_after_epoch": future}) + "\n")
    assert kick_mod.queue_has_ready_work(q) is False


def test_queue_processing_timed_out(tmp_path: Path, kick_mod) -> None:
    q = tmp_path / "q.jsonl"
    past = time.time() - 7200
    q.write_text(json.dumps({"status": "processing", "processing_started_epoch": past}) + "\n")
    assert kick_mod.queue_has_ready_work(q) is True


def test_runner_active_check_no_lock_dir(kick_mod, monkeypatch) -> None:
    monkeypatch.setattr(kick_mod, "RUNNER_LOCK_DIR", Path("/nonexistent/path"))
    assert kick_mod.is_runner_active() is False


def test_double_acquire_kick_lock(tmp_path: Path, kick_mod, monkeypatch) -> None:
    monkeypatch.setattr(kick_mod, "KICK_LOCK_DIR", tmp_path / "kick.d")
    assert kick_mod._try_acquire_kick_lock() is True
    # 2 回目は失敗（既存のため）
    assert kick_mod._try_acquire_kick_lock() is False
