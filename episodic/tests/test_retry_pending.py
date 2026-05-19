"""session/retry_pending.py の単体テスト。"""
from __future__ import annotations

import importlib
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "session"))

from lib.notify import NullNotifier  # noqa: E402


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sys.modules.pop("retry_pending", None)
    m = importlib.import_module("retry_pending")
    importlib.reload(m)
    return m


def test_empty_queue(mod, monkeypatch) -> None:
    class FakeResult:
        stdout = ""
        returncode = 0

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: FakeResult())
    rc = mod.run(notifier=NullNotifier())
    assert rc == 0


def test_drop_when_report_exists(mod, monkeypatch, tmp_path) -> None:
    sid = str(uuid.uuid4())
    report = tmp_path / "report.md"
    report.write_text("existed")
    entry = json.dumps({
        "session_id": sid,
        "cwd": "/x",
        "transcript_path": str(tmp_path / "t.jsonl"),
        "report_path": str(report),
        "attempt_count": 0,
    })
    calls: list = []

    def fake_run(args, **kw):
        calls.append(args)

        class _R:
            stdout = entry if "list" in args else ""
            returncode = 0

        return _R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.run(notifier=NullNotifier())
    # remove が呼ばれていることを確認
    assert any("remove" in a for a in calls)


def test_dead_letter_promotion(mod, monkeypatch, tmp_path) -> None:
    sid = str(uuid.uuid4())
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("a")
    entry = json.dumps({
        "session_id": sid,
        "cwd": "/x",
        "transcript_path": str(transcript),
        "report_path": "",
        "attempt_count": 99,
    })
    calls: list = []

    def fake_run(args, **kw):
        calls.append(args)

        class _R:
            stdout = entry if "list" in args else ""
            returncode = 0

        return _R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("MEMORIES_RETRY_MAX_ATTEMPTS", "5")
    notifier = MagicMock()
    notifier.notify = MagicMock()
    mod.run(notifier=notifier)
    assert any("promote-dead-letter" in a for a in calls)
    notifier.notify.assert_called_once()


def test_invalid_session_id_skipped(mod, monkeypatch, tmp_path) -> None:
    entry = json.dumps({
        "session_id": "not-uuid",
        "cwd": "/x",
        "transcript_path": str(tmp_path / "t.jsonl"),
        "report_path": "",
        "attempt_count": 0,
    })
    calls: list = []

    def fake_run(args, **kw):
        calls.append(args)

        class _R:
            stdout = entry if "list" in args else ""
            returncode = 0

        return _R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.run(notifier=NullNotifier())
    # remove や hook 呼び出しは行われない（list のみ）
    assert all("remove" not in a and "promote-dead-letter" not in a for a in calls if isinstance(a, list))
