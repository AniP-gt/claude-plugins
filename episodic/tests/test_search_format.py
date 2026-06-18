"""scripts/search/format.py の純関数テスト（DB 接続不要）。

format.py は stdlib のみ依存。importlib のファイルパス指定でロードし、
parse_search_output / filter_scope / filter_status の代表ケースを検証する。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

FORMAT_PY = Path(__file__).resolve().parent.parent / "scripts" / "search" / "format.py"


@pytest.fixture(scope="module")
def fmt():
    spec = importlib.util.spec_from_file_location("episodic_format_under_test", FORMAT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- parse_search_output


def test_parse_basic_two_hits(fmt) -> None:
    text = "[0.823] /a/b.md\n  hello world\n[0.745] /c/d.md\n  second preview\n"
    hits = fmt.parse_search_output(text)
    assert len(hits) == 2
    assert hits[0] == {"score": 0.823, "path": "/a/b.md", "snippet": "hello world"}
    assert hits[1]["score"] == 0.745
    assert hits[1]["path"] == "/c/d.md"
    assert hits[1]["snippet"] == "second preview"


def test_parse_joins_multiline_snippet(fmt) -> None:
    text = "[0.5] /x.md\n  line1\n  line2\n"
    hits = fmt.parse_search_output(text)
    assert hits[0]["snippet"] == "line1 line2"


def test_parse_path_is_stripped(fmt) -> None:
    hits = fmt.parse_search_output("[0.9] /spaced/path.md   \n")
    assert hits[0]["path"] == "/spaced/path.md"


def test_parse_ignores_preamble_before_first_header(fmt) -> None:
    hits = fmt.parse_search_output("garbage line\n[0.9] /p.md\n  snip\n")
    assert len(hits) == 1
    assert hits[0]["path"] == "/p.md"


def test_parse_empty(fmt) -> None:
    assert fmt.parse_search_output("") == []


# ---------------------------------------------------------------- filter_scope


def test_filter_scope_all_always_true(fmt, tmp_path) -> None:
    hit = {"path": str(tmp_path / "raw" / "diary" / "2026-05-19" / "x.md")}
    assert fmt.filter_scope(hit, tmp_path, "all") is True


def test_filter_scope_session_match(fmt, tmp_path) -> None:
    p = tmp_path / "raw" / "session" / "2026-05-19" / "x.md"
    assert fmt.filter_scope({"path": str(p)}, tmp_path, "session") is True


def test_filter_scope_session_excludes_other_kind(fmt, tmp_path) -> None:
    p = tmp_path / "raw" / "web" / "2026-05-19" / "x.md"
    assert fmt.filter_scope({"path": str(p)}, tmp_path, "session") is False


def test_filter_scope_wiki(fmt, tmp_path) -> None:
    p = tmp_path / "wiki" / "person" / "x.md"
    assert fmt.filter_scope({"path": str(p)}, tmp_path, "wiki") is True
    # wiki scope は raw/session を拾わない
    other = tmp_path / "raw" / "session" / "2026-05-19" / "x.md"
    assert fmt.filter_scope({"path": str(other)}, tmp_path, "wiki") is False


def test_filter_scope_outside_memories_dir(fmt, tmp_path) -> None:
    outside = tmp_path.parent / "outside-root" / "x.md"
    assert fmt.filter_scope({"path": str(outside)}, tmp_path, "session") is False


def test_filter_scope_relative_path_resolved(fmt, tmp_path) -> None:
    # 相対パスは memories_dir 基準で解決される
    hit = {"path": "raw/minutes/2026-05-19/x.md"}
    assert fmt.filter_scope(hit, tmp_path, "minutes") is True


# ---------------------------------------------------------------- filter_status


def test_filter_status_active(fmt) -> None:
    assert fmt.filter_status({"status": "active"}, include_superseded=False) is True


def test_filter_status_missing_defaults_active(fmt) -> None:
    assert fmt.filter_status({}, include_superseded=False) is True


def test_filter_status_superseded_excluded(fmt) -> None:
    assert fmt.filter_status({"status": "superseded"}, include_superseded=False) is False


def test_filter_status_deprecated_excluded(fmt) -> None:
    assert fmt.filter_status({"status": "deprecated"}, include_superseded=False) is False


def test_filter_status_include_superseded_overrides(fmt) -> None:
    assert fmt.filter_status({"status": "superseded"}, include_superseded=True) is True
    assert fmt.filter_status({"status": "deprecated"}, include_superseded=True) is True
