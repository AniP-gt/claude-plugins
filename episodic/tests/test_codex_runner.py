"""lib/codex_runner.py の単体テスト。

CODEX_BIN を `/usr/bin/true` / `/usr/bin/false` / `/bin/sleep` に差し替えて経路検証。
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.codex_runner import CodexRunner  # noqa: E402


@pytest.fixture
def safe_bin(tmp_path: Path) -> Path:
    """world-writable でない bin ディレクトリを作る。"""
    d = tmp_path / "safe_bin"
    d.mkdir()
    os.chmod(d, 0o755)
    return d


def _make_exec(path: Path, body: str) -> Path:
    path.write_text(f"#!/bin/sh\n{body}\n")
    os.chmod(path, 0o755)
    return path


def test_run_success(tmp_path: Path, safe_bin: Path) -> None:
    fake = _make_exec(safe_bin / "codex", 'cat "$11" >/dev/null; exit 0')
    # capture_file へ何か書き出すフェイク
    capture = tmp_path / "capture.txt"
    capture.write_text("hello")
    input_md = tmp_path / "in.md"
    input_md.write_text("prompt")
    log_file = tmp_path / "log.log"
    runner = CodexRunner(model="m", effort="low", timeout_seconds=10, codex_bin=str(fake))
    result = runner.run(input_md, log_file, capture)
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.last_message == "hello"


def test_run_failure_rc(tmp_path: Path, safe_bin: Path) -> None:
    fake = _make_exec(safe_bin / "codex", "exit 7")
    runner = CodexRunner(model="m", effort="low", codex_bin=str(fake), timeout_seconds=10)
    input_md = tmp_path / "in.md"
    input_md.write_text("p")
    result = runner.run(input_md, tmp_path / "log.log", tmp_path / "cap.txt")
    assert result.returncode == 7
    assert result.timed_out is False


def test_timeout_path(tmp_path: Path, safe_bin: Path) -> None:
    fake = _make_exec(safe_bin / "codex", "sleep 30")
    runner = CodexRunner(model="m", effort="low", codex_bin=str(fake), timeout_seconds=1)
    input_md = tmp_path / "in.md"
    input_md.write_text("p")
    log = tmp_path / "log.log"
    result = runner.run(input_md, log, tmp_path / "cap.txt")
    assert result.timed_out is True
    assert result.returncode == 124
    log_text = log.read_text()
    assert "timeout" in log_text


def test_codex_binary_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_BINARY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    runner = CodexRunner(model="m", effort="low", codex_bin=None)
    with pytest.raises(FileNotFoundError):
        runner.run(tmp_path / "in.md", tmp_path / "log.log")


def test_reject_world_writable_dir(tmp_path: Path) -> None:
    bad_dir = tmp_path / "world_writable"
    bad_dir.mkdir()
    os.chmod(bad_dir, 0o777)
    fake = _make_exec(bad_dir / "codex", "exit 0")
    runner = CodexRunner(model="m", effort="low", codex_bin=str(fake))
    input_md = tmp_path / "in.md"
    input_md.write_text("p")
    with pytest.raises(PermissionError):
        runner.run(input_md, tmp_path / "log.log", tmp_path / "cap.txt")


def test_build_cmd_includes_required_flags(tmp_path: Path, safe_bin: Path) -> None:
    fake = _make_exec(safe_bin / "codex", "exit 0")
    runner = CodexRunner(model="gpt-x", effort="low", codex_bin=str(fake))
    cmd = runner.build_cmd(tmp_path / "cap.txt")
    assert "--disable" in cmd and "hooks" in cmd
    assert "--ignore-user-config" in cmd
    assert "--ephemeral" in cmd
    assert "--sandbox" in cmd and "workspace-write" in cmd
    assert "model_reasoning_effort=low" in cmd
    assert "-m" in cmd and "gpt-x" in cmd
    assert "-o" in cmd
