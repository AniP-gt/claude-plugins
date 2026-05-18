"""wiki/enqueue.py の単体テスト。

カバレッジ:

- sanitize_slug: 不正文字除去、空判定、長さクリップ、日本語通過
- detect_kind: パスから kind を推定
- _entry_identity: person のみ slug 含む、それ以外は空
- _append_entry: 新規追加、(raw_path, kind, slug) ベースの dedupe
- main(): minutes/diary の people_extract 自動連動、person の正常系・異常系、サニタイズ拒否、
  異 slug は別エントリ、raw_path 不在の rc=2、person 必須引数欠落の rc=3

すべて isolated_home fixture により HOME を tmp_path に固定し、実 ~/.local/share/
episodic/state/ingest-queue.jsonl を絶対に触らない。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


WIKI_DIR = Path(__file__).resolve().parent.parent / "wiki"
ENQUEUE_PY = WIKI_DIR / "enqueue.py"


# ============================================================================
# Pure-function tests (import enqueue.py module directly)
# ============================================================================


class TestSanitizeSlug:
    def test_japanese_passthrough(self, enqueue_module):
        assert enqueue_module.sanitize_slug("山田太郎") == "山田太郎"

    def test_hiragana_katakana(self, enqueue_module):
        assert enqueue_module.sanitize_slug("やまだタロウ") == "やまだタロウ"

    def test_iteration_mark(self, enqueue_module):
        # 々 と ー は許可文字
        assert enqueue_module.sanitize_slug("佐々木サーバー") == "佐々木サーバー"

    def test_ascii_alnum(self, enqueue_module):
        assert enqueue_module.sanitize_slug("john-doe_42") == "john-doe_42"

    def test_pipe_removed(self, enqueue_module):
        # sed 区切り文字インジェクション対策
        assert enqueue_module.sanitize_slug("田中|太郎") == "田中太郎"

    def test_path_traversal_neutralized(self, enqueue_module):
        # `..` / `/` が除去され、結果が `wiki/people/<slug>.md` を脱出できない
        assert enqueue_module.sanitize_slug("../../../etc/passwd") == "etcpasswd"

    def test_path_separator_removed(self, enqueue_module):
        assert enqueue_module.sanitize_slug("foo/bar\\baz") == "foobarbaz"

    def test_control_chars_removed(self, enqueue_module):
        assert enqueue_module.sanitize_slug("山田\t太郎\n") == "山田太郎"

    def test_dot_only_becomes_empty(self, enqueue_module):
        # `...` は先頭 dot ストリップ後に空
        assert enqueue_module.sanitize_slug("...") == ""

    def test_leading_dash_stripped(self, enqueue_module):
        assert enqueue_module.sanitize_slug("-山田") == "山田"

    def test_punctuation_removed_to_empty(self, enqueue_module):
        assert enqueue_module.sanitize_slug("!!!") == ""

    def test_empty_input(self, enqueue_module):
        assert enqueue_module.sanitize_slug("") == ""

    def test_long_clipped(self, enqueue_module):
        long = "山" * 200
        assert len(enqueue_module.sanitize_slug(long)) == 96


class TestDetectKind:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("/m/raw/session/2026-05-15/foo.md", "session"),
            ("/m/raw/web/2026-05-15/foo.md", "web"),
            ("/m/raw/minutes/2026-05-15/foo.md", "minutes"),
            ("/m/raw/diary/2026-05-15/foo.md", "diary"),
            ("/m/no-raw-dir/foo.md", "session"),  # fallback
        ],
    )
    def test_kind_detection(self, enqueue_module, path, expected):
        assert enqueue_module.detect_kind(Path(path)) == expected


class TestEntryIdentity:
    def test_non_person_ignores_slug(self, enqueue_module):
        e = {"raw_path": "/x", "kind": "minutes", "slug": "ignored"}
        assert enqueue_module._entry_identity(e) == ("/x", "minutes", "")

    def test_person_includes_slug(self, enqueue_module):
        e = {"raw_path": "/x", "kind": "person", "slug": "山田太郎"}
        assert enqueue_module._entry_identity(e) == ("/x", "person", "山田太郎")

    def test_person_missing_slug_uses_empty(self, enqueue_module):
        e = {"raw_path": "/x", "kind": "person"}
        assert enqueue_module._entry_identity(e) == ("/x", "person", "")


class TestAppendEntry:
    def test_first_append_returns_true(self, enqueue_module, tmp_path):
        q = tmp_path / "queue.jsonl"
        entry = {"raw_path": "/x", "kind": "minutes", "status": "pending"}
        assert enqueue_module._append_entry(q, entry) is True
        assert q.read_text().count("\n") == 1

    def test_duplicate_returns_false(self, enqueue_module, tmp_path):
        q = tmp_path / "queue.jsonl"
        entry = {"raw_path": "/x", "kind": "minutes", "status": "pending"}
        assert enqueue_module._append_entry(q, entry) is True
        assert enqueue_module._append_entry(q, entry) is False
        assert q.read_text().count("\n") == 1

    def test_non_pending_does_not_dedupe(self, enqueue_module, tmp_path):
        # 既存エントリが status=processing なら新規 pending を追加できる
        q = tmp_path / "queue.jsonl"
        q.write_text(
            json.dumps({"raw_path": "/x", "kind": "minutes", "status": "processing"})
            + "\n",
            encoding="utf-8",
        )
        entry = {"raw_path": "/x", "kind": "minutes", "status": "pending"}
        assert enqueue_module._append_entry(q, entry) is True
        assert q.read_text().count("\n") == 2

    def test_different_kind_not_deduped(self, enqueue_module, tmp_path):
        q = tmp_path / "queue.jsonl"
        e1 = {"raw_path": "/x", "kind": "minutes", "status": "pending"}
        e2 = {"raw_path": "/x", "kind": "people_extract", "status": "pending"}
        assert enqueue_module._append_entry(q, e1) is True
        assert enqueue_module._append_entry(q, e2) is True

    def test_person_different_slug_not_deduped(self, enqueue_module, tmp_path):
        q = tmp_path / "queue.jsonl"
        e1 = {"raw_path": "/x", "kind": "person", "slug": "山田太郎", "status": "pending"}
        e2 = {"raw_path": "/x", "kind": "person", "slug": "鈴木一郎", "status": "pending"}
        assert enqueue_module._append_entry(q, e1) is True
        assert enqueue_module._append_entry(q, e2) is True

    def test_person_same_slug_deduped(self, enqueue_module, tmp_path):
        q = tmp_path / "queue.jsonl"
        e = {"raw_path": "/x", "kind": "person", "slug": "山田太郎", "status": "pending"}
        assert enqueue_module._append_entry(q, e) is True
        assert enqueue_module._append_entry(q, dict(e)) is False


# ============================================================================
# E2E tests via subprocess (verify main() argparse + auto-cascade behavior)
# ============================================================================


def _run_enqueue(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """enqueue.py を subprocess で呼ぶ。HOME は引数 home に強制。"""
    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    return subprocess.run(
        [sys.executable, str(ENQUEUE_PY), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def _read_queue(home: Path) -> list[dict]:
    q = home / ".local" / "share" / "episodic" / "state" / "ingest-queue.jsonl"
    if not q.exists():
        return []
    return [
        json.loads(line)
        for line in q.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestMainAutoCascade:
    def test_minutes_enqueue_also_creates_people_extract(
        self, isolated_home, fake_raw, tmp_path
    ):
        r = _run_enqueue(tmp_path, str(fake_raw), "--kind", "minutes")
        assert r.returncode == 0, r.stderr
        entries = _read_queue(tmp_path)
        kinds = [e["kind"] for e in entries]
        assert kinds == ["minutes", "people_extract"]
        # source_kind が保持される
        pe = next(e for e in entries if e["kind"] == "people_extract")
        assert pe["source_kind"] == "minutes"

    def test_diary_enqueue_also_creates_people_extract(
        self, isolated_home, fake_diary_raw, tmp_path
    ):
        r = _run_enqueue(tmp_path, str(fake_diary_raw), "--kind", "diary")
        assert r.returncode == 0, r.stderr
        entries = _read_queue(tmp_path)
        kinds = [e["kind"] for e in entries]
        assert kinds == ["diary", "people_extract"]

    def test_session_does_not_create_people_extract(self, isolated_home, tmp_path):
        # session Raw を作る
        raw_dir = tmp_path / "memories" / "raw" / "session" / "2026-05-15"
        raw_dir.mkdir(parents=True)
        raw_path = raw_dir / "000000_test.md"
        raw_path.write_text("---\nkind: session\n---\n", encoding="utf-8")
        r = _run_enqueue(tmp_path, str(raw_path), "--kind", "session")
        assert r.returncode == 0
        entries = _read_queue(tmp_path)
        assert [e["kind"] for e in entries] == ["session"]

    def test_minutes_reenqueue_dedupes_both_entries(
        self, isolated_home, fake_raw, tmp_path
    ):
        _run_enqueue(tmp_path, str(fake_raw), "--kind", "minutes")
        r = _run_enqueue(tmp_path, str(fake_raw), "--kind", "minutes")
        assert r.returncode == 0
        assert "skip:" in r.stderr  # 何らかのスキップメッセージ
        entries = _read_queue(tmp_path)
        # 2 件のまま（重複なし）
        assert len(entries) == 2


class TestMainErrorCases:
    def test_missing_raw_path_returns_2(self, isolated_home, tmp_path):
        r = _run_enqueue(tmp_path, str(tmp_path / "nonexistent.md"), "--kind", "minutes")
        assert r.returncode == 2

    def test_person_without_name_returns_3(self, isolated_home, fake_raw, tmp_path):
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--slug", "山田太郎",
            "--source-kind", "minutes",
        )
        assert r.returncode == 3

    def test_person_without_slug_returns_3(self, isolated_home, fake_raw, tmp_path):
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "山田太郎",
            "--source-kind", "minutes",
        )
        assert r.returncode == 3

    def test_person_without_source_kind_returns_3(self, isolated_home, fake_raw, tmp_path):
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "山田太郎",
            "--slug", "山田太郎",
        )
        assert r.returncode == 3

    def test_person_slug_sanitized_to_empty_returns_3(
        self, isolated_home, fake_raw, tmp_path
    ):
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "bad",
            "--slug", "!!!",
            "--source-kind", "minutes",
        )
        assert r.returncode == 3
        assert "becomes empty after sanitize" in r.stderr


class TestMainPersonHappyPath:
    def test_person_normal_path(self, isolated_home, fake_raw, tmp_path):
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "山田太郎",
            "--slug", "山田太郎",
            "--source-kind", "minutes",
            "--aliases", "山田さん,Yamada",
            "--context", "4月の定例で新機能の方針を提示",
        )
        assert r.returncode == 0, r.stderr
        entries = _read_queue(tmp_path)
        assert len(entries) == 1
        e = entries[0]
        assert e["kind"] == "person"
        assert e["name"] == "山田太郎"
        assert e["slug"] == "山田太郎"
        assert e["aliases"] == ["山田さん", "Yamada"]
        assert e["source_kind"] == "minutes"
        assert e["context"] == "4月の定例で新機能の方針を提示"

    def test_person_pipe_slug_sanitized_and_appended(
        self, isolated_home, fake_raw, tmp_path
    ):
        # sed インジェクション攻撃シナリオ
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "田中|太郎",
            "--slug", "田中|太郎",
            "--source-kind", "minutes",
        )
        assert r.returncode == 0
        assert "slug sanitized" in r.stderr
        entries = _read_queue(tmp_path)
        assert len(entries) == 1
        assert entries[0]["slug"] == "田中太郎"

    def test_person_path_traversal_sanitized(
        self, isolated_home, fake_raw, tmp_path
    ):
        # パストラバーサル攻撃シナリオ
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "evil",
            "--slug", "../../../etc/passwd",
            "--source-kind", "minutes",
        )
        assert r.returncode == 0
        entries = _read_queue(tmp_path)
        assert len(entries) == 1
        assert entries[0]["slug"] == "etcpasswd"
        assert "/" not in entries[0]["slug"]
        assert ".." not in entries[0]["slug"]

    def test_person_same_slug_deduped_via_main(
        self, isolated_home, fake_raw, tmp_path
    ):
        args = [
            str(fake_raw),
            "--kind", "person",
            "--name", "山田太郎",
            "--slug", "山田太郎",
            "--source-kind", "minutes",
        ]
        _run_enqueue(tmp_path, *args)
        r = _run_enqueue(tmp_path, *args)
        assert r.returncode == 0
        assert "skip:" in r.stderr
        assert len(_read_queue(tmp_path)) == 1

    def test_person_different_slug_not_deduped_via_main(
        self, isolated_home, fake_raw, tmp_path
    ):
        _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "山田太郎",
            "--slug", "山田太郎",
            "--source-kind", "minutes",
        )
        r = _run_enqueue(
            tmp_path,
            str(fake_raw),
            "--kind", "person",
            "--name", "鈴木一郎",
            "--slug", "鈴木一郎",
            "--source-kind", "minutes",
        )
        assert r.returncode == 0
        entries = _read_queue(tmp_path)
        assert len(entries) == 2
        slugs = sorted(e["slug"] for e in entries)
        assert slugs == ["山田太郎", "鈴木一郎"]


class TestRealQueueIsNotTouched:
    """テスト実行で実 HOME 配下の queue を絶対に触らないことを担保する回帰防止テスト。

    過去（2026-05-15）に HOME 隔離不備で実 queue を汚染したインシデントの
    再発を検知する。
    """

    def test_isolated_home_path_under_tmp(self, isolated_home, tmp_path):
        # state_dir が tmp_path 配下に位置することを確認
        assert str(isolated_home).startswith(str(tmp_path))

    def test_enqueue_writes_only_under_tmp_home(
        self, isolated_home, fake_raw, tmp_path
    ):
        _run_enqueue(tmp_path, str(fake_raw), "--kind", "minutes")
        q = tmp_path / ".local" / "share" / "episodic" / "state" / "ingest-queue.jsonl"
        assert q.exists()
        # tmp_path の外には書かれていない（real_home に書き込んでいないことの状況証拠）
        assert str(q.resolve()).startswith(str(tmp_path.resolve()))
