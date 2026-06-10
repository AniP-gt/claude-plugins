"""session/retry_queue.py の単体テスト。

HOME を tmp_path に隔離し、retry_queue モジュールを reload して
STATE_DIR / QUEUE_PATH / DEAD_LETTER_PATH / LOCK_DIR を tmp 配下へ再計算させる
（既存 test_retry_pending.py / test_mount_memory_share.py と同じイディオム）。
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "session"))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows 互換 (CI 安全策)
    sys.modules.pop("retry_queue", None)
    m = importlib.import_module("retry_queue")
    importlib.reload(m)
    return m


def _upsert_args(**over) -> argparse.Namespace:
    base = dict(
        session_id="s",
        cwd="",
        transcript="",
        first_ts="",
        report_path="",
        is_staged=False,
        reason="unknown",
    )
    base.update(over)
    return argparse.Namespace(**base)


# --------------------------------------------------------------------------- #
# _acquire_lock
# --------------------------------------------------------------------------- #
def test_acquire_lock_basic(mod) -> None:
    mod._acquire_lock()
    try:
        assert mod.LOCK_DIR.is_dir()
        assert (mod.LOCK_DIR / "pid").read_text(encoding="utf-8").strip() == str(os.getpid())
    finally:
        mod._release_lock()
    assert not mod.LOCK_DIR.exists()


def test_acquire_lock_timeout_when_held_by_live_pid(mod, monkeypatch) -> None:
    """生存 PID が握る非 stale ロックに対しては待機の末タイムアウトする。"""
    mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
    mod.LOCK_DIR.mkdir(parents=True)
    # 自プロセス PID は生存中なので stale 判定されない
    (mod.LOCK_DIR / "pid").write_text(str(os.getpid()), encoding="utf-8")
    # ループを即座にデッドライン超過させてテストを高速化
    monkeypatch.setattr(mod, "LOCK_TIMEOUT_SEC", 0)
    with pytest.raises(TimeoutError):
        mod._acquire_lock()
    # 既存ロックは奪取されていない（PID は元のまま）
    assert (mod.LOCK_DIR / "pid").read_text(encoding="utf-8").strip() == str(os.getpid())


def test_acquire_lock_reaps_stale_dead_pid(mod) -> None:
    """死んだ PID(ESRCH) を握るロックは奪取される。"""
    mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
    mod.LOCK_DIR.mkdir(parents=True)
    (mod.LOCK_DIR / "pid").write_text("999999\n", encoding="utf-8")  # 不在 PID 想定
    mod._acquire_lock()
    try:
        assert (mod.LOCK_DIR / "pid").read_text(encoding="utf-8").strip() == str(os.getpid())
    finally:
        mod._release_lock()


def test_acquire_lock_reaps_stale_by_age(mod) -> None:
    """PID 不明かつ mtime が LOCK_STALE_SEC を超えるロックは age 判定で奪取される。"""
    mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
    mod.LOCK_DIR.mkdir(parents=True)
    (mod.LOCK_DIR / "pid").write_text("0\n", encoding="utf-8")  # old_pid=0 → kill 判定スキップ
    old = time.time() - (mod.LOCK_STALE_SEC + 60)
    os.utime(mod.LOCK_DIR, (old, old))
    mod._acquire_lock()
    try:
        assert (mod.LOCK_DIR / "pid").read_text(encoding="utf-8").strip() == str(os.getpid())
    finally:
        mod._release_lock()


# --------------------------------------------------------------------------- #
# _read_entries（破損行の現挙動固定）
# --------------------------------------------------------------------------- #
def test_read_entries_missing_file_returns_empty(mod) -> None:
    assert not mod.QUEUE_PATH.exists()
    assert mod._read_entries() == []


def test_read_entries_silently_skips_corrupt_lines(mod) -> None:
    """破損行（不正 JSON）が黙ってスキップされる現挙動を固定する。

    要確認挙動:
      - 不正 JSON 行は JSONDecodeError で握り潰され、当該 session のリトライが消失する
        （ここでは session_id="ccc_corrupt" のエントリが復元されない＝リトライ消失リスクの実証）。
      - 一方で「型不一致だが JSON として妥当」な行（例: 数値 42）は **スキップされず**
        非 dict 値としてそのまま entries に混入する（後段が e.get(...) 前提のため
        AttributeError を誘発しうる）。
    """
    mod.QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    good_a = {"session_id": "aaa", "attempt_count": 1}
    good_b = {"session_id": "bbb", "attempt_count": 2}
    lines = [
        json.dumps(good_a),
        '{"session_id": "ccc_corrupt", "attempt_count": 1',  # 閉じ括弧欠落 → 不正 JSON
        "",                                                  # 空行 → スキップ
        "   ",                                               # 空白行 → スキップ
        "42",                                                # 妥当 JSON だが非 dict
        json.dumps(good_b),
    ]
    mod.QUEUE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    entries = mod._read_entries()

    # 残存は good_a, 42(非dict), good_b の 3 件。不正 JSON 行の 1 件のみが消失。
    assert len(entries) == 3
    dict_ids = {e["session_id"] for e in entries if isinstance(e, dict)}
    assert dict_ids == {"aaa", "bbb"}
    # リトライ消失リスクの実証: 不正 JSON だった ccc_corrupt は復元されない
    assert "ccc_corrupt" not in dict_ids
    # 型不一致リスクの実証: 数値 42 はスキップされず非 dict としてリストに混入する
    assert 42 in entries
    assert any(not isinstance(e, dict) for e in entries)


# --------------------------------------------------------------------------- #
# cmd_upsert
# --------------------------------------------------------------------------- #
def test_upsert_inserts_new_entry(mod) -> None:
    sid = str(uuid.uuid4())
    rc = mod.cmd_upsert(_upsert_args(
        session_id=sid, cwd="/work", transcript="/t.jsonl",
        first_ts="2026-06-10T00:00:00", report_path="/r.md",
        is_staged=True, reason="usage_limit",
    ))
    assert rc == 0
    entries = mod._read_entries()
    assert len(entries) == 1
    e = entries[0]
    assert e["session_id"] == sid
    assert e["cwd"] == "/work"
    assert e["transcript_path"] == "/t.jsonl"
    assert e["report_path"] == "/r.md"
    assert e["is_staged"] is True
    assert e["failure_reason"] == "usage_limit"
    assert e["attempt_count"] == 1
    assert e["first_failed_at"] == e["last_attempted_at"]


def test_upsert_updates_existing_increments_attempt(mod) -> None:
    sid = str(uuid.uuid4())
    mod.cmd_upsert(_upsert_args(session_id=sid, cwd="/old", reason="usage_limit"))
    first = mod._read_entries()[0]
    assert first["attempt_count"] == 1
    first_failed_at = first["first_failed_at"]

    mod.cmd_upsert(_upsert_args(session_id=sid, cwd="/new", reason="network", is_staged=True))
    entries = mod._read_entries()
    # session_id は単一のまま（重複追加されない）
    assert len(entries) == 1
    e = entries[0]
    assert e["attempt_count"] == 2
    assert e["cwd"] == "/new"
    assert e["failure_reason"] == "network"
    assert e["is_staged"] is True
    # first_failed_at は初回値を保持する
    assert e["first_failed_at"] == first_failed_at


def test_upsert_distinct_sessions_kept_separately(mod) -> None:
    sid1 = str(uuid.uuid4())
    sid2 = str(uuid.uuid4())
    assert sid1 != sid2
    mod.cmd_upsert(_upsert_args(session_id=sid1, cwd="/a"))
    mod.cmd_upsert(_upsert_args(session_id=sid2, cwd="/b"))
    entries = mod._read_entries()
    assert {e["session_id"] for e in entries} == {sid1, sid2}
    assert {e["cwd"] for e in entries} == {"/a", "/b"}


# --------------------------------------------------------------------------- #
# cmd_remove / cmd_list
# --------------------------------------------------------------------------- #
def test_remove_clears_last_entry_leaves_empty_file(mod) -> None:
    sid = str(uuid.uuid4())
    mod.cmd_upsert(_upsert_args(session_id=sid))
    rc = mod.cmd_remove(argparse.Namespace(session_id=sid))
    assert rc == 0
    # 最後の 1 件削除後も 0 byte ファイルとして残す現挙動
    assert mod.QUEUE_PATH.exists()
    assert mod.QUEUE_PATH.read_text(encoding="utf-8") == ""
    assert mod._read_entries() == []


def test_remove_nonexistent_is_noop(mod) -> None:
    rc = mod.cmd_remove(argparse.Namespace(session_id=str(uuid.uuid4())))
    assert rc == 0
    # エントリが無ければ書き込みも発生せずファイルは作られない
    assert not mod.QUEUE_PATH.exists()


def test_list_filters_by_max_attempts(mod, capsys) -> None:
    low = str(uuid.uuid4())
    high = str(uuid.uuid4())
    mod.cmd_upsert(_upsert_args(session_id=low))           # attempt_count=1
    for _ in range(3):
        mod.cmd_upsert(_upsert_args(session_id=high))      # attempt_count=3
    rc = mod.cmd_list(argparse.Namespace(max_attempts=2))
    assert rc == 0
    out_lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    listed_ids = {json.loads(l)["session_id"] for l in out_lines}
    # attempt_count(3) > max_attempts(2) の high は除外され、low のみ出力される
    assert listed_ids == {low}


# --------------------------------------------------------------------------- #
# cmd_promote_dead_letter
# --------------------------------------------------------------------------- #
def test_promote_dead_letter_moves_entry(mod) -> None:
    sid = str(uuid.uuid4())
    mod.cmd_upsert(_upsert_args(session_id=sid, cwd="/x", reason="usage_limit"))
    rc = mod.cmd_promote_dead_letter(argparse.Namespace(session_id=sid))
    assert rc == 0
    # active キューからは除外される
    assert mod._read_entries() == []
    # dead-letter ファイルに promoted_at 付きで追記される
    assert mod.DEAD_LETTER_PATH.exists()
    dl_lines = [l for l in mod.DEAD_LETTER_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(dl_lines) == 1
    dl = json.loads(dl_lines[0])
    assert dl["session_id"] == sid
    assert "promoted_at" in dl


def test_promote_dead_letter_unknown_session_noop(mod) -> None:
    rc = mod.cmd_promote_dead_letter(argparse.Namespace(session_id=str(uuid.uuid4())))
    assert rc == 0
    # 対象不在では dead-letter ファイルは作られない
    assert not mod.DEAD_LETTER_PATH.exists()


# --------------------------------------------------------------------------- #
# atomic rewrite（tmp ファイル残存時の挙動）
# --------------------------------------------------------------------------- #
def test_write_entries_empty_writes_zero_byte_file(mod) -> None:
    mod.QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    mod._write_entries([])
    assert mod.QUEUE_PATH.exists()
    assert mod.QUEUE_PATH.read_text(encoding="utf-8") == ""


def test_upsert_overwrites_stale_tmp_file(mod) -> None:
    """書き込み途中クラッシュを模した残存 .tmp があっても upsert は正しく完了する。"""
    sid = str(uuid.uuid4())
    mod.QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = mod.QUEUE_PATH.with_suffix(mod.QUEUE_PATH.suffix + ".tmp")
    tmp.write_text("garbage-half-written-line-without-newline", encoding="utf-8")

    mod.cmd_upsert(_upsert_args(session_id=sid, cwd="/work"))

    entries = mod._read_entries()
    assert len(entries) == 1
    assert entries[0]["session_id"] == sid
    # os.replace により tmp は最終ファイルへ消費され残存しない
    assert not tmp.exists()
