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


# --- MEMORIES_RETRY_MAX_PER_RUN: 1 回の実行で spawn する件数の上限 ---


def _spawnable_entry(tmp_path: Path, idx: int) -> tuple[str, str]:
    """spawn 経路に到達する有効エントリ（transcript 実在・report なし・attempt < max）。"""
    sid = str(uuid.uuid4())
    transcript = tmp_path / f"t{idx}.jsonl"
    transcript.write_text("a")
    payload = json.dumps({
        "session_id": sid,
        "cwd": "/x",
        "transcript_path": str(transcript),
        "report_path": "",
        "attempt_count": 0,
    })
    return sid, payload


def _make_fake_run(list_output: str, calls: list):
    def fake_run(args, **kw):
        calls.append(args)

        class _R:
            stdout = list_output if "list" in args else ""
            returncode = 0

        return _R()

    return fake_run


def _spawn_count(calls: list, mod) -> int:
    return sum(1 for a in calls if isinstance(a, list) and str(mod.HOOK_PY) in a)


def test_within_limit_all_spawned(mod, monkeypatch, tmp_path) -> None:
    entries = [_spawnable_entry(tmp_path, i) for i in range(3)]
    list_output = "\n".join(p for _, p in entries)
    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_fake_run(list_output, calls))
    monkeypatch.delenv("MEMORIES_RETRY_MAX_PER_RUN", raising=False)  # 既定 3
    mod.run(notifier=NullNotifier())
    # 件数が上限内なら全件 spawn される
    assert _spawn_count(calls, mod) == 3


def test_over_limit_excess_left_in_queue(mod, monkeypatch, tmp_path) -> None:
    entries = [_spawnable_entry(tmp_path, i) for i in range(5)]
    list_output = "\n".join(p for _, p in entries)
    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_fake_run(list_output, calls))
    monkeypatch.setenv("MEMORIES_RETRY_MAX_PER_RUN", "2")
    mod.run(notifier=NullNotifier())
    # 上限の 2 件だけ spawn
    assert _spawn_count(calls, mod) == 2
    # 残り 3 件は remove / dead-letter されずキューに残る
    assert all(
        "remove" not in a and "promote-dead-letter" not in a
        for a in calls
        if isinstance(a, list)
    )


def test_env_override_raises_limit(mod, monkeypatch, tmp_path) -> None:
    entries = [_spawnable_entry(tmp_path, i) for i in range(5)]
    list_output = "\n".join(p for _, p in entries)
    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_fake_run(list_output, calls))
    monkeypatch.setenv("MEMORIES_RETRY_MAX_PER_RUN", "5")
    mod.run(notifier=NullNotifier())
    assert _spawn_count(calls, mod) == 5


def test_invalid_env_falls_back_to_default(mod, monkeypatch, tmp_path) -> None:
    entries = [_spawnable_entry(tmp_path, i) for i in range(5)]
    list_output = "\n".join(p for _, p in entries)
    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_fake_run(list_output, calls))
    monkeypatch.setenv("MEMORIES_RETRY_MAX_PER_RUN", "not-a-number")
    mod.run(notifier=NullNotifier())
    # 不正値は既定 3 にフォールバック
    assert _spawn_count(calls, mod) == 3


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", 1),
        ("3", 3),
        ("20", 20),
        ("0", 3),       # 範囲外（下限未満）
        ("21", 3),      # 範囲外（上限超過）
        ("999", 3),     # 範囲外
        ("-1", 3),      # 非数値（isdigit False）
        ("3.5", 3),     # 非数値
        ("abc", 3),     # 非数値
        ("", 3),        # 空文字
    ],
)
def test_max_per_run_validation(mod, monkeypatch, value, expected) -> None:
    monkeypatch.setenv("MEMORIES_RETRY_MAX_PER_RUN", value)
    assert mod._max_per_run() == expected


def test_max_per_run_default_when_unset(mod, monkeypatch) -> None:
    monkeypatch.delenv("MEMORIES_RETRY_MAX_PER_RUN", raising=False)
    assert mod._max_per_run() == 3
