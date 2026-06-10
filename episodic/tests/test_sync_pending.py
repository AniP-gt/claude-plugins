"""bin/sync_pending.py の統合テスト。"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))

from lib.notify import NullNotifier  # noqa: E402


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """MEMORIES_DIR / FALLBACK_DIR / HOME を tmp に固定。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    mem = tmp_path / "memory"
    fb = tmp_path / "staging"
    mem.mkdir()
    fb.mkdir()
    monkeypatch.setenv("MEMORIES_DIR", str(mem))
    monkeypatch.setenv("MEMORIES_FALLBACK_DIR", str(fb))
    # canary を置いてマウント成立扱い
    (mem / ".mount-canary").write_text("ok")
    # config を再ロードさせるため lru_cache をクリア
    from lib import config
    config.load_config.cache_clear()
    return {"home": home, "memories": mem, "fallback": fb}


@pytest.fixture
def sync_pending_mod(monkeypatch: pytest.MonkeyPatch):
    sys.modules.pop("sync_pending", None)
    mod = importlib.import_module("sync_pending")
    # 実 _kick_wiki_runner は detached の kick_runner → wiki_runner → 実 codex 起動 →
    # macOS 失敗通知（テスト終了の数分後）まで漏れるため、必ず無効化する。
    # 呼び出し有無は mod._kick_calls で検証できる。
    mod._kick_calls = []
    monkeypatch.setattr(
        mod, "_kick_wiki_runner", lambda *a, **k: mod._kick_calls.append((a, k))
    )
    return mod


def test_no_canary_skips(env, monkeypatch, sync_pending_mod):
    (env["memories"] / ".mount-canary").unlink()
    from lib import config
    config.load_config.cache_clear()
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0


def test_no_staged_files_skips(env, sync_pending_mod):
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0


def test_normal_move(env, sync_pending_mod):
    src = env["fallback"] / "2026-05-19" / "010203_abcd1234_sess0001__staged.md"
    src.parent.mkdir(parents=True)
    src.write_text("---\nkind: session\n---\n# body\n")
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0
    dst = env["memories"] / "raw" / "session" / "2026-05-19" / "010203_abcd1234_sess0001.md"
    assert dst.is_file()
    assert not src.exists()


def test_duplicate_hash_dedupes(env, sync_pending_mod):
    src = env["fallback"] / "2026-05-19" / "010203_a_b__staged.md"
    src.parent.mkdir(parents=True)
    src.write_text("same")
    dst_dir = env["memories"] / "raw" / "session" / "2026-05-19"
    dst_dir.mkdir(parents=True)
    (dst_dir / "010203_a_b.md").write_text("same")
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0
    assert not src.exists()
    assert (dst_dir / "010203_a_b.md").read_text() == "same"


def test_collision_resolution_src_wins(env, sync_pending_mod):
    src = env["fallback"] / "2026-05-19" / "010203_a_b__staged.md"
    src.parent.mkdir(parents=True)
    src.write_text("---\nkind: session\nended_at: 2026-05-19T10:00:00Z\n---\nnew\n")
    dst_dir = env["memories"] / "raw" / "session" / "2026-05-19"
    dst_dir.mkdir(parents=True)
    dst = dst_dir / "010203_a_b.md"
    dst.write_text("---\nkind: session\nended_at: 2026-05-19T09:00:00Z\n---\nold\n")
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0
    assert dst.read_text().startswith("---\nkind: session\nended_at: 2026-05-19T10:00:00Z")
    # 旧 dst が revision に退避
    revs = list(dst_dir.glob("*__r*.md"))
    assert len(revs) == 1


def test_collision_unresolvable(env, sync_pending_mod):
    src = env["fallback"] / "2026-05-19" / "x__staged.md"
    src.parent.mkdir(parents=True)
    # frontmatter なし → tiebreaker できない
    src.write_text("AAA")
    dst_dir = env["memories"] / "raw" / "session" / "2026-05-19"
    dst_dir.mkdir(parents=True)
    (dst_dir / "x.md").write_text("BBB")
    # mtime を揃える
    ts = 1700000000
    os.utime(src, (ts, ts))
    os.utime(dst_dir / "x.md", (ts, ts))
    rc = sync_pending_mod.run(notifier=NullNotifier())
    assert rc == 0
    # 解決不能 → staging 保全
    assert src.exists()
