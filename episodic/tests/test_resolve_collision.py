"""lib/resolve_collision.py の単体テスト。

カバレッジ:
  - frontmatter 解析（ended_at / updated_at / message_count）
  - winner 判定の優先順位（ended_at > updated_at > message_count > mtime）
  - revision 連番（__r1, __r2, ...）
  - session/web/minutes/diary（.md）の解決と frontmatter 更新
  - session-source（.jsonl.zst）の paired-winner / mtime fallback
  - 自己参照禁止アサート（src == dst で error）
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def resolver_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(PLUGIN_ROOT))
    sys.modules.pop("lib.resolve_collision", None)
    from lib import resolve_collision  # type: ignore[import-not-found]
    return resolve_collision


def _write_md(path: Path, ended_at: str | None = None, updated_at: str | None = None,
              message_count: int | None = None, status: str = "active", body: str = "body") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "kind: session", "session_id: dummy"]
    if ended_at is not None:
        lines.append(f"ended_at: {ended_at}")
    if updated_at is not None:
        lines.append(f"updated_at: {updated_at}")
    if message_count is not None:
        lines.append(f"message_count: {message_count}")
    lines.append(f"status: {status}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    path.write_text("\n".join(lines), encoding="utf-8")


class TestParseFrontmatter:
    def test_basic(self, resolver_module, tmp_path: Path):
        p = tmp_path / "x.md"
        _write_md(p, ended_at="2026-05-19T15:00:00+09:00", message_count=42)
        fm = resolver_module._parse_frontmatter(p)
        assert fm["ended_at"] == "2026-05-19T15:00:00+09:00"
        assert fm["message_count"] == "42"
        assert fm["status"] == "active"

    def test_no_frontmatter(self, resolver_module, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text("no fm here", encoding="utf-8")
        assert resolver_module._parse_frontmatter(p) == {}

    def test_quoted_value_stripped(self, resolver_module, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text('---\ntitle: "Hello World"\n---\n\nbody', encoding="utf-8")
        assert resolver_module._parse_frontmatter(p)["title"] == "Hello World"


class TestCompare:
    def test_ended_at_wins(self, resolver_module):
        src = (100.0, 50.0, 100, 0.0)
        dst = (90.0, 200.0, 200, 999.0)
        assert resolver_module._compare(src, dst) == "src"

    def test_falls_back_to_updated_at(self, resolver_module):
        src = (None, 100.0, 1, 0.0)
        dst = (None, 50.0, 999, 0.0)
        assert resolver_module._compare(src, dst) == "src"

    def test_falls_back_to_message_count(self, resolver_module):
        src = (None, None, 100, 0.0)
        dst = (None, None, 200, 999.0)
        assert resolver_module._compare(src, dst) == "dst"

    def test_mtime_tiebreaker(self, resolver_module):
        src = (None, None, None, 200.0)
        dst = (None, None, None, 100.0)
        assert resolver_module._compare(src, dst) == "src"

    def test_no_signal_returns_none(self, resolver_module):
        src = (None, None, None, 0.0)
        dst = (None, None, None, 0.0)
        assert resolver_module._compare(src, dst) is None


class TestRevisionPath:
    def test_first_slot(self, resolver_module, tmp_path: Path):
        dst = tmp_path / "abc.md"
        dst.write_text("x", encoding="utf-8")
        rev = resolver_module._next_revision_path(dst)
        assert rev.name == "abc__r1.md"

    def test_increments(self, resolver_module, tmp_path: Path):
        dst = tmp_path / "abc.md"
        dst.write_text("x", encoding="utf-8")
        (tmp_path / "abc__r1.md").write_text("x", encoding="utf-8")
        (tmp_path / "abc__r2.md").write_text("x", encoding="utf-8")
        rev = resolver_module._next_revision_path(dst)
        assert rev.name == "abc__r3.md"

    def test_jsonl_zst_extension(self, resolver_module, tmp_path: Path):
        dst = tmp_path / "abc.jsonl.zst"
        dst.write_text("x", encoding="utf-8")
        rev = resolver_module._next_revision_path(dst)
        assert rev.name == "abc__r1.jsonl.zst"


class TestResolveMd:
    def test_src_newer_wins(self, resolver_module, tmp_path: Path):
        src = tmp_path / "staging" / "141203_b4dab9d6_019e3ea5__staged.md"
        dst = tmp_path / "canonical" / "141203_b4dab9d6_019e3ea5.md"
        _write_md(src, ended_at="2026-05-19T15:09:00+09:00", message_count=900)
        _write_md(dst, ended_at="2026-05-19T14:55:00+09:00", message_count=600)

        result = resolver_module.resolve(src, dst, "session", None)
        assert result["winner"] == "src"
        assert not src.exists()
        assert dst.exists()
        rev = Path(result["revision"])
        assert rev.exists()
        assert rev.name == "141203_b4dab9d6_019e3ea5__r1.md"

        rev_fm = resolver_module._parse_frontmatter(rev)
        assert rev_fm["status"] == "superseded"
        assert rev_fm["superseded_by"] == str(dst)

        dst_fm = resolver_module._parse_frontmatter(dst)
        assert dst_fm["supersedes"] == str(rev)
        assert dst_fm.get("status") == "active"

    def test_dst_newer_wins(self, resolver_module, tmp_path: Path):
        src = tmp_path / "staging" / "x__staged.md"
        dst = tmp_path / "canonical" / "x.md"
        _write_md(src, ended_at="2026-05-19T14:55:00+09:00", message_count=600)
        _write_md(dst, ended_at="2026-05-19T15:09:00+09:00", message_count=900)

        result = resolver_module.resolve(src, dst, "session", None)
        assert result["winner"] == "dst"
        assert not src.exists()
        rev = Path(result["revision"])
        assert rev.exists()
        assert rev.parent == dst.parent  # revision は canonical 隣
        rev_fm = resolver_module._parse_frontmatter(rev)
        assert rev_fm["status"] == "superseded"

    def test_self_reference_prevented(self, resolver_module, tmp_path: Path):
        # 新 canonical の supersedes は自分自身を指してはいけない
        src = tmp_path / "staging" / "x__staged.md"
        dst = tmp_path / "canonical" / "x.md"
        _write_md(src, ended_at="2026-05-19T15:09:00+09:00")
        _write_md(dst, ended_at="2026-05-19T14:55:00+09:00")

        result = resolver_module.resolve(src, dst, "session", None)
        assert result["winner"] == "src"
        dst_fm = resolver_module._parse_frontmatter(dst)
        assert dst_fm["supersedes"] != str(dst)


class TestResolveSessionSource:
    def test_paired_winner_src(self, resolver_module, tmp_path: Path):
        src = tmp_path / "staging" / "x__staged.jsonl.zst"
        dst = tmp_path / "canonical" / "x.jsonl.zst"
        src.parent.mkdir(parents=True)
        dst.parent.mkdir(parents=True)
        src.write_bytes(b"new")
        dst.write_bytes(b"old")

        result = resolver_module.resolve(src, dst, "session-source", "src")
        assert result["winner"] == "src"
        assert dst.read_bytes() == b"new"
        rev = Path(result["revision"])
        assert rev.read_bytes() == b"old"

    def test_paired_winner_dst(self, resolver_module, tmp_path: Path):
        src = tmp_path / "staging" / "x__staged.jsonl.zst"
        dst = tmp_path / "canonical" / "x.jsonl.zst"
        src.parent.mkdir(parents=True)
        dst.parent.mkdir(parents=True)
        src.write_bytes(b"new-but-discard")
        dst.write_bytes(b"keep")

        result = resolver_module.resolve(src, dst, "session-source", "dst")
        assert result["winner"] == "dst"
        assert dst.read_bytes() == b"keep"
        rev = Path(result["revision"])
        assert rev.read_bytes() == b"new-but-discard"


class TestRetireToRevision:
    def test_md_canonical_retired_and_frontmatter_patched(self, resolver_module, tmp_path: Path):
        canonical = tmp_path / "141203_b4dab9d6_019e3ea5.md"
        _write_md(canonical, ended_at="2026-05-19T14:55:00+09:00", status="active")
        revision = resolver_module.retire_to_revision(canonical, "session", new_canonical=canonical)
        assert revision.exists()
        assert revision.name == "141203_b4dab9d6_019e3ea5__r1.md"
        assert not canonical.exists()
        fm = resolver_module._parse_frontmatter(revision)
        assert fm["status"] == "superseded"
        assert fm["superseded_by"] == str(canonical)
        assert "superseded_at" in fm

    def test_binary_canonical_retired_no_frontmatter(self, resolver_module, tmp_path: Path):
        canonical = tmp_path / "x.jsonl.zst"
        canonical.write_bytes(b"binary")
        revision = resolver_module.retire_to_revision(canonical, "session-source")
        assert revision.exists()
        assert revision.name == "x__r1.jsonl.zst"
        assert revision.read_bytes() == b"binary"
        assert not canonical.exists()

    def test_missing_canonical_raises(self, resolver_module, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            resolver_module.retire_to_revision(tmp_path / "missing.md", "session")

    def test_next_revision_increments(self, resolver_module, tmp_path: Path):
        canonical = tmp_path / "x.md"
        _write_md(canonical)
        (tmp_path / "x__r1.md").write_text("old", encoding="utf-8")
        revision = resolver_module.retire_to_revision(canonical, "session")
        assert revision.name == "x__r2.md"


class TestCli:
    def test_resolves_and_emits_json(self, tmp_path: Path):
        src = tmp_path / "staging" / "x__staged.md"
        dst = tmp_path / "canonical" / "x.md"
        _write_md(src, ended_at="2026-05-19T15:00:00+09:00")
        _write_md(dst, ended_at="2026-05-19T14:00:00+09:00")
        env = {**os.environ, "PYTHONPATH": str(PLUGIN_ROOT)}
        proc = subprocess.run(
            [sys.executable, "-m", "lib.resolve_collision",
             "--src", str(src), "--dst", str(dst), "--kind", "session"],
            capture_output=True, text=True, env=env, check=False,
        )
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout.strip())
        assert out["winner"] == "src"

    def test_missing_src_returns_error(self, tmp_path: Path):
        dst = tmp_path / "x.md"
        _write_md(dst)
        env = {**os.environ, "PYTHONPATH": str(PLUGIN_ROOT)}
        proc = subprocess.run(
            [sys.executable, "-m", "lib.resolve_collision",
             "--src", str(tmp_path / "missing.md"), "--dst", str(dst), "--kind", "session"],
            capture_output=True, text=True, env=env, check=False,
        )
        assert proc.returncode != 0
        out = json.loads(proc.stdout.strip())
        assert out["action"] == "error"
