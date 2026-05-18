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


def twin_report_path(report_path: Path) -> Path | None:
    """report_path (session .md) の "双子" を返す: staging ↔ memory の対側パス。

    snapshot 同様、finalize が複数回走った際に staging/memory 両側に同 session_id の
    .md が出来てしまう状況を防ぐため、runner.sh の Codex 起動前チェックで使う。
    判定できない場合は None を返す。
    """
    name = report_path.name
    date_dir = report_path.parent.name

    if name.endswith(f"{STAGED_SUFFIX}.md"):
        memories_dir = cfg.resolve_memories_dir()
        return map_staged_to_normal(report_path, memories_dir)

    if name.endswith(".md"):
        base = name[: -len(".md")]
        staged_basename = f"{base}{STAGED_SUFFIX}.md"
        return cfg.resolve_fallback_dir() / date_dir / staged_basename
    return None


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


def twin_snapshot_path(snapshot_path: Path) -> Path | None:
    """snapshot_path の "双子" を返す: staging ↔ memory の対側パス。

    save_source_snapshot は finalize が走った時点のマウント状態だけ見て保存先を決める。
    1 セッションが複数回 finalize される間にマウント状態が揺らぐと、同じ session_id で
    staging と memory の両側に snapshot が生成され sync-pending が永続 COLLISION を起こす。
    重複チェックを片側だけでなく双子側にも広げるための補助関数。

    判定できない場合は None を返す。
    """
    name = snapshot_path.name
    date_dir = snapshot_path.parent.name

    if name.endswith(f"{STAGED_SUFFIX}.jsonl.zst") or name.endswith(f"{STAGED_SUFFIX}.jsonl"):
        memories_dir = cfg.resolve_memories_dir()
        return map_snapshot_staged_to_normal(snapshot_path, memories_dir)

    for ext in (".jsonl.zst", ".jsonl"):
        if name.endswith(ext):
            base = name[: -len(ext)]
            staged_basename = f"{base}{STAGED_SUFFIX}{ext}"
            return cfg.resolve_fallback_dir() / "session-source" / date_dir / staged_basename
    return None
