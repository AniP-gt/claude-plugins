"""共通 fixture。HOME を tmp_path に強制隔離し、テスト実行が
~/.local/share/episodic/state/ingest-queue.jsonl など実ファイルを触らないようにする。

2026-05-15 の人物 Wiki 機能実装中に、`HOME=...` を bash 行頭で指定する経路で
HOME 上書きが伝播せず実 queue を汚染したインシデントが発生したため、テストは
必ず本 conftest 経由で HOME を tmp_path に固定する設計とする。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


WIKI_DIR = Path(__file__).resolve().parent.parent / "wiki"


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HOME を tmp_path に固定し、enqueue.py が書き込む state ディレクトリを隔離する。

    Returns:
        Path: tmp_path 配下にできる state ディレクトリ
        (~/.local/share/episodic/state 相当)
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows 互換 (CI 安全策)
    state_dir = tmp_path / ".local" / "share" / "episodic" / "state"
    return state_dir


@pytest.fixture
def fake_raw(tmp_path: Path) -> Path:
    """ダミーの minutes Raw を作る。enqueue.py は raw_path の存在チェックを行うため必須。"""
    raw_dir = tmp_path / "memories" / "raw" / "minutes" / "2026-05-15"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "000000_test.md"
    raw_path.write_text(
        "---\nkind: minutes\ndate: 2026-05-15\n---\n\n# テスト議事録\n",
        encoding="utf-8",
    )
    return raw_path


@pytest.fixture
def fake_diary_raw(tmp_path: Path) -> Path:
    """ダミーの diary Raw を作る。"""
    raw_dir = tmp_path / "memories" / "raw" / "diary" / "2026-05-15"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "000000_diary.md"
    raw_path.write_text(
        "---\nkind: diary\ndate: 2026-05-15\n---\n\n# 日記\n",
        encoding="utf-8",
    )
    return raw_path


@pytest.fixture
def enqueue_module(monkeypatch: pytest.MonkeyPatch):
    """wiki/enqueue.py を import 可能な状態で返す（単体関数テスト用）。

    パス追加だけで sys.modules キャッシュに頼らず、毎回フレッシュに import する。
    """
    monkeypatch.syspath_prepend(str(WIKI_DIR))
    # キャッシュを除去して fresh import
    sys.modules.pop("enqueue", None)
    import enqueue  # type: ignore[import-not-found]
    return enqueue
