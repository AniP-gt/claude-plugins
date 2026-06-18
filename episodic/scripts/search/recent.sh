#!/usr/bin/env bash
# episodic-search/recent: memories/raw 配下を時系列で一覧する（セマンティック検索ではない）。
#
# kind 既定は session（過去のセッション要約）。--kind オプションで web / minutes / diary / all に切替可能。
#
# Usage:
#   recent.sh [--kind session|web|minutes|diary|all] [--top N] [--project NAME] [--days D] \
#             [--format markdown|json|paths]
#
# Defaults: --kind session, --top 10, --format markdown, 全プロジェクト, 全期間
#
# 出力フィールド: ended_at / title / project / tags / duration / path
# ファイル名先頭タイムスタンプ（HHMMSS）と日付ディレクトリで時系列ソートする。
# frontmatter は yaml ライブラリ非依存で先頭ブロックを行ベースに最小パースする。
#
# 副作用なし（読み取り専用）。
set -u

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"

KIND="session"
TOP=10
PROJECT=""
DAYS=""
FORMAT="markdown"

usage() {
    cat <<EOF >&2
Usage: $(basename "$0") [options]

  --kind KIND     session (default) | web | minutes | diary | all
  --top N         返す件数 (default: 10)
  --project NAME  指定 project の記録のみ抽出（kind=session で意味あり）
  --days D        過去 D 日以内のみ（日付ディレクトリ名で判定）
  --format        markdown (default) | json | paths
EOF
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --kind) KIND="$2"; shift 2 ;;
        --top) TOP="$2"; shift 2 ;;
        --project) PROJECT="$2"; shift 2 ;;
        --days) DAYS="$2"; shift 2 ;;
        --format) FORMAT="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

# kind 値とディレクトリ名は完全一致（session / web / minutes / diary）。
case "$KIND" in
    session|web|minutes|diary|all) ;;
    *) echo "Error: invalid --kind: $KIND" >&2; usage ;;
esac

# 全 kind は MEMORIES_DIR 配下。all は raw 直下を走査して全 kind をまとめる。
if [[ "$KIND" == "all" ]]; then
    RAW_DIR="$MEMORIES_DIR/raw"
else
    RAW_DIR="$MEMORIES_DIR/raw/$KIND"
fi

if [ ! -d "$RAW_DIR" ]; then
    echo "Error: raw dir not found: $RAW_DIR" >&2
    exit 2
fi

export MEMORIES_DIR RAW_DIR TOP PROJECT DAYS FORMAT KIND

python3 - <<'PY'
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

raw_dir = Path(os.environ["RAW_DIR"])
top = int(os.environ["TOP"])
project_filter = os.environ.get("PROJECT") or ""
days = os.environ.get("DAYS") or ""
fmt = os.environ.get("FORMAT", "markdown")

cutoff = None
if days:
    try:
        cutoff = date.today() - timedelta(days=int(days))
    except ValueError:
        print(f"Invalid --days: {days}", file=sys.stderr)
        sys.exit(2)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILE_RE = re.compile(r"^(\d{6})_.+\.md$")

def parse_frontmatter(path: Path) -> dict:
    fm: dict = {}
    try:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline()
            if first.strip() != "---":
                return fm
            for line in f:
                if line.strip() == "---":
                    break
                m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line.rstrip("\n"))
                if not m:
                    continue
                key, val = m.group(1), m.group(2).strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                fm[key] = val
    except OSError:
        pass
    return fm

def _collect_date_dirs(roots: list[Path]) -> dict[str, list[Path]]:
    """各 root 直下の YYYY-MM-DD ディレクトリを日付キーで集約する（cutoff 適用）。

    ファイル列挙はせずディレクトリ列挙のみ。複数 root（kind=all）は同日付をまとめる。
    """
    by_date: dict[str, list[Path]] = {}
    for root in roots:
        if not root.exists():
            continue
        for date_dir in root.iterdir():
            if not date_dir.is_dir() or not DATE_RE.match(date_dir.name):
                continue
            try:
                d = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if cutoff and d < cutoff:
                continue
            by_date.setdefault(date_dir.name, []).append(date_dir)
    return by_date


kind = os.environ.get("KIND", "session")
if kind == "all":
    roots = [raw_dir / sub for sub in ("session", "web", "minutes", "diary")]
else:
    # raw_dir は kind=all なら memories/raw、それ以外なら memories/raw/<kind>
    roots = [raw_dir]

date_dirs_by_date = _collect_date_dirs(roots)

# 日付ディレクトリを YYYY-MM-DD 降順に走査し、top 充足で打ち切る。
# 全日付の全ファイルを列挙→全ソートする旧実装に対し、古い日付のファイル列挙・
# frontmatter 読込を回避する。日付単位の前進なので結果は旧実装と一致する。
results = []
for date_str in sorted(date_dirs_by_date, reverse=True):
    # 同日付の全 root のファイルを集約し、HHMMSS 降順に整列する。
    # roots 順（session→web→minutes→diary）で append するため、同 HHMMSS の
    # 安定ソートでの並びは旧グローバルソートと一致する。
    day_entries: list[tuple[str, Path]] = []
    for date_dir in date_dirs_by_date[date_str]:
        for f in date_dir.iterdir():
            m = FILE_RE.match(f.name)
            if not m:
                continue
            day_entries.append((m.group(1), f))
    day_entries.sort(key=lambda x: x[0], reverse=True)

    for hhmmss, path in day_entries:
        if len(results) >= top:
            break
        fm = parse_frontmatter(path)
        if project_filter and fm.get("project", "") != project_filter:
            continue
        results.append({
            "date": date_str,
            "time": f"{hhmmss[0:2]}:{hhmmss[2:4]}:{hhmmss[4:6]}",
            "ended_at": fm.get("ended_at", ""),
            "started_at": fm.get("started_at", ""),
            "title": fm.get("title", path.stem),
            "project": fm.get("project", ""),
            "duration_minutes": fm.get("duration_minutes", ""),
            "tags": fm.get("tags", ""),
            "status": fm.get("status", ""),
            "path": str(path),
        })
    if len(results) >= top:
        break

if fmt == "json":
    print(json.dumps(results, ensure_ascii=False, indent=2))
elif fmt == "paths":
    for r in results:
        print(r["path"])
else:
    if not results:
        print("該当する記録なし")
    for i, r in enumerate(results, 1):
        when = r["ended_at"] or f"{r['date']} {r['time']}"
        dur = f"{r['duration_minutes']}分" if r["duration_minutes"] else "-"
        print(f"### {i}. {r['title']}  _(ended: {when}, {dur})_")
        print(f"- **project**: {r['project'] or '-'}")
        if r["tags"]:
            print(f"- **tags**: {r['tags']}")
        print(f"- **path**: `{r['path']}`")
        print()
PY
