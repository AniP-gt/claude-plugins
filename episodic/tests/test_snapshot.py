"""lib/snapshot.py の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import snapshot as snap  # noqa: E402


def test_skip_when_already_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "in.jsonl"
    src.write_text("a")
    dst = tmp_path / "out.jsonl"
    dst.write_text("existing")
    monkeypatch.setattr(snap.pr, "twin_snapshot_path", lambda p: None)
    assert snap.save_source_snapshot(dst, src) == snap.SnapshotResult.SKIP_ALREADY_EXISTS


def test_skip_twin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "in.jsonl"
    src.write_text("a")
    twin = tmp_path / "twin.jsonl"
    twin.write_text("t")
    dst = tmp_path / "out.jsonl"
    monkeypatch.setattr(snap.pr, "twin_snapshot_path", lambda p: twin)
    assert snap.save_source_snapshot(dst, src) == snap.SnapshotResult.SKIP_TWIN_EXISTS


def test_skip_traversal(tmp_path: Path) -> None:
    assert snap.save_source_snapshot("/x/../y", str(tmp_path / "src.jsonl")) == snap.SnapshotResult.SKIP_TRAVERSAL


def test_skip_source_missing(tmp_path: Path) -> None:
    assert snap.save_source_snapshot(tmp_path / "x.jsonl", tmp_path / "nope.jsonl") == snap.SnapshotResult.SKIP_SOURCE_MISSING


def test_plain_jsonl_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "in.jsonl"
    src.write_bytes(b"hello\n")
    dst = tmp_path / "out.jsonl"
    monkeypatch.setattr(snap.pr, "twin_snapshot_path", lambda p: None)
    result = snap.save_source_snapshot(dst, src)
    assert result == snap.SnapshotResult.SAVED
    assert dst.read_bytes() == b"hello\n"
    assert not (tmp_path / "out.jsonl.partial").exists()


def test_zstd_fallback_to_plain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "in.jsonl"
    src.write_bytes(b"data")
    dst = tmp_path / "out.jsonl.zst"
    monkeypatch.setattr(snap.pr, "twin_snapshot_path", lambda p: None)
    monkeypatch.setattr(snap.shutil, "which", lambda n: None)
    result = snap.save_source_snapshot(dst, src)
    assert result == snap.SnapshotResult.SAVED_FALLBACK
    plain = tmp_path / "out.jsonl"
    assert plain.read_bytes() == b"data"


def test_bad_extension(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "in.jsonl"
    src.write_text("x")
    monkeypatch.setattr(snap.pr, "twin_snapshot_path", lambda p: None)
    assert snap.save_source_snapshot(tmp_path / "x.txt", src) == snap.SnapshotResult.SKIP_BAD_EXT
