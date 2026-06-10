"""lib/wiki_queue.py の単体テスト。

4 関数 × 3 経路をカバー:
  - purge_missing_entries: 不在 raw を backoff 再試行 / 上限到達で dead-letter / 存在 raw は残す / 空 queue
  - read_pending_entries:  retry_after_epoch 未来は除外 / processing timeout / dedupe
  - mark_processing:       指定 identity を processing 化 / 非該当はそのまま / 空 identity
  - update_queue_after_results: 成功削除 / 失敗→retry / max超過→deadletter (+ missing→retry / missing max→dead)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_queue  # noqa: E402


def _write_queue(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _read_queue(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------- purge_missing_entries


class TestPurgeMissingEntries:
    def test_missing_raw_deferred_on_first_miss(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": str(tmp_path / "missing.md"), "kind": "session", "status": "pending"},
        ])
        deferred, dead = wiki_queue.purge_missing_entries(
            q, max_raw_missing_attempts=5, retry_base_seconds=60
        )
        assert deferred == 1
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["raw_missing_count"] == 1
        assert rows[0]["last_error"] == "raw_missing"
        assert "retry_after_epoch" in rows[0]
        assert not (tmp_path / "ingest-deadletter.jsonl").exists()

    def test_missing_raw_deadletters_at_max(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {
                "raw_path": str(tmp_path / "missing.md"),
                "kind": "session",
                "status": "pending",
                "raw_missing_count": 4,  # 次で 5 = max
            },
        ])
        deferred, dead = wiki_queue.purge_missing_entries(
            q, max_raw_missing_attempts=5, retry_base_seconds=60
        )
        assert deferred == 0
        assert dead == 1
        assert _read_queue(q) == []
        dead_rows = _read_queue(tmp_path / "ingest-deadletter.jsonl")
        assert len(dead_rows) == 1
        assert dead_rows[0]["status"] == "dead_letter"
        assert dead_rows[0]["last_error"] == "raw_missing"
        assert dead_rows[0]["raw_missing_count"] == 5

    def test_existing_raw_kept(self, tmp_path: Path) -> None:
        raw = tmp_path / "raw.md"
        raw.write_text("body")
        q = tmp_path / "q.jsonl"
        _write_queue(q, [{"raw_path": str(raw), "kind": "session", "status": "pending"}])
        deferred, dead = wiki_queue.purge_missing_entries(q)
        assert deferred == 0
        assert dead == 0
        assert len(_read_queue(q)) == 1

    def test_empty_queue_no_action(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        # 存在しない場合
        deferred, dead = wiki_queue.purge_missing_entries(q)
        assert deferred == 0
        assert dead == 0
        # 空ファイル
        q.write_text("")
        deferred, dead = wiki_queue.purge_missing_entries(q)
        assert deferred == 0
        assert dead == 0

    def test_corrupt_json_line_skipped_others_processed(self, tmp_path: Path) -> None:
        # 破損 JSON 行（lib/wiki_queue.py:95-96 の JSONDecodeError 経路）は読み飛ばされ、
        # クラッシュせずに正常エントリの処理が継続される。破損行は queue に原文保全される。
        q = tmp_path / "q.jsonl"
        valid = json.dumps({"raw_path": str(tmp_path / "missing.md"), "kind": "session", "status": "pending"})
        q.write_text("{ this is broken json\n" + valid + "\n", encoding="utf-8")
        deferred, dead = wiki_queue.purge_missing_entries(
            q, max_raw_missing_attempts=5, retry_base_seconds=60
        )
        assert deferred == 1  # 正常な missing エントリは defer される
        assert dead == 0
        lines = [ln for ln in q.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # 破損行は原文のまま保全される
        assert "{ this is broken json" in lines
        # JSON として読めるのは正常エントリ 1 件のみで、処理済み（raw_missing_count 加算）
        parsed = []
        for ln in lines:
            try:
                parsed.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
        assert len(parsed) == 1
        assert parsed[0]["raw_missing_count"] == 1
        assert parsed[0]["status"] == "pending"


# ---------------------------------------------------------------- read_pending_entries


class TestReadPendingEntries:
    def test_pending_returned(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "pending"},
            {"raw_path": "/b.md", "kind": "web", "status": "pending"},
        ])
        out = wiki_queue.read_pending_entries(q)
        assert len(out) == 2

    def test_future_retry_excluded(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        future = time.time() + 3600
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "pending"},
            {"raw_path": "/b.md", "kind": "session", "status": "pending", "retry_after_epoch": future},
        ])
        out = wiki_queue.read_pending_entries(q)
        assert len(out) == 1
        assert out[0]["raw_path"] == "/a.md"

    def test_corrupt_json_line_skipped(self, tmp_path: Path) -> None:
        # 破損 JSON 行は読み飛ばされ、正常エントリのみ返る（クラッシュしない）
        q = tmp_path / "q.jsonl"
        valid = json.dumps({"raw_path": "/a.md", "kind": "session", "status": "pending"})
        q.write_text("not json at all\n" + valid + "\n", encoding="utf-8")
        out = wiki_queue.read_pending_entries(q)
        assert len(out) == 1
        assert out[0]["raw_path"] == "/a.md"

    def test_processing_dedupe_and_timeout(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        recent = time.time() - 10
        old = time.time() - 7200
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "processing", "processing_started_epoch": recent},
            {"raw_path": "/b.md", "kind": "session", "status": "processing", "processing_started_epoch": old},
            # dedupe: 同一 (raw_path, kind, slug=)
            {"raw_path": "/b.md", "kind": "session", "status": "pending"},
            # person で slug 違いは別エントリ
            {"raw_path": "/c.md", "kind": "person", "slug": "x", "status": "pending"},
            {"raw_path": "/c.md", "kind": "person", "slug": "y", "status": "pending"},
        ])
        out = wiki_queue.read_pending_entries(q, processing_timeout_seconds=3600)
        raws = [(e["raw_path"], e.get("slug", "")) for e in out]
        # /a は processing 直前なので除外、/b は timeout 超過 1 回のみ、/c は slug 2 種
        assert ("/a.md", "") not in raws
        assert raws.count(("/b.md", "")) == 1
        assert ("/c.md", "x") in raws
        assert ("/c.md", "y") in raws


# ---------------------------------------------------------------- mark_processing


class TestMarkProcessing:
    def test_target_marked_processing(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "pending"},
            {"raw_path": "/b.md", "kind": "session", "status": "pending"},
        ])
        updated = wiki_queue.mark_processing(q, [("/a.md", "session", "")])
        assert updated == 1
        rows = _read_queue(q)
        a = next(r for r in rows if r["raw_path"] == "/a.md")
        b = next(r for r in rows if r["raw_path"] == "/b.md")
        assert a["status"] == "processing"
        assert "processing_started_epoch" in a
        assert b["status"] == "pending"

    def test_non_matching_left_alone(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [{"raw_path": "/a.md", "kind": "session", "status": "pending"}])
        updated = wiki_queue.mark_processing(q, [("/x.md", "session", "")])
        assert updated == 0

    def test_empty_identities(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [{"raw_path": "/a.md", "kind": "session", "status": "pending"}])
        updated = wiki_queue.mark_processing(q, [])
        assert updated == 0


# ---------------------------------------------------------------- update_queue_after_results


class TestUpdateQueueAfterResults:
    def test_success_deletes(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "processing"},
            {"raw_path": "/b.md", "kind": "session", "status": "pending"},
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "success", "label": "p1", "raw_path": "/a.md", "kind": "session", "slug": ""}],
            max_attempts=5,
        )
        assert deleted == 1
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1 and rows[0]["raw_path"] == "/b.md"

    def test_failed_schedules_retry(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [{"raw_path": "/a.md", "kind": "session", "status": "processing"}])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "failed", "label": "p1", "raw_path": "/a.md", "kind": "session", "slug": ""}],
            max_attempts=5,
            retry_base_seconds=100,
        )
        assert deleted == 0
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["attempt_count"] == 1
        assert rows[0]["last_error"] == "codex_failed"
        assert "retry_after_epoch" in rows[0]

    def test_max_attempts_deadletters_codex_failure(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "processing", "attempt_count": 4},
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "failed", "label": "p", "raw_path": "/a.md", "kind": "session", "slug": ""}],
            max_attempts=5,
        )
        assert deleted == 0
        assert dead == 1
        assert _read_queue(q) == []
        dead_rows = _read_queue(tmp_path / "ingest-deadletter.jsonl")
        assert len(dead_rows) == 1
        assert dead_rows[0]["last_error"] == "codex_failed"

    def test_missing_label_schedules_raw_missing_retry(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/b.md", "kind": "session", "status": "processing", "attempt_count": 0},
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "failed", "label": "missing:b.md", "raw_path": "/b.md", "kind": "session", "slug": ""}],
            max_attempts=5,
            max_raw_missing_attempts=5,
            raw_missing_retry_base_seconds=60,
        )
        assert deleted == 0
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["raw_missing_count"] == 1
        assert rows[0]["last_error"] == "raw_missing"
        assert "retry_after_epoch" in rows[0]
        # codex 失敗側の attempt_count は増えない（raw_missing は別カウンタ）
        assert rows[0].get("attempt_count", 0) == 0

    def test_missing_label_deadletters_at_max(self, tmp_path: Path) -> None:
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {
                "raw_path": "/b.md",
                "kind": "session",
                "status": "processing",
                "raw_missing_count": 4,
            },
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "failed", "label": "missing:b.md", "raw_path": "/b.md", "kind": "session", "slug": ""}],
            max_attempts=5,
            max_raw_missing_attempts=5,
        )
        assert deleted == 0
        assert dead == 1
        assert _read_queue(q) == []
        dead_rows = _read_queue(tmp_path / "ingest-deadletter.jsonl")
        assert len(dead_rows) == 1
        assert dead_rows[0]["last_error"] == "raw_missing"
        assert dead_rows[0]["raw_missing_count"] == 5

    def test_deferred_resets_to_pending_without_penalty(self, tmp_path: Path) -> None:
        """target lock 競合による deferred は pending へ戻し、試行回数を消費しない。"""
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {
                "raw_path": "/a.md",
                "kind": "session",
                "status": "processing",
                "attempt_count": 3,
                "processing_started_epoch": 123.0,
                "processing_started_at": "2026-01-01T00:00:00+00:00",
                "runner_pid": "999",
            },
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [{"status": "deferred", "label": "p1", "raw_path": "/a.md", "kind": "session", "slug": ""}],
            max_attempts=5,
        )
        assert deleted == 0
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1
        # pending に戻り即時再試行可能（retry_after 未設定）/ attempt_count 据え置き
        assert rows[0]["status"] == "pending"
        assert rows[0]["attempt_count"] == 3
        assert "retry_after_epoch" not in rows[0]
        assert "processing_started_epoch" not in rows[0]
        assert "runner_pid" not in rows[0]
        assert "last_error" not in rows[0]

    def test_deferred_and_success_mixed(self, tmp_path: Path) -> None:
        """同一 run で success は削除、deferred は pending 復帰する。"""
        q = tmp_path / "q.jsonl"
        _write_queue(q, [
            {"raw_path": "/a.md", "kind": "session", "status": "processing"},
            {"raw_path": "/b.md", "kind": "session", "status": "processing"},
        ])
        deleted, dead = wiki_queue.update_queue_after_results(
            q,
            [
                {"status": "success", "label": "a", "raw_path": "/a.md", "kind": "session", "slug": ""},
                {"status": "deferred", "label": "b", "raw_path": "/b.md", "kind": "session", "slug": ""},
            ],
            max_attempts=5,
        )
        assert deleted == 1
        assert dead == 0
        rows = _read_queue(q)
        assert len(rows) == 1
        assert rows[0]["raw_path"] == "/b.md"
        assert rows[0]["status"] == "pending"
