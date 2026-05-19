"""bin/session_start.py の単体テスト。"""
from __future__ import annotations

import importlib
import json
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sys.modules.pop("session_start", None)
    m = importlib.import_module("session_start")
    importlib.reload(m)
    return m


def test_main_calls_mount_then_sync(mod, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(mod, "_mount_attempt", lambda: calls.append("mount"))
    monkeypatch.setattr(mod, "_detect_pending_sessions", lambda: calls.append("detect"))
    monkeypatch.setattr(mod, "_sync_pending", lambda: calls.append("sync"))
    assert mod.main() == 0
    assert calls == ["mount", "detect", "sync"]


def test_failed_mount_continues(mod, monkeypatch) -> None:
    def raising():
        raise RuntimeError("boom")
    monkeypatch.setattr(mod, "_mount_attempt", raising)
    monkeypatch.setattr(mod, "_detect_pending_sessions", lambda: None)
    monkeypatch.setattr(mod, "_sync_pending", lambda: None)
    # main は失敗を捕えない設計なので 例外が伝播するか確認
    with pytest.raises(RuntimeError):
        mod.main()


def test_detect_pending_drops_when_report_exists(mod, tmp_path, monkeypatch) -> None:
    pending = tmp_path / ".local" / "state" / "episodic" / "pending"
    sid = str(uuid.uuid4())
    sd = pending / sid
    sd.mkdir(parents=True)
    report = tmp_path / "report.md"
    report.write_text("exists")
    meta = sd / "010203.codex.meta.json"
    meta.write_text(json.dumps({"report_path": str(report)}))
    # hook.py の存在を保証
    monkeypatch.setattr(mod, "BIN_DIR", REPO_ROOT / "bin")
    monkeypatch.setattr(mod, "LOG_DIR_LOCAL", tmp_path / "logs")
    mod._detect_pending_sessions()
    assert not sd.exists()
