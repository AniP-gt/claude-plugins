"""scripts/search/search.py の純関数テスト（DB 接続不要）。

scripts/search/ は package ではなく、search.py のトップレベルで
dotenv / psycopg2 / voyageai を import し、import 時に load_dotenv() も呼ぶ。
これらを sys.modules にスタブを差した上で importlib のファイルパス指定でロードし、
reciprocal_rank_fusion / dedup_by_filename の純粋ロジックのみを検証する。
スタブは exec_module 後に元へ復元し、他テストへ漏らさない。
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

SEARCH_PY = Path(__file__).resolve().parent.parent / "scripts" / "search" / "search.py"


def _stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def search_mod():
    keys = ("dotenv", "psycopg2", "psycopg2.sql", "voyageai")
    saved = {k: sys.modules.get(k) for k in keys}

    dotenv_stub = _stub("dotenv", load_dotenv=lambda *a, **k: False)
    psycopg2_stub = _stub("psycopg2")
    psycopg2_stub.sql = _stub("psycopg2.sql")
    psycopg2_stub.OperationalError = type("OperationalError", (Exception,), {})
    voyageai_stub = _stub("voyageai", Client=object)

    sys.modules["dotenv"] = dotenv_stub
    sys.modules["psycopg2"] = psycopg2_stub
    sys.modules["psycopg2.sql"] = psycopg2_stub.sql
    sys.modules["voyageai"] = voyageai_stub
    try:
        spec = importlib.util.spec_from_file_location("episodic_search_under_test", SEARCH_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


# ---------------------------------------------------------------- reciprocal_rank_fusion


def test_rrf_single_list_exact_scores(search_mod) -> None:
    s = search_mod.reciprocal_rank_fusion([["a", "b", "c"]], k=1)
    # rank は 1 始まり → 1/(k+rank)
    assert s == {"a": 1 / 2, "b": 1 / 3, "c": 1 / 4}


def test_rrf_default_k_is_60(search_mod) -> None:
    s = search_mod.reciprocal_rank_fusion([["x", "y"]])
    assert s["x"] == pytest.approx(1 / 61)
    assert s["y"] == pytest.approx(1 / 62)


def test_rrf_fuses_two_lists(search_mod) -> None:
    s = search_mod.reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=10)
    assert s["a"] == pytest.approx(1 / 11)                # list1 rank1
    assert s["b"] == pytest.approx(1 / 12 + 1 / 11)       # list1 rank2 + list2 rank1
    assert s["c"] == pytest.approx(1 / 12)                # list2 rank2
    # 両リストに現れる b が融合スコアで最上位
    assert max(s, key=s.get) == "b"


def test_rrf_higher_rank_scores_higher(search_mod) -> None:
    s = search_mod.reciprocal_rank_fusion([["first", "second", "third"]])
    assert s["first"] > s["second"] > s["third"]


def test_rrf_empty_inputs(search_mod) -> None:
    assert search_mod.reciprocal_rank_fusion([]) == {}
    assert search_mod.reciprocal_rank_fusion([[]]) == {}


# ---------------------------------------------------------------- dedup_by_filename


def _row(cid: str, fname: str) -> tuple:
    # by_id の tuple は (id, filename, chunk_text, sim) 形式（index[1] が filename）
    return (cid, fname, f"text-{cid}", 0.0)


def test_dedup_keeps_top_chunk_per_filename(search_mod) -> None:
    by_id = {
        "1": _row("1", "f1.md"),
        "2": _row("2", "f1.md"),  # 同一 filename → 除外
        "3": _row("3", "f2.md"),
        "4": _row("4", "f3.md"),
    }
    out = search_mod.dedup_by_filename(["1", "2", "3", "4"], by_id, limit=10)
    assert out == ["1", "3", "4"]


def test_dedup_respects_limit(search_mod) -> None:
    by_id = {
        "1": _row("1", "f1.md"),
        "2": _row("2", "f2.md"),
        "3": _row("3", "f3.md"),
    }
    assert search_mod.dedup_by_filename(["1", "2", "3"], by_id, limit=2) == ["1", "2"]


def test_dedup_preserves_input_order(search_mod) -> None:
    by_id = {
        "a": _row("a", "fa.md"),
        "b": _row("b", "fb.md"),
        "c": _row("c", "fa.md"),
    }
    assert search_mod.dedup_by_filename(["b", "a", "c"], by_id, limit=10) == ["b", "a"]


def test_dedup_empty(search_mod) -> None:
    assert search_mod.dedup_by_filename([], {}, limit=5) == []
