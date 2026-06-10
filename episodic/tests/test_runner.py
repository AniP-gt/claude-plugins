"""session/runner.py の単体テスト。"""
from __future__ import annotations

import importlib
import json
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "session"))

from lib.codex_runner import CodexResult  # noqa: E402
from lib.notify import NullNotifier  # noqa: E402


@pytest.fixture
def runner_mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    sys.modules.pop("runner", None)
    mod = importlib.import_module("runner")
    # ログ先を tmp に置き換える
    importlib.reload(mod)
    mod.LOG_DIR_LOCAL = home / ".local" / "state" / "episodic" / "logs"
    mod.LOG_FILE = mod.LOG_DIR_LOCAL / "session-runner.log"
    return mod


class FakeRunner:
    def __init__(self, rc: int = 0, last: str = "", timed_out: bool = False) -> None:
        self.rc = rc
        self.last = last
        self.timed_out = timed_out
        self.runs: list[tuple[Path, Path, Path]] = []
        self.write_report: Path | None = None
        self.write_content: str = ""

    def run(self, input_path: Path, log_file: Path, capture_file: Path | None = None) -> CodexResult:
        self.runs.append((input_path, log_file, capture_file or Path()))
        if capture_file and self.last:
            capture_file.write_text(self.last)
        if self.write_report:
            self.write_report.write_text(self.write_content)
        return CodexResult(returncode=self.rc, timed_out=self.timed_out, last_message=self.last)


def _make_session_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    sid = str(uuid.uuid4())
    pending = tmp_path / ".local" / "state" / "episodic" / "pending" / sid
    pending.mkdir(parents=True)
    input_md = pending / "010203.codex.md"
    input_md.write_text("prompt")
    meta = pending / "010203.codex.meta.json"
    meta.write_text(json.dumps({
        "session_id": sid,
        "cwd": "/x",
        "transcript_path": "",
        "first_ts": "2026-05-19T01:02:03Z",
        "report_path": str(tmp_path / "mem" / "raw" / "session" / "2026-05-19" / "report.md"),
        "is_staged": False,
        "snapshot_path": "",
    }))
    return pending, input_md, meta


def test_skip_via_codex_skip(tmp_path: Path, runner_mod, monkeypatch) -> None:
    # HOME を pending root として使う
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    fake = FakeRunner(rc=0, last="SKIP: no real work")
    rc = runner_mod.run(input_md, report, "normal", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 0
    assert not report.exists()


def test_report_written_by_codex(tmp_path: Path, runner_mod, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    fake = FakeRunner(rc=0, last="")
    fake.write_report = report
    fake.write_content = "---\nproject: P\ntitle: T\n---\nbody\n"
    rc = runner_mod.run(input_md, report, "staged", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 0
    assert report.is_file()
    # report 内容（frontmatter キー）が保持されていることを検証
    front = runner_mod.fm.parse(report)
    assert front["project"] == "P"
    assert front["title"] == "T"
    text = report.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "body" in text


def test_last_message_fallback(tmp_path: Path, runner_mod, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    fake = FakeRunner(rc=0, last="---\nproject: P\n---\nbody\n")
    rc = runner_mod.run(input_md, report, "staged", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 0
    assert report.read_text().startswith("---")


@pytest.mark.parametrize(
    "log_seed, expected_reason",
    [
        ("[2026-05-19T00:00:00] error: you've hit your usage limit, try again later\n", "usage_limit"),
        ("[2026-05-19T00:00:00] error: unauthorized: invalid api key provided\n", "auth_failure"),
        ("[2026-05-19T00:00:00] error: something unexpected went wrong\n", "unknown"),
    ],
)
def test_codex_failure_retry_upsert(
    tmp_path: Path, runner_mod, monkeypatch, log_seed: str, expected_reason: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    # _classify_failure_reason は LOG_FILE 末尾 200 行を読むため、内容をシードして判定を固定する。
    # runner が後続で追記する行はいずれの分類パターンにも一致しないため、シード行が判定を決める。
    runner_mod.LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    runner_mod.LOG_FILE.write_text(log_seed, encoding="utf-8")
    fake = FakeRunner(rc=1, last="")  # timed_out=False → _classify_failure_reason 経路
    called: list = []
    monkeypatch.setattr(runner_mod, "_retry_queue_upsert", lambda meta, reason: called.append(reason))
    rc = runner_mod.run(input_md, report, "normal", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 1
    # 失敗ログ内容ごとに期待する reason が 1 つに特定される
    assert called == [expected_reason]


def test_codex_timeout(tmp_path: Path, runner_mod, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    fake = FakeRunner(rc=124, last="", timed_out=True)
    called: list = []
    monkeypatch.setattr(runner_mod, "_retry_queue_upsert", lambda meta, reason: called.append(reason))
    rc = runner_mod.run(input_md, report, "normal", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 1
    assert called == ["timeout"]


def test_twin_skip(tmp_path: Path, runner_mod, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    pending, input_md, meta = _make_session_dir(tmp_path)
    report = tmp_path / "report.md"
    twin = tmp_path / "twin.md"
    twin.write_text("existing")
    monkeypatch.setattr(runner_mod.pr, "twin_report_path", lambda p: twin)
    fake = FakeRunner(rc=0, last="")
    rc = runner_mod.run(input_md, report, "normal", meta, codex_runner=fake, notifier=NullNotifier())
    assert rc == 0
    assert fake.runs == []  # codex は呼ばれない


def test_enforce_supersedes_self_ref(tmp_path: Path, runner_mod) -> None:
    report = tmp_path / "r.md"
    report.write_text(f"---\nproject: P\nsupersedes: {report}\n---\nbody\n")
    runner_mod._enforce_supersedes_integrity(report)
    assert "supersedes: null" in report.read_text()


class _RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def notify(self, subtitle: str, message: str, sound: str | None = None) -> None:
        self.calls.append((subtitle, message, sound))


def test_notify_all_level_passes_everything(runner_mod, monkeypatch) -> None:
    monkeypatch.setattr(runner_mod.cfg, "resolve_notification_level", lambda: "all")
    n = _RecordingNotifier()
    runner_mod._notify(n, "完了", "ok", "Glass")
    runner_mod._notify(n, "失敗", "boom", "Basso")
    assert n.calls == [("完了", "ok", "Glass"), ("失敗", "boom", "Basso")]


def test_notify_failure_level_suppresses_success(runner_mod, monkeypatch) -> None:
    monkeypatch.setattr(runner_mod.cfg, "resolve_notification_level", lambda: "failure")
    n = _RecordingNotifier()
    runner_mod._notify(n, "完了", "ok", "Glass")
    runner_mod._notify(n, "スキップ", "skip")
    assert n.calls == []
    runner_mod._notify(n, "失敗", "boom", "Basso")
    assert n.calls == [("失敗", "boom", "Basso")]


def test_notify_none_level_suppresses_all(runner_mod, monkeypatch) -> None:
    monkeypatch.setattr(runner_mod.cfg, "resolve_notification_level", lambda: "none")
    n = _RecordingNotifier()
    runner_mod._notify(n, "完了", "ok", "Glass")
    runner_mod._notify(n, "失敗", "boom", "Basso")
    assert n.calls == []
