"""session-source の元 JSONL snapshot 保存ヘルパ。

bash runner.sh の save_source_snapshot を Python 化。
- twin 双子側に既存があれば skip
- *.jsonl.zst → zstd 圧縮、失敗時は plain .jsonl にフォールバック
- *.jsonl    → 単純 cp
- 書き込みは .partial → rename の atomic 化
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import path_resolver as pr

DEFAULT_ZSTD_LEVEL = 9
ZSTD_LEVEL_ENV = "MEMORIES_SNAPSHOT_ZSTD_LEVEL"


def _zstd_level() -> int:
    """zstd 圧縮レベルを返す。

    テキスト JSONL では -19 と -9 の圧縮率差は小さいが、-19 は全コアで
    数十秒級のコストを要するため既定を 9 に下げる。環境変数
    MEMORIES_SNAPSHOT_ZSTD_LEVEL（範囲 1-19）で上書き可能。不正値は既定 9。
    """
    val = os.environ.get(ZSTD_LEVEL_ENV)
    if val and val.isdigit():
        n = int(val)
        if 1 <= n <= 19:
            return n
    return DEFAULT_ZSTD_LEVEL


class SnapshotResult:
    SKIP_NO_INPUT = "skip_no_input"
    SKIP_TRAVERSAL = "skip_traversal"
    SKIP_SOURCE_MISSING = "skip_source_missing"
    SKIP_ALREADY_EXISTS = "skip_already_exists"
    SKIP_TWIN_EXISTS = "skip_twin_exists"
    SKIP_BAD_EXT = "skip_bad_ext"
    SAVED = "saved"
    SAVED_FALLBACK = "saved_fallback"
    FAILED = "failed"


def _has_traversal(path_str: str) -> bool:
    parts = path_str.split("/")
    return ".." in parts


def save_source_snapshot(
    snapshot_path: Path | str | None,
    transcript_path: Path | str | None,
) -> str:
    """元 JSONL を snapshot_path に保存する。戻り値は SnapshotResult.*。

    呼び出し側はログに使う。
    """
    if not snapshot_path or not transcript_path:
        return SnapshotResult.SKIP_NO_INPUT

    snap = Path(snapshot_path)
    src = Path(transcript_path)

    if _has_traversal(str(snap)) or _has_traversal(str(src)):
        return SnapshotResult.SKIP_TRAVERSAL
    if not src.is_file():
        return SnapshotResult.SKIP_SOURCE_MISSING
    if snap.is_file():
        return SnapshotResult.SKIP_ALREADY_EXISTS

    try:
        twin = pr.twin_snapshot_path(snap)
    except Exception:
        twin = None
    if twin and twin.is_file():
        return SnapshotResult.SKIP_TWIN_EXISTS

    snap.parent.mkdir(parents=True, exist_ok=True)
    tmp = snap.with_name(snap.name + ".partial")
    try:
        tmp.unlink()
    except OSError:
        pass

    name = snap.name
    if name.endswith(".jsonl.zst"):
        if shutil.which("zstd"):
            try:
                subprocess.run(
                    ["zstd", "-q", f"-{_zstd_level()}", "-T0", "-o", str(tmp), str(src)],
                    check=True,
                    capture_output=True,
                )
            except (subprocess.SubprocessError, OSError):
                _cleanup(tmp)
                return _fallback_plain(snap, src)
        else:
            return _fallback_plain(snap, src)
    elif name.endswith(".jsonl"):
        try:
            shutil.copy2(str(src), str(tmp))
        except OSError:
            _cleanup(tmp)
            return SnapshotResult.FAILED
    else:
        return SnapshotResult.SKIP_BAD_EXT

    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    try:
        tmp.replace(snap)
    except OSError:
        _cleanup(tmp)
        return SnapshotResult.FAILED
    return SnapshotResult.SAVED


def _fallback_plain(snap: Path, src: Path) -> str:
    plain = Path(str(snap)[: -len(".zst")]) if snap.name.endswith(".zst") else snap
    plain_tmp = plain.with_name(plain.name + ".partial")
    try:
        shutil.copy2(str(src), str(plain_tmp))
        plain_tmp.chmod(0o600)
        plain_tmp.replace(plain)
        return SnapshotResult.SAVED_FALLBACK
    except OSError:
        _cleanup(plain_tmp)
        return SnapshotResult.FAILED


def _cleanup(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
