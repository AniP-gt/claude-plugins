"""Session レポート保存先パス解決器。

セッションメタから (report_path, is_staged) を返す。session（Claude Code セッション要約）
専用の保存先解決を担う。web / minutes は episodic-recording skill 側のスクリプトが直接組み立てる。

命名規則:
  HHMMSS_<host8>_<sid8>[__staged].md

  HHMMSS  : セッション開始時刻（local time）
  host8   : ホスト名 SHA-1 の先頭 8 文字。マシン跨ぎでの衝突防止
  sid8    : Claude Code session_id 先頭 8 文字
  __staged: fallback_dir に書く場合のみ付与。sync 時に外して正規パスへ移送

絶対衝突を防ぐためファイル名末尾の連番は採用しない（host8 + sid8 + HHMMSS で実質衝突ゼロ）。
万一既存ファイルがあれば、それは命名規則上ありえない異常状態として停止する。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import config as cfg


STAGED_SUFFIX = "__staged"


def _format_basename(time_str: str, host8: str, sid8: str, staged: bool) -> str:
    suffix = STAGED_SUFFIX if staged else ""
    return f"{time_str}_{host8}_{sid8}{suffix}.md"


def to_normal_basename(staged_basename: str) -> str:
    """staging のベース名から __staged サフィックスを取り除く。"""
    if not staged_basename.endswith(f"{STAGED_SUFFIX}.md"):
        return staged_basename
    return staged_basename[: -len(f"{STAGED_SUFFIX}.md")] + ".md"


def resolve_report_path(started_at_iso: str, session_id: str) -> tuple[Path, bool]:
    """セッション開始 ISO8601 と session_id から (report_path, is_staged) を返す。

    raw_root は config.effective_raw_root() で決定:
      - マウント成立: <memories_dir>/raw/session/YYYY-MM-DD/<basename>.md
      - 未成立      : <fallback_dir>/YYYY-MM-DD/<basename>__staged.md

    マウント成立時のディレクトリ階層 raw/session/YYYY-MM-DD/ は recording が常に作成する。
    fallback_dir 直下にも YYYY-MM-DD/ を作り、staging→正規への移送を 1:1 で対応付けやすくする。
    """
    started_dt = datetime.fromisoformat(started_at_iso.replace("Z", "+00:00")).astimezone()
    date_dir = started_dt.strftime("%Y-%m-%d")
    time_str = started_dt.strftime("%H%M%S")
    host8 = cfg.host_hash()
    sid8 = (session_id or "unknown00")[:8]

    raw_root, is_staged = cfg.effective_raw_root()
    basename = _format_basename(time_str, host8, sid8, staged=is_staged)
    report_dir = raw_root / date_dir
    return report_dir / basename, is_staged


def map_staged_to_normal(staged_path: Path, memories_dir: Path) -> Path:
    """staging 上の絶対パスを、正規 memories_dir/raw/session 配下の対応パスへ写像する。

    fallback_dir 配下の構造 `<fallback_dir>/YYYY-MM-DD/<basename>__staged.md` を
    `<memories_dir>/raw/session/YYYY-MM-DD/<basename>.md` へ変換する。
    """
    date_dir = staged_path.parent.name
    normal_basename = to_normal_basename(staged_path.name)
    return memories_dir / "raw" / "session" / date_dir / normal_basename


def _format_snapshot_basename(time_str: str, host8: str, sid8: str, staged: bool, ext: str) -> str:
    suffix = STAGED_SUFFIX if staged else ""
    return f"{time_str}_{host8}_{sid8}{suffix}{ext}"


def _snapshot_ext(use_zstd: bool) -> str:
    return ".jsonl.zst" if use_zstd else ".jsonl"


def to_normal_snapshot_basename(staged_basename: str) -> str:
    """staging snapshot のベース名から __staged サフィックスを取り除く。"""
    for ext in (".jsonl.zst", ".jsonl"):
        suffix = f"{STAGED_SUFFIX}{ext}"
        if staged_basename.endswith(suffix):
            return staged_basename[: -len(suffix)] + ext
    return staged_basename


def resolve_snapshot_path(started_at_iso: str, session_id: str,
                          use_zstd: bool) -> tuple[Path, bool]:
    """セッション開始 ISO8601 と session_id から元 JSONL snapshot の (path, is_staged) を返す。

    snapshot root は config.effective_snapshot_root() で決定:
      - マウント成立: <memories_dir>/raw/session-source/YYYY-MM-DD/<basename>.jsonl[.zst]
      - 未成立      : <fallback_dir>/session-source/YYYY-MM-DD/<basename>__staged.jsonl[.zst]

    時刻・host8・sid8 は session レポートと同じ規則で算出する。同じ session を再生成しても
    snapshot は不変なので、命名衝突は命名規則上ありえないが、衝突時は呼び出し側で扱う。
    """
    started_dt = datetime.fromisoformat(started_at_iso.replace("Z", "+00:00")).astimezone()
    date_dir = started_dt.strftime("%Y-%m-%d")
    time_str = started_dt.strftime("%H%M%S")
    host8 = cfg.host_hash()
    sid8 = (session_id or "unknown00")[:8]

    snap_root, is_staged = cfg.effective_snapshot_root()
    ext = _snapshot_ext(use_zstd)
    basename = _format_snapshot_basename(time_str, host8, sid8, staged=is_staged, ext=ext)
    return snap_root / date_dir / basename, is_staged


def map_snapshot_staged_to_normal(staged_path: Path, memories_dir: Path) -> Path:
    """staging snapshot の絶対パスを、正規 memories_dir/raw/session-source 配下へ写像する。

    `<fallback_dir>/session-source/YYYY-MM-DD/<basename>__staged.jsonl[.zst]` を
    `<memories_dir>/raw/session-source/YYYY-MM-DD/<basename>.jsonl[.zst]` へ変換する。
    """
    date_dir = staged_path.parent.name
    normal_basename = to_normal_snapshot_basename(staged_path.name)
    return memories_dir / "raw" / "session-source" / date_dir / normal_basename
