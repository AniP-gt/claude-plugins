"""lib/notify.py の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import notify as notify_mod  # noqa: E402

# conftest の autouse ガードが OsascriptNotifier.notify を no-op 化するため、
# notify 実装そのものを検証するテストでは collection 時に捕捉した元実装を復元する。
_ORIG_NOTIFY = notify_mod.OsascriptNotifier.notify


@pytest.fixture
def real_notify(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(notify_mod.OsascriptNotifier, "notify", _ORIG_NOTIFY)


def test_escape_quotes_and_newlines() -> None:
    assert notify_mod._escape_for_osascript('a"b') == 'a\\"b'
    assert notify_mod._escape_for_osascript("a\\b") == "a\\\\b"
    assert notify_mod._escape_for_osascript("a\nb\rc") == "a b c"


def test_osascript_present_invokes(real_notify, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_which(name: str) -> str | None:
        return "/usr/bin/osascript" if name == "osascript" else None

    def fake_run(args, **kwargs):
        calls.append(args)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(notify_mod.shutil, "which", fake_which)
    monkeypatch.setattr(notify_mod.subprocess, "run", fake_run)
    n = notify_mod.OsascriptNotifier(title="T")
    n.notify("sub", "msg", sound="Glass")
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[0] == "osascript"
    assert cmd[1] == "-e"
    assert 'subtitle "sub"' in cmd[2]
    assert 'sound name "Glass"' in cmd[2]


def test_osascript_absent_skips(real_notify, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notify_mod.shutil, "which", lambda name: None)
    called = []
    monkeypatch.setattr(notify_mod.subprocess, "run", lambda *a, **k: called.append(a))
    n = notify_mod.OsascriptNotifier()
    n.notify("sub", "msg")
    assert called == []


def test_default_notifier_falls_back_when_no_osascript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notify_mod.shutil, "which", lambda name: None)
    n = notify_mod.default_notifier()
    assert isinstance(n, notify_mod.NullNotifier)


def test_sound_optional_omitted(real_notify, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(notify_mod.shutil, "which", lambda name: "/usr/bin/osascript")

    def fake_run(args, **kwargs):
        calls.append(args)
        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(notify_mod.subprocess, "run", fake_run)
    notify_mod.OsascriptNotifier().notify("sub", "msg")
    assert "sound name" not in calls[0][2]
