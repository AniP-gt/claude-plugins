"""lib/frontmatter.py の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import frontmatter as fm  # noqa: E402


def test_parse_basic(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\nkind: session\nmessage_count: 42\n---\n\nbody\n")
    out = fm.parse(p)
    assert out == {"kind": "session", "message_count": "42"}


def test_parse_strip_quotes(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text('---\ntitle: "a b"\nname: \'c\'\n---\nbody')
    out = fm.parse(p)
    assert out == {"title": "a b", "name": "c"}


def test_parse_strip_inline_comment(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\nkind: session #コメント\n---\nbody")
    assert fm.parse(p) == {"kind": "session"}


def test_parse_missing_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("no frontmatter here")
    assert fm.parse(p) == {}


def test_parse_missing_file(tmp_path: Path) -> None:
    assert fm.parse(tmp_path / "nope.md") == {}


def test_patch_replaces_existing(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\nkind: session\nstatus: active\n---\n\nbody\n")
    fm.patch(p, {"status": "superseded"})
    out = fm.parse(p)
    assert out["status"] == "superseded"
    assert "body" in p.read_text()


def test_patch_appends_new_key(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\nkind: session\n---\nbody")
    fm.patch(p, {"new_key": "value"})
    assert fm.parse(p)["new_key"] == "value"


def test_patch_noop_when_no_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("plain text")
    fm.patch(p, {"k": "v"})
    assert p.read_text() == "plain text"
