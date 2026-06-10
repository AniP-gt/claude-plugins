"""wiki/index.md を再生成し、references / minutes / diary の source_count を補正する。

bash wiki-runner.sh 末尾の Python ブロックを `wiki_index` モジュールに切り出したもの。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _count_md_files(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0
    return sum(1 for p in dir_path.rglob("*.md") if not p.name.startswith("."))


def _mention_count(target: Path) -> int:
    """frontmatter から mention_count を取り出す。フィールド不在なら 0。"""
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return 0
    if not text.startswith("---\n"):
        return 0
    end = text.find("\n---", 4)
    if end == -1:
        return 0
    for ln in text[4:end].split("\n"):
        m = re.match(r"^mention_count\s*:\s*(\d+)", ln)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
    return 0


# people/orgs 双方の mention_count 集計に使う汎用関数。
# 既存呼び出し互換のため _people_mention_count を別名として残す。
_people_mention_count = _mention_count


def enforce_source_count(target: Path, expected: int) -> None:
    """frontmatter の source_count フィールドを expected で上書きする。

    フィールドが無ければ追加、frontmatter 自体が無いファイルは何もしない。
    """
    if not target.exists():
        return
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return
    if not text.startswith("---\n"):
        return
    end = text.find("\n---", 4)
    if end == -1:
        return
    fm_block = text[4:end]
    body = text[end:]
    fm_lines = fm_block.split("\n")
    found = False
    new_lines: list[str] = []
    for ln in fm_lines:
        m = re.match(r"^(source_count\s*:\s*)(.*)$", ln)
        if m:
            new_lines.append(f"{m.group(1)}{expected}")
            found = True
        else:
            new_lines.append(ln)
    if not found:
        new_lines.append(f"source_count: {expected}")
    new_fm = "\n".join(new_lines)
    target.write_text(f"---\n{new_fm}{body}", encoding="utf-8")


def _yyyymm_buckets(root: Path) -> dict[str, int]:
    """raw/<kind>/YYYY-MM-DD/*.md を月単位で集計する。"""
    by_month: dict[str, int] = defaultdict(int)
    if not root.exists():
        return by_month
    for p in root.rglob("*.md"):
        if p.name.startswith("."):
            continue
        parent = p.parent.name
        if len(parent) >= 7 and parent[4] == "-":
            ym = parent[:4] + parent[5:7]
        else:
            ym = "unknown"
        by_month[ym] += 1
    return dict(by_month)


def regenerate_index(wiki_dir: Path, memories_dir: Path) -> Path:
    """wiki/index.md を再生成して書き出し、ファイルパスを返す。

    enforce_source_count も同時に走らせる（codex 取り扱い失敗の保険）。
    """
    wiki = Path(wiki_dir)
    memories = Path(memories_dir)

    projects_dir = wiki / "projects"
    projects = sorted(
        p
        for p in (projects_dir.glob("*.md") if projects_dir.exists() else [])
        if not p.name.startswith(".")
    )

    web_count = _count_md_files(memories / "raw" / "web")
    minutes_by_month = _yyyymm_buckets(memories / "raw" / "minutes")
    minutes_count = sum(minutes_by_month.values())

    minutes_dir = wiki / "minutes"
    minutes_files = sorted(
        p
        for p in (minutes_dir.glob("*.md") if minutes_dir.exists() else [])
        if not p.name.startswith(".")
    )

    diary_by_month = _yyyymm_buckets(memories / "raw" / "diary")
    diary_count = sum(diary_by_month.values())

    diary_wiki_dir = wiki / "diary"
    diary_files = sorted(
        p
        for p in (diary_wiki_dir.glob("*.md") if diary_wiki_dir.exists() else [])
        if not p.name.startswith(".")
    )

    people_wiki_dir = wiki / "people"
    people_files_raw = [
        p
        for p in (people_wiki_dir.glob("*.md") if people_wiki_dir.exists() else [])
        if not p.name.startswith(".")
    ]
    # mention_count はソートキーと表示行で 2 回必要になるため、
    # ファイル読込を 1 回に集約してから両用途で使い回す。
    people_mentions = {p: _mention_count(p) for p in people_files_raw}
    people_files = sorted(
        people_files_raw,
        key=lambda x: (-people_mentions[x], x.stem),
    )
    people_count = len(people_files)

    orgs_wiki_dir = wiki / "orgs"
    orgs_files_raw = [
        p
        for p in (orgs_wiki_dir.glob("*.md") if orgs_wiki_dir.exists() else [])
        if not p.name.startswith(".")
    ]
    orgs_mentions = {p: _mention_count(p) for p in orgs_files_raw}
    orgs_files = sorted(
        orgs_files_raw,
        key=lambda x: (-orgs_mentions[x], x.stem),
    )
    orgs_count = len(orgs_files)

    # source_count の保険更新
    enforce_source_count(wiki / "references.md", web_count)
    for ym, count in minutes_by_month.items():
        enforce_source_count(wiki / "minutes" / f"{ym}.md", count)
    for ym, count in diary_by_month.items():
        enforce_source_count(wiki / "diary" / f"{ym}.md", count)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines: list[str] = [
        "---",
        "title: Wiki Index",
        f"updated_at: {now}",
        "status: active",
        "---",
        "",
        "# Wiki Index",
        "",
    ]

    lines.append("## Sessions Timeline")
    lines.append("")
    lines.append(f"project 別通史（codex 統合済み、計 {len(projects)} プロジェクト）:")
    lines.append("")
    for p in projects:
        rel = p.relative_to(wiki)
        lines.append(f"- [{p.stem}](./{rel})")
    lines.append("")

    lines.append("## References Library")
    lines.append("")
    references_md = wiki / "references.md"
    if references_md.exists():
        lines.append(f"外部 URL アーカイブ（kind: web、Raw 計 {web_count} 件、codex 統合済み）:")
        lines.append("")
        lines.append("- [References Library](./references.md)")
    else:
        lines.append(f"外部 URL アーカイブ（kind: web、Raw 計 {web_count} 件、未統合）:")
        lines.append("")
        lines.append("- (まだ統合されていません。`episodic-recording` skill から URL を保存すると自動生成されます)")
    lines.append("")

    lines.append("## Minutes")
    lines.append("")
    if minutes_files:
        lines.append(f"議事録（kind: minutes、月次集約、Raw 計 {minutes_count} 件、codex 統合済み）:")
        lines.append("")
        for p in sorted(minutes_files, key=lambda x: x.stem, reverse=True):
            rel = p.relative_to(wiki)
            lines.append(f"- [{p.stem}](./{rel})")
    else:
        lines.append(f"議事録（kind: minutes、Raw 計 {minutes_count} 件、未統合）:")
        lines.append("")
        lines.append("- (まだ統合されていません。`episodic-recording` skill から議事録を保存すると自動生成されます)")
    lines.append("")

    lines.append("## Diary")
    lines.append("")
    if diary_files:
        lines.append(f"日記（kind: diary、月次集約、Raw 計 {diary_count} 件、codex 統合済み）:")
        lines.append("")
        for p in sorted(diary_files, key=lambda x: x.stem, reverse=True):
            rel = p.relative_to(wiki)
            lines.append(f"- [{p.stem}](./{rel})")
    else:
        lines.append(f"日記（kind: diary、Raw 計 {diary_count} 件、未統合）:")
        lines.append("")
        lines.append("- (まだ統合されていません。`episodic-recording` skill から日記を保存すると自動生成されます)")
    lines.append("")

    lines.append("## People")
    lines.append("")
    if people_files:
        lines.append(
            f"人物 Wiki（minutes/diary から自動抽出、計 {people_count} 名、mention_count 降順）:"
        )
        lines.append("")
        for p in people_files:
            rel = p.relative_to(wiki)
            mc = people_mentions[p]
            lines.append(f"- [{p.stem}](./{rel}) — 言及 {mc} 件")
    else:
        lines.append("人物 Wiki（minutes/diary に人物名が登場すると自動生成されます）:")
        lines.append("")
        lines.append("- (まだ統合されていません)")
    lines.append("")

    lines.append("## Orgs（組織）")
    lines.append("")
    if orgs_files:
        lines.append(
            f"組織 Wiki（minutes/diary から自動抽出、計 {orgs_count} 組織、mention_count 降順）:"
        )
        lines.append("")
        for p in orgs_files:
            rel = p.relative_to(wiki)
            mc = orgs_mentions[p]
            lines.append(f"- [{p.stem}](./{rel}) — 言及 {mc} 件")
    else:
        lines.append("組織 Wiki（minutes/diary に組織名が登場すると自動生成されます）:")
        lines.append("")
        lines.append("- (まだ統合されていません)")
    lines.append("")

    index_path = wiki / "index.md"
    wiki.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path
