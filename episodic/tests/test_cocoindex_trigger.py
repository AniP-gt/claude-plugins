"""lib/cocoindex_trigger.py の単体テスト。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import cocoindex_trigger as ct  # noqa: E402


def test_skip_when_main_episodic_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "plugin"
    fake_root.mkdir()
    (fake_root / "pyproject.toml").write_text("")
    monkeypatch.setattr(ct, "plugin_root", lambda: fake_root)
    monkeypatch.setattr(ct.shutil, "which", lambda n: "/usr/bin/uv")
    called: list = []
    monkeypatch.setattr(ct.subprocess, "Popen", lambda *a, **k: called.append((a, k)))
    assert ct.trigger_cocoindex_update(memories_dir="/m", log_dir=tmp_path / "logs") is False
    assert called == []


def test_skip_when_uv_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "plugin"
    (fake_root / "recording").mkdir(parents=True)
    (fake_root / "recording" / "main_episodic.py").write_text("")
    (fake_root / "pyproject.toml").write_text("")
    monkeypatch.setattr(ct, "plugin_root", lambda: fake_root)
    monkeypatch.setattr(ct.shutil, "which", lambda n: None)
    assert ct.trigger_cocoindex_update(log_dir=tmp_path / "logs") is False


def test_popen_invoked_with_expected_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "plugin"
    (fake_root / "recording").mkdir(parents=True)
    main = fake_root / "recording" / "main_episodic.py"
    main.write_text("")
    (fake_root / "pyproject.toml").write_text("")
    monkeypatch.setattr(ct, "plugin_root", lambda: fake_root)
    monkeypatch.setattr(ct.shutil, "which", lambda n: "/usr/bin/uv")
    captured = {}

    class _FakePopen:
        def __init__(self, args, **kw):
            captured["args"] = args
            captured["kw"] = kw

    monkeypatch.setattr(ct.subprocess, "Popen", _FakePopen)
    assert ct.trigger_cocoindex_update(memories_dir="/mem", log_dir=tmp_path / "logs") is True
    assert captured["args"][:5] == ["uv", "run", "cocoindex", "update", "-f"]
    spec = captured["args"][5]
    assert spec.startswith(str(main))
    assert spec.endswith("_episodic")
    assert captured["kw"]["start_new_session"] is True
    assert captured["kw"]["env"]["SOURCE_PATH"] == "/mem"
    assert captured["kw"]["env"]["INDEX_NAME"] == "episodic"


def test_popen_failure_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "plugin"
    (fake_root / "recording").mkdir(parents=True)
    (fake_root / "recording" / "main_episodic.py").write_text("")
    (fake_root / "pyproject.toml").write_text("")
    monkeypatch.setattr(ct, "plugin_root", lambda: fake_root)
    monkeypatch.setattr(ct.shutil, "which", lambda n: "/usr/bin/uv")

    def _raise(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr(ct.subprocess, "Popen", _raise)
    assert ct.trigger_cocoindex_update(log_dir=tmp_path / "logs") is False
