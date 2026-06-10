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
    calls: list[tuple] = []

    def rec(name: str):
        def _f(*a, **k):
            calls.append((name, a, k))

        return _f

    monkeypatch.setattr(mod, "_mount_attempt", rec("mount"))
    monkeypatch.setattr(mod, "_detect_pending_sessions", rec("detect"))
    monkeypatch.setattr(mod, "_sync_pending", rec("sync"))
    assert mod.main() == 0
    # 厳密な呼び出し順
    names = [c[0] for c in calls]
    assert names == ["mount", "detect", "sync"]
    # 各段は 1 回だけ・位置/キーワード引数なしで呼ばれる
    assert all(a == () and k == {} for _, a, k in calls)
    assert names.count("mount") == 1
    assert names.count("detect") == 1
    assert names.count("sync") == 1
    # main は副作用として LOG_DIR_LOCAL を作成する
    assert mod.LOG_DIR_LOCAL.is_dir()


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
