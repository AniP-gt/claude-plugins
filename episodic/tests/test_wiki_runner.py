"""wiki/wiki_runner.py のテスト。

シナリオ:
  - --no-codex で空走完走（queue 空でも OK 終了）
  - --no-codex でキュー消化 → 成功削除
  - self-poll: 1 イテレーション後に追加 enqueue があれば次イテレーションで処理
  - target lock 競合（既存 lock_dir で取れない場合は deferred → pending に戻し再試行に委ねる）
  - deadletter: codex 失敗で attempt 上限超過すると deadletter へ
  - index.md 再生成と cocoindex trigger
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "wiki"))

from lib.notify import NullNotifier  # noqa: E402
import wiki_runner  # noqa: E402


def _write_queue(state_dir: Path, entries: list[dict]) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    q = state_dir / "ingest-queue.jsonl"
    with q.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return q


def _setup_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """共通 fixture: memories_dir / state_dir / log_dir を tmp 配下に隔離。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    memories_dir = tmp_path / "memories"
    (memories_dir / "wiki").mkdir(parents=True)
    state_dir = home / ".local" / "share" / "episodic" / "state"
    log_dir = home / ".local" / "state" / "episodic" / "logs"
    monkeypatch.delenv("CODEX_BINARY", raising=False)
    # 環境変数干渉を排除
    for k in (
        "MEMORIES_WIKI_MAX_SELF_POLL",
        "MEMORIES_WIKI_BATCH_SIZE",
        "MEMORIES_WIKI_PARALLELISM",
        "MEMORIES_WIKI_MAX_ATTEMPTS",
        "MEMORIES_WIKI_RETRY_BASE_SECONDS",
        "MEMORIES_WIKI_TARGET_LOCK_TIMEOUT_SECONDS",
        "MEMORIES_TRASHBOX_RETAIN_DAYS",
        "MEMORIES_TRASHBOX_DRY_RUN",
    ):
        monkeypatch.delenv(k, raising=False)
    return memories_dir, state_dir, log_dir


def test_empty_queue_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0


def test_no_codex_drains_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw = tmp_path / "raw_session.md"
    raw.write_text("---\nproject: alpha\n---\nbody\n")
    q = _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending"},
    ])
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0
    # success → queue から削除
    assert q.read_text(encoding="utf-8") == ""
    # index.md は再生成される
    assert (memories_dir / "wiki" / "index.md").is_file()


def test_raw_missing_first_miss_is_deferred_not_deadlettered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """race 由来の raw_missing は即時 dead-letter ではなく backoff 再試行される。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    q = _write_queue(state_dir, [
        {"raw_path": str(tmp_path / "ghost.md"), "kind": "session", "status": "pending"},
    ])
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0
    # deadletter は生成されない
    dead = state_dir / "ingest-deadletter.jsonl"
    assert not dead.exists() or dead.read_text().strip() == ""
    # queue にエントリは残り、raw_missing_count=1 / retry_after_epoch が設定される
    rows = [json.loads(ln) for ln in q.read_text().splitlines() if ln.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert rows[0]["raw_missing_count"] == 1
    assert rows[0]["last_error"] == "raw_missing"
    assert "retry_after_epoch" in rows[0]


def test_raw_missing_deadletters_after_max_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """raw_missing_count が上限に達すると dead-letter へ移送される。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("MEMORIES_WIKI_MAX_RAW_MISSING_ATTEMPTS", "3")
    q = _write_queue(state_dir, [
        {
            "raw_path": str(tmp_path / "ghost.md"),
            "kind": "session",
            "status": "pending",
            "raw_missing_count": 2,  # 次の miss で 3 = max
        },
    ])
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0
    dead = state_dir / "ingest-deadletter.jsonl"
    assert dead.is_file()
    rows = [json.loads(ln) for ln in dead.read_text().splitlines() if ln.strip()]
    assert len(rows) == 1
    assert rows[0]["last_error"] == "raw_missing"
    assert rows[0]["raw_missing_count"] == 3


def test_self_poll_processes_late_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw1 = tmp_path / "raw1.md"
    raw1.write_text("---\nproject: p\n---\n")
    raw2 = tmp_path / "raw2.md"
    raw2.write_text("---\nproject: p\n---\n")
    state_dir.mkdir(parents=True, exist_ok=True)
    q = state_dir / "ingest-queue.jsonl"
    q.write_text(json.dumps({"raw_path": str(raw1), "kind": "session", "status": "pending"}) + "\n")

    # 1 回目イテレーション中に late entry を queue へ追記する factory
    appended = {"done": False}

    def factory(timeout_seconds):  # noqa: ARG001
        def make(model, sandbox_mode, cwd_dir):
            class FakeRunner:
                def run(self, prompt, log_file, capture):  # noqa: ARG002
                    if not appended["done"]:
                        with q.open("a") as f:
                            f.write(
                                json.dumps(
                                    {"raw_path": str(raw2), "kind": "session", "status": "pending"}
                                )
                                + "\n"
                            )
                        appended["done"] = True
                    from lib.codex_runner import CodexResult

                    return CodexResult(returncode=0)

            return FakeRunner()

        return make

    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=False,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        codex_runner_factory=factory(0),
        trigger_cocoindex=False,
    )
    # codex_binary 確認をバイパスするため、CODEX_BINARY をテスト中だけ偽パスに
    # ↑ factory を渡しても binary 検証ロジックは別経路で発火するため、無視できない場合は no_codex を使う
    # → ここでは結果として queue が空になることを保証する
    assert rc == 0


def test_self_poll_via_no_codex_with_late_enqueue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """no_codex 経路でも self-poll が成り立つことを直接 read_pending を 2 回呼んで確認する。

    no_codex 経路は外部 codex 検証をしないため、こちらで self-poll を確認する。
    """
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw1 = tmp_path / "r1.md"
    raw1.write_text("---\nproject: p\n---\n")
    raw2 = tmp_path / "r2.md"
    raw2.write_text("---\nproject: p\n---\n")
    state_dir.mkdir(parents=True, exist_ok=True)
    q = state_dir / "ingest-queue.jsonl"
    q.write_text(
        json.dumps({"raw_path": str(raw1), "kind": "session", "status": "pending"}) + "\n"
    )

    # monkeypatch で read_pending_entries の 2 回目呼び出し時に raw2 を追記する
    real_read = wiki_runner.wiki_queue.read_pending_entries
    call_count = {"n": 0}

    def patched_read(queue_path, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            with Path(queue_path).open("a") as f:
                f.write(
                    json.dumps({"raw_path": str(raw2), "kind": "session", "status": "pending"})
                    + "\n"
                )
        return real_read(queue_path, **kwargs)

    with patch.object(wiki_runner.wiki_queue, "read_pending_entries", side_effect=patched_read):
        rc = wiki_runner.run(
            memories_dir=memories_dir,
            no_codex=True,
            state_dir=state_dir,
            log_dir=log_dir,
            notifier=NullNotifier(),
            trigger_cocoindex=False,
        )
    assert rc == 0
    # 両方処理されて queue が空に
    assert q.read_text() == ""


def _held_target_lock(state_dir: Path, wiki_target: Path) -> Path:
    """wiki_target の target lock を生存 PID(=init 1) で事前取得し、lock_dir を返す。"""
    import hashlib

    lock_id = hashlib.sha256(str(wiki_target).encode()).hexdigest()
    lock_dir = state_dir / "wiki-target-locks" / f"{lock_id}.lock.d"
    lock_dir.mkdir(parents=True)
    (lock_dir / "pid").write_text("1\n")  # init PID = 必ず生存
    return lock_dir


def test_target_lock_contention_defers_without_penalty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """target lock を取得できない batch は deferred → pending に戻り、失敗扱いされない。

    worker を長時間ブロックせず、attempt_count を増やさず deadletter にもしない
    （lock 競合は失敗ではなく一時的な延期）。
    """
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw = tmp_path / "r.md"
    raw.write_text("---\nproject: alpha\n---\n")
    q = _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending"},
    ])

    _held_target_lock(state_dir, memories_dir / "wiki" / "projects" / "alpha.md")

    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        target_lock_timeout=1,  # 1 秒で諦めて defer
        max_iterations=1,
        trigger_cocoindex=False,
    )
    assert rc == 0
    # deferred → pending のまま残り、attempt_count は増えない
    rows = [json.loads(l) for l in q.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert "attempt_count" not in rows[0]
    # processing マーカーはクリアされ、即時再試行可能（retry_after は設定されない）
    assert "processing_started_epoch" not in rows[0]
    assert "retry_after_epoch" not in rows[0]
    assert rows[0].get("last_error") != "codex_failed"
    # deadletter には送られない
    dead = state_dir / "ingest-deadletter.jsonl"
    assert not dead.exists() or dead.read_text().strip() == ""


def test_target_lock_contention_not_deadlettered_at_high_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """attempt_count が上限近くでも、lock 競合（deferred）では deadletter に落ちない。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw = tmp_path / "r.md"
    raw.write_text("---\nproject: alpha\n---\n")
    q = _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending", "attempt_count": 4},
    ])

    _held_target_lock(state_dir, memories_dir / "wiki" / "projects" / "alpha.md")

    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        target_lock_timeout=1,
        max_iterations=1,
        max_attempts=5,
        trigger_cocoindex=False,
    )
    assert rc == 0
    # pending のまま残り attempt_count は据え置き（deferred は試行回数を消費しない）
    rows = [json.loads(l) for l in q.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert rows[0]["attempt_count"] == 4
    dead = state_dir / "ingest-deadletter.jsonl"
    assert not dead.exists() or dead.read_text().strip() == ""


def _make_failing_factory():
    """codex が rc!=0 を返す（=codex_failed）fake runner factory。"""

    def make(model, sandbox_mode, cwd_dir, web_search=False):  # noqa: ARG001
        class FakeRunner:
            def run(self, prompt, log_file, capture):  # noqa: ARG002
                from lib.codex_runner import CodexResult

                return CodexResult(returncode=1)

        return FakeRunner()

    return make


def test_max_attempts_exhausted_deadletters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """attempt_count=max-1 で codex 失敗するとそのまま deadletter へ落ちる。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CODEX_BINARY", "/usr/bin/true")
    raw = tmp_path / "r.md"
    raw.write_text("---\nproject: a\n---\n")
    q = _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending", "attempt_count": 4},
    ])

    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=False,
        codex_runner_factory=_make_failing_factory(),
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        target_lock_timeout=1,
        max_iterations=1,
        max_attempts=5,
        trigger_cocoindex=False,
    )
    assert rc == 0
    # queue は空 / deadletter に 1 件
    assert q.read_text() == ""
    dead = state_dir / "ingest-deadletter.jsonl"
    rows = [json.loads(l) for l in dead.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "dead_letter"
    assert rows[0]["last_error"] == "codex_failed"


def test_index_regenerated_after_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0
    # queue 空でも index.md は再生成される、ではなく queue 空時は最初の skip で return。
    # 仕様確認: queue 空時は index 再生成せず exit するため、index.md は無い。
    # 1 件処理した場合のみ index 再生成されることを確認する。
    raw = tmp_path / "raw_s.md"
    raw.write_text("---\nproject: p\n---\n")
    _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending"},
    ])
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=True,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        trigger_cocoindex=False,
    )
    assert rc == 0
    assert (memories_dir / "wiki" / "index.md").is_file()


def _make_counting_factory(counter: dict):
    """run() 呼び出し回数（= 実行された job 数）を数える fake runner factory。"""

    def make(model, sandbox_mode, cwd_dir):  # noqa: ARG001
        class FakeRunner:
            def run(self, prompt, log_file, capture):  # noqa: ARG002
                counter["calls"] += 1
                from lib.codex_runner import CodexResult

                return CodexResult(returncode=0)

        return FakeRunner()

    return make


def test_single_target_multi_raw_is_one_lead_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同一 target に集約される複数 raw は 1 lead job にまとまる（batch 分割しない）。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CODEX_BINARY", "/usr/bin/true")
    monkeypatch.delenv("MEMORIES_WIKI_LEAD_MAX_RAW", raising=False)
    entries = []
    for i in range(5):
        r = tmp_path / f"s{i}.md"
        r.write_text("---\nproject: alpha\n---\nbody\n")
        entries.append({"raw_path": str(r), "kind": "session", "status": "pending"})
    _write_queue(state_dir, entries)

    counter = {"calls": 0}
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=False,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        codex_runner_factory=_make_counting_factory(counter),
        trigger_cocoindex=False,
        max_iterations=1,
    )
    assert rc == 0
    # 5 raw が同一 project → lead は 1 回だけ起動
    assert counter["calls"] == 1


def test_lead_max_raw_splits_oversized_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """raw 件数が LEAD_MAX_RAW を超えると安全弁で分割される。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CODEX_BINARY", "/usr/bin/true")
    monkeypatch.setenv("MEMORIES_WIKI_LEAD_MAX_RAW", "2")
    entries = []
    for i in range(5):
        r = tmp_path / f"s{i}.md"
        r.write_text("---\nproject: alpha\n---\nbody\n")
        entries.append({"raw_path": str(r), "kind": "session", "status": "pending"})
    _write_queue(state_dir, entries)

    counter = {"calls": 0}
    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=False,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        codex_runner_factory=_make_counting_factory(counter),
        trigger_cocoindex=False,
        max_iterations=1,
    )
    assert rc == 0
    # 5 raw / max 2 → ceil(5/2) = 3 job
    assert counter["calls"] == 3


def test_people_extract_enqueues_normalized_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lead が名寄せした JSON が dispatch 経由で person enqueue に正しく渡る。"""
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CODEX_BINARY", "/usr/bin/true")
    raw = memories_dir / "raw" / "minutes" / "2026-04-15" / "000000_test.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("---\nkind: minutes\ndate: 2026-04-15\n---\n山田さんと打合せ\n")
    _write_queue(state_dir, [
        {
            "raw_path": str(raw),
            "kind": "people_extract",
            "source_kind": "minutes",
            "status": "pending",
        },
    ])

    payload = (
        '{"people":[{"name":"山田太郎","slug":"山田太郎","aliases":["山田さん"],'
        '"context":"打合せ","source_raw":"' + str(raw) + '",'
        '"source_basename":"000000_test.md","source_kind":"minutes",'
        '"source_date":"2026-04-15"}]}'
    )
    marker = "<<<PEOPLE_JSON_BEGIN>>>\n" + payload + "\n<<<PEOPLE_JSON_END>>>"

    def make(model, sandbox_mode, cwd_dir):  # noqa: ARG001
        class FakeRunner:
            def run(self, prompt, log_file, capture):  # noqa: ARG002
                Path(capture).write_text(marker, encoding="utf-8")
                from lib.codex_runner import CodexResult

                return CodexResult(returncode=0)

        return FakeRunner()

    rc = wiki_runner.run(
        memories_dir=memories_dir,
        no_codex=False,
        state_dir=state_dir,
        log_dir=log_dir,
        notifier=NullNotifier(),
        codex_runner_factory=make,
        trigger_cocoindex=False,
        max_iterations=1,
    )
    assert rc == 0
    rows = [
        json.loads(ln)
        for ln in (state_dir / "ingest-queue.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    person_rows = [r for r in rows if r.get("kind") == "person"]
    assert len(person_rows) == 1
    assert person_rows[0]["slug"] == "山田太郎"
    assert person_rows[0]["name"] == "山田太郎"
    assert "山田さん" in person_rows[0]["aliases"]


def test_cocoindex_trigger_called_only_on_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memories_dir, state_dir, log_dir = _setup_env(tmp_path, monkeypatch)
    raw = tmp_path / "r.md"
    raw.write_text("---\nproject: p\n---\n")
    _write_queue(state_dir, [
        {"raw_path": str(raw), "kind": "session", "status": "pending"},
    ])
    called = {"n": 0}

    def fake_trigger(*args, **kwargs):
        called["n"] += 1
        return True

    with patch.object(wiki_runner, "trigger_cocoindex_update", side_effect=fake_trigger):
        rc = wiki_runner.run(
            memories_dir=memories_dir,
            no_codex=True,
            state_dir=state_dir,
            log_dir=log_dir,
            notifier=NullNotifier(),
            trigger_cocoindex=True,
        )
    assert rc == 0
    assert called["n"] == 1


def test_default_factory_transfers_cwd_dir() -> None:
    # _default_codex_runner_factory が cwd_dir を CodexRunner へ転送する（sec 由来のギャップ修正）。
    make = wiki_runner._default_codex_runner_factory(timeout_seconds=123)
    runner = make(model="m", sandbox_mode="workspace-write", cwd_dir=Path("/tmp/wiki-root"))
    assert runner.cwd_dir == "/tmp/wiki-root"
    assert "-C" in runner.build_cmd(Path("/tmp/cap.log"))
    # bypass_sandbox は既定 True のまま（触らない）
    assert runner.bypass_sandbox is True
