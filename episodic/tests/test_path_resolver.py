"""lib/path_resolver.py の単体テスト。

to_normal_basename / to_normal_snapshot_basename の staged↔normal 往復、
twin_report_path / twin_snapshot_path、__staged サフィックス処理、
不正 basename・.jsonl.zst 二重拡張子の境界を検証する。

twin_* は cfg.resolve_memories_dir() / resolve_fallback_dir() を参照するため、
config の env を tmp に固定し lru_cache をクリアする。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import config as config_mod  # noqa: E402
from lib import path_resolver as pr  # noqa: E402


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    mem = tmp_path / "memory"
    fb = tmp_path / "staging"
    mem.mkdir()
    fb.mkdir()
    monkeypatch.setenv("MEMORIES_DIR", str(mem))
    monkeypatch.setenv("MEMORIES_FALLBACK_DIR", str(fb))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "no-such-config.toml")
    config_mod.load_config.cache_clear()
    yield {"memories": mem.resolve(), "fallback": fb.resolve()}
    config_mod.load_config.cache_clear()


# ---------------------------------------------------------------- to_normal_basename


def test_to_normal_basename_strips_staged_suffix() -> None:
    assert pr.to_normal_basename("100000_h_s__staged.md") == "100000_h_s.md"


def test_to_normal_basename_passthrough_without_suffix() -> None:
    assert pr.to_normal_basename("100000_h_s.md") == "100000_h_s.md"


def test_to_normal_basename_staged_without_md_extension() -> None:
    # __staged.md で終わらないものは不変（不正 basename の境界）
    assert pr.to_normal_basename("100000_h_s__staged") == "100000_h_s__staged"


# ---------------------------------------------------------------- to_normal_snapshot_basename


def test_to_normal_snapshot_basename_jsonl() -> None:
    assert pr.to_normal_snapshot_basename("100000_h_s__staged.jsonl") == "100000_h_s.jsonl"


def test_to_normal_snapshot_basename_jsonl_zst_double_ext() -> None:
    # .jsonl.zst 二重拡張子を取りこぼさず正規化する（.jsonl を先に剥がさない）
    assert pr.to_normal_snapshot_basename("100000_h_s__staged.jsonl.zst") == "100000_h_s.jsonl.zst"


def test_to_normal_snapshot_basename_passthrough() -> None:
    assert pr.to_normal_snapshot_basename("100000_h_s.jsonl.zst") == "100000_h_s.jsonl.zst"
    assert pr.to_normal_snapshot_basename("100000_h_s.jsonl") == "100000_h_s.jsonl"


# ---------------------------------------------------------------- twin_report_path


def test_twin_report_path_staged_to_normal(env) -> None:
    staged = env["fallback"] / "2026-05-19" / "100000_h_s__staged.md"
    twin = pr.twin_report_path(staged)
    assert twin == env["memories"] / "raw" / "session" / "2026-05-19" / "100000_h_s.md"


def test_twin_report_path_normal_to_staged(env) -> None:
    normal = env["memories"] / "raw" / "session" / "2026-05-19" / "100000_h_s.md"
    twin = pr.twin_report_path(normal)
    assert twin == env["fallback"] / "2026-05-19" / "100000_h_s__staged.md"


def test_twin_report_path_round_trip(env) -> None:
    staged = env["fallback"] / "2026-05-19" / "100000_h_s__staged.md"
    assert pr.twin_report_path(pr.twin_report_path(staged)) == staged


def test_twin_report_path_non_md_returns_none(env) -> None:
    assert pr.twin_report_path(env["memories"] / "2026-05-19" / "100000_h_s.txt") is None


# ---------------------------------------------------------------- twin_snapshot_path


def test_twin_snapshot_path_staged_to_normal_zst(env) -> None:
    staged = env["fallback"] / "session-source" / "2026-05-19" / "100000_h_s__staged.jsonl.zst"
    twin = pr.twin_snapshot_path(staged)
    assert twin == env["memories"] / "raw" / "session-source" / "2026-05-19" / "100000_h_s.jsonl.zst"


def test_twin_snapshot_path_normal_to_staged_jsonl(env) -> None:
    normal = env["memories"] / "raw" / "session-source" / "2026-05-19" / "100000_h_s.jsonl"
    twin = pr.twin_snapshot_path(normal)
    assert twin == env["fallback"] / "session-source" / "2026-05-19" / "100000_h_s__staged.jsonl"


def test_twin_snapshot_path_round_trip_zst(env) -> None:
    staged = env["fallback"] / "session-source" / "2026-05-19" / "100000_h_s__staged.jsonl.zst"
    assert pr.twin_snapshot_path(pr.twin_snapshot_path(staged)) == staged


def test_twin_snapshot_path_unknown_ext_returns_none(env) -> None:
    assert pr.twin_snapshot_path(env["memories"] / "2026-05-19" / "100000_h_s.md") is None


# ---------------------------------------------------------------- map_* helpers


def test_map_staged_to_normal(env) -> None:
    staged = env["fallback"] / "2026-05-19" / "100000_h_s__staged.md"
    mapped = pr.map_staged_to_normal(staged, env["memories"])
    assert mapped == env["memories"] / "raw" / "session" / "2026-05-19" / "100000_h_s.md"


def test_map_snapshot_staged_to_normal_zst(env) -> None:
    staged = env["fallback"] / "session-source" / "2026-05-19" / "100000_h_s__staged.jsonl.zst"
    mapped = pr.map_snapshot_staged_to_normal(staged, env["memories"])
    assert mapped == env["memories"] / "raw" / "session-source" / "2026-05-19" / "100000_h_s.jsonl.zst"
