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


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WIKI_DIR = REPO_ROOT / "wiki"


@pytest.fixture(autouse=True)
def _block_real_side_effects(monkeypatch: pytest.MonkeyPatch):
    """テストから実環境への副作用（macOS 通知・実 codex 起動）を多層で遮断する。

    2026-06-10 のインシデント: test_sync_pending が実 _kick_wiki_runner 経由で
    detached の kick_runner → wiki_runner → 実 codex（401 で 90 秒リトライ）を起動し、
    テスト終了の約 2 分後に「Episodic Wiki 失敗」の macOS 通知を毎回 2 件発火していた。
    直接原因は当該テストでモック済みだが、将来のテストが detached チェーンを
    取りこぼしても実害が出ないよう、ここで包括的に防御する。

    - MEMORIES_NOTIFICATION_LEVEL=none: 漏れた detached 子プロセスにも env で伝播し
      通知を抑止する（v3.14.0 の notification_level ゲーティングが効く）
    - CODEX_BINARY=/usr/bin/false: 漏れた子プロセスが codex を解決しても即 rc=1 で
      終了し、実 API 呼び出し（トークン消費）を防ぐ
    - OsascriptNotifier.notify: in-process の osascript 発火を no-op 化
      （test_notify.py は元実装を自前で復元して検証する）
    """
    monkeypatch.setenv("MEMORIES_NOTIFICATION_LEVEL", "none")
    monkeypatch.setenv("CODEX_BINARY", "/usr/bin/false")
    from lib.notify import OsascriptNotifier

    monkeypatch.setattr(OsascriptNotifier, "notify", lambda self, *a, **k: None)


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
