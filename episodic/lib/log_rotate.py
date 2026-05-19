"""ログファイルのサイズ超過時に gzip ローテーションする。

bash の lib/log_rotate.sh を Python 化したもの。

仕様:
- 閾値（既定 5MB / 環境変数 MEMORIES_LOG_ROTATE_BYTES）を超えていたら
  `<log>.YYYYMMDDHHMMSS.gz` に圧縮退避し active log を空にする
- 同一 prefix の .gz は世代数（既定 3 / 環境変数 MEMORIES_LOG_ROTATE_KEEP）で打ち切り、
  古いものから順に削除
- best effort（atomic 保証なし）
"""
from __future__ import annotations

import contextlib
import gzip
import os
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_THRESHOLD_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_KEEP_GENERATIONS = 3


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if not val or not val.isdigit():
        return default
    return int(val)


def rotate_log_if_needed(
    log_path: Path | str,
    threshold_bytes: int | None = None,
    keep_generations: int | None = None,
) -> bool:
    """サイズ超過時に gzip ローテーションする。実施したら True。

    引数で None を渡した場合は環境変数 / 既定値を使う。
    """
    log = Path(log_path)
    if threshold_bytes is None:
        threshold_bytes = _env_int("MEMORIES_LOG_ROTATE_BYTES", DEFAULT_THRESHOLD_BYTES)
    if keep_generations is None:
        keep_generations = _env_int("MEMORIES_LOG_ROTATE_KEEP", DEFAULT_KEEP_GENERATIONS)

    if not log.is_file():
        return False
    if threshold_bytes <= 0:
        return False
    try:
        size = log.stat().st_size
    except OSError:
        return False
    if size < threshold_bytes:
        return False

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rotated = log.with_name(f"{log.name}.{ts}.gz")

    if shutil.which("gzip") is None and not _python_gzip_available():
        return False

    try:
        with log.open("rb") as src, gzip.open(rotated, "wb") as dst:
            shutil.copyfileobj(src, dst)
    except OSError:
        with contextlib.suppress(OSError):
            rotated.unlink()
        return False

    try:
        log.write_bytes(b"")
    except OSError:
        return False

    if keep_generations > 0:
        _prune_old_generations(log, keep_generations)
    return True


def _python_gzip_available() -> bool:
    return True  # stdlib gzip は常に利用可能


def _prune_old_generations(log: Path, keep: int) -> None:
    parent = log.parent
    prefix = log.name + "."
    rotated = [
        p for p in parent.glob(f"{log.name}.*.gz")
        if p.name.startswith(prefix) and p.name.endswith(".gz")
    ]
    rotated.sort(key=lambda p: p.stat().st_mtime, reverse=True)  # 新しい順
    for victim in rotated[keep:]:
        with contextlib.suppress(OSError):
            victim.unlink()
