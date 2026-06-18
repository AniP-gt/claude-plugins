"""lib/staging_scanner.py の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.staging_scanner import scan_staged_files  # noqa: E402


def test_empty_dir(tmp_path: Path) -> None:
    assert scan_staged_files(tmp_path) == []


def test_missing_dir(tmp_path: Path) -> None:
    assert scan_staged_files(tmp_path / "nope") == []


def test_session_path(tmp_path: Path) -> None:
    f = tmp_path / "2026-05-19" / "010203_abcd1234_sess0001__staged.md"
    f.parent.mkdir(parents=True)
    f.write_text("---\nkind: session\n---\n")
    out = scan_staged_files(tmp_path)
    assert len(out) == 1
    assert out[0].path == f
    assert out[0].kind == "session"


def test_kind_subdirs(tmp_path: Path) -> None:
    for kind in ("web", "minutes", "diary"):
        d = tmp_path / kind / "2026-05-19"
        d.mkdir(parents=True)
        (d / "010203_test__staged.md").write_text("body")
    out = scan_staged_files(tmp_path)
    kinds = {e.kind for e in out}
    assert kinds == {"web", "minutes", "diary"}


def test_session_source_jsonl(tmp_path: Path) -> None:
    d = tmp_path / "session-source" / "2026-05-19"
    d.mkdir(parents=True)
    (d / "010203_test__staged.jsonl").write_text("")
    (d / "010204_test__staged.jsonl.zst").write_bytes(b"")
    (d / "ignore.md").write_text("")
    out = scan_staged_files(tmp_path)
    paths = sorted(e.path.name for e in out)
    assert paths == ["010203_test__staged.jsonl", "010204_test__staged.jsonl.zst"]
    assert all(e.kind == "session-source" for e in out)


def test_excludes_kind_dirs_from_session_scan(tmp_path: Path) -> None:
    # session 経路は kind サブディレクトリを拾わない
    (tmp_path / "web" / "2026-05-19").mkdir(parents=True)
    (tmp_path / "web" / "2026-05-19" / "x__staged.md").write_text("")
    out = scan_staged_files(tmp_path)
    assert all(e.kind == "web" for e in out)
