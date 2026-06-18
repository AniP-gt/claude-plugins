#!/usr/bin/env python3
"""Raw レポート（kind: session/web/minutes/diary）または派生ジョブ
（kind: people_extract/person）1 件分のエントリを ingest-queue.jsonl に追記する。

呼び出し側（runner.sh / fetch-jina.sh / save.sh）が保存成功直後に実行。
同一 (raw_path, kind, slug) の pending エントリが既にあれば追記をスキップする（dedupe）。
追記前に flock(LOCK_EX) を取って read→check→append を直列化し、
複数プロセス並行 enqueue でも重複を生まない。

minutes / diary を enqueue したときは、人物抽出ジョブ（kind: people_extract）も
同じ raw_path で自動的に積まれる。本体 Wiki 更新と人物抽出は wiki-runner 側で
並列実行されるため、片方が失敗しても他方には波及しない。

kind は引数 --kind 優先、未指定時は raw_path から自動推定する
（`raw/session/` `raw/web/` `raw/minutes/` `raw/diary/` のいずれを含むか）。

person kind 用の追加引数:
    --name <表示名> --slug <slug> --aliases <カンマ区切り>
    --context <短い文脈> --source-kind minutes|diary
  これらは wiki-runner の people_extract ジョブから呼ばれる内部経路で使用される。

Usage:
    enqueue.py <raw_path> [--kind session|web|minutes|diary|people_extract|person]
               [--memories-dir PATH]
               [--name NAME --slug SLUG --source-kind minutes|diary
                --aliases A,B,C --context TEXT]  # kind=person のみ

終了コード:
    0 → 追記成功 または 重複スキップ（どちらも正常終了）
    2 → raw_path が存在しない（kind=person は source_raw として参照するため要存在）
    3 → kind=person で必須引数が不足

Stdout: 追記した行（デバッグ用）。重複スキップ時は "skip: ..." を stderr に出力。
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


# slug に許可する文字: ASCII 英数字 / アンダースコア / ハイフン
# + Hiragana / Katakana / CJK Unified Ideographs / CJK Ext-A / 々 / ー
_SLUG_ALLOWED = re.compile(
    r"[^0-9A-Za-z_\-぀-ゟ゠-・ヽ-ヿー々㐀-䶿一-鿿]"
)


def sanitize_slug(slug: str) -> str:
    """Codex 出力の slug をファイル名・ファイルパス・sed 区切り文字に対して安全な形に正規化する。

    許可文字以外（パス区切り `/`、sed 区切り `|`、改行、タブ、`.`、空白等）は除去する。
    NFC 正規化後、先頭の `-` / `.` を剥がし、長さ上限 96 文字でクリップする。
    """
    if not slug:
        return ""
    normalized = unicodedata.normalize("NFC", slug)
    cleaned = _SLUG_ALLOWED.sub("", normalized)
    cleaned = cleaned.lstrip(".-")
    return cleaned[:96]


# CLI から --kind 引数で指定できる kind 一覧。
USER_KINDS = ("session", "web", "minutes", "diary")
# 内部派生 kind（wiki-runner の people_extract ジョブから enqueue.py が呼ばれる）。
INTERNAL_KINDS = ("people_extract", "person", "org")
VALID_KINDS = USER_KINDS + INTERNAL_KINDS

# org エントリの category 選択肢。
ORG_CATEGORIES = ("company", "hospital", "government", "academic", "other")


def detect_kind(raw_path: Path) -> str:
    """パスから kind を推定する。判別不能時は 'session' にフォールバック。

    パス例 `<memories_dir>/raw/session/YYYY-MM-DD/file.md` から `session` を返す。
    kind 値とディレクトリ名は完全一致（session / web / minutes / diary）。
    diary も memories_dir 配下（`<memories_dir>/raw/diary/`）に保存される。
    `raw/<kind>/` 構造を見るだけのルート非依存判定なので全 kind で機能する。
    """
    parts = raw_path.parts
    for i, p in enumerate(parts):
        if p == "raw" and i + 1 < len(parts):
            nxt = parts[i + 1]
            if nxt in USER_KINDS:
                return nxt
    return "session"


def _entry_identity(entry: dict) -> tuple[str, str, str]:
    """dedupe 判定のための identity tuple を返す。

    person / org kind は同じ raw_path に対して複数 slug が共存し得るので
    slug を識別子に含める。それ以外の kind は slug 空文字。
    """
    return (
        entry.get("raw_path", ""),
        entry.get("kind", ""),
        entry.get("slug", "") if entry.get("kind") in ("person", "org") else "",
    )


def _append_entry(queue_path: Path, entry: dict) -> bool:
    """queue ファイルに 1 エントリを排他追記する。dedupe ヒット時は False を返す。"""
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    target_id = _entry_identity(entry)
    # 走査効率化: raw_path の JSON 表現で行をリテラル前置フィルタし、
    # raw_path が一致し得ない行は json.loads を省く。identity の第一要素は
    # raw_path なので、token を含まない行は重複になり得ない。JSON エンコード形で
    # 比較するためエスケープ差異による取りこぼしは生じず、重複判定基準は不変。
    raw_path_token = json.dumps(entry.get("raw_path", ""), ensure_ascii=False)
    with queue_path.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        for existing in f:
            if raw_path_token not in existing:
                continue
            existing = existing.strip()
            if not existing:
                continue
            try:
                d = json.loads(existing)
            except json.JSONDecodeError:
                continue
            if d.get("status") != "pending":
                continue
            if _entry_identity(d) == target_id:
                return False
        f.seek(0, os.SEEK_END)
        f.write(line)
    print(line, end="")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("raw_path", help="生成された Raw レポートの絶対パス（kind=person では source raw のパス）")
    p.add_argument(
        "--kind",
        choices=VALID_KINDS,
        default=None,
        help="kind を明示指定（未指定時は raw_path から自動推定）",
    )
    p.add_argument(
        "--memories-dir",
        default=Path(os.environ.get("MEMORIES_DIR", "/Volumes/memory")),
        type=Path,
    )
    # kind=person 用の追加メタ。それ以外の kind では無視する。
    p.add_argument("--name", default=None, help="kind=person: 表示名")
    p.add_argument("--slug", default=None, help="kind=person: slug（ファイル名に使用）")
    p.add_argument("--aliases", default="", help="kind=person: 別名（カンマ区切り）")
    p.add_argument("--context", default="", help="kind=person: source raw での言及文脈")
    p.add_argument(
        "--source-kind",
        choices=("minutes", "diary"),
        default=None,
        help="kind=person/org: 言及元 Raw の kind",
    )
    p.add_argument(
        "--category",
        choices=ORG_CATEGORIES,
        default="other",
        help="kind=org: 組織のカテゴリ（company|hospital|government|academic|other）",
    )
    args = p.parse_args()

    raw_path = Path(args.raw_path).resolve()
    if not raw_path.exists():
        print(f"raw not found: {raw_path}", file=sys.stderr)
        return 2

    kind = args.kind or detect_kind(raw_path)
    if kind not in VALID_KINDS:
        print(f"invalid kind: {kind}", file=sys.stderr)
        return 2

    if kind in ("person", "org"):
        if not args.name or not args.slug or not args.source_kind:
            print(
                f"kind={kind} requires --name, --slug, --source-kind",
                file=sys.stderr,
            )
            return 3
        sanitized = sanitize_slug(args.slug)
        if not sanitized:
            print(
                f"kind={kind}: slug becomes empty after sanitize: original={args.slug!r}",
                file=sys.stderr,
            )
            return 3
        if sanitized != args.slug:
            print(
                f"info: slug sanitized: {args.slug!r} -> {sanitized!r}",
                file=sys.stderr,
            )
        args.slug = sanitized

    # state は ~/.local/share/episodic/state に永続化（OS 再起動でも pending が残る）。
    state_dir = Path.home() / ".local" / "share" / "episodic" / "state"
    queue_path = state_dir / "ingest-queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now().astimezone().isoformat(timespec="seconds")

    base_entry = {
        "raw_path": str(raw_path),
        "kind": kind,
        "enqueued_at": now_iso,
        "status": "pending",
    }
    if kind == "person":
        aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
        base_entry.update(
            {
                "name": args.name,
                "slug": args.slug,
                "aliases": aliases,
                "context": args.context,
                "source_kind": args.source_kind,
            }
        )
    elif kind == "org":
        aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
        base_entry.update(
            {
                "name": args.name,
                "slug": args.slug,
                "aliases": aliases,
                "category": args.category,
                "context": args.context,
                "source_kind": args.source_kind,
            }
        )

    appended = _append_entry(queue_path, base_entry)
    if not appended:
        print(
            f"skip: duplicate pending entry for kind={kind} raw={raw_path}",
            file=sys.stderr,
        )

    # minutes / diary は人物抽出ジョブを同 raw_path で自動連動 enqueue する。
    # 本体 Wiki 更新と並列実行され、片方の失敗は他方に波及しない。
    if kind in ("minutes", "diary"):
        people_extract_entry = {
            "raw_path": str(raw_path),
            "kind": "people_extract",
            "source_kind": kind,
            "enqueued_at": now_iso,
            "status": "pending",
        }
        if not _append_entry(queue_path, people_extract_entry):
            print(
                f"skip: duplicate pending people_extract for raw={raw_path}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
