#!/usr/bin/env python3
"""LLM Wiki の設定解決・雛形作成・機械的な点検を行う CLI。

設定は各ユーザーのローカルに置く（公開リポジトリには含めない）:
  $LLM_WIKI_CONFIG または ~/.config/llm-wiki/projects.json

Python 3.9 以上、標準ライブラリのみ。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PLUGIN_ROOT / "templates" / "wiki"
DEFAULT_CONFIG = Path("~/.config/llm-wiki/projects.json")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
SKIP_DIRS = {"raw", ".obsidian", ".git"}


def config_path():
    return Path(os.environ.get("LLM_WIKI_CONFIG") or DEFAULT_CONFIG).expanduser()


def load_config():
    path = config_path()
    if not path.is_file():
        return {"projects": {}}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("projects", {})
    return data


def save_config(data):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def expand(p):
    return Path(p).expanduser().resolve()


def git_main_root(cwd):
    """cwd が属するリポジトリの本体ルートを返す（worktree でも本体を指す）。"""
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    common = Path(out)
    return common.parent.resolve() if common.name == ".git" else None


def resolve_project(cwd):
    cwd = expand(cwd)
    candidates = [cwd]
    root = git_main_root(cwd)
    if root:
        candidates.append(root)
    for name, entry in load_config()["projects"].items():
        repo = expand(entry["repo"])
        for c in candidates:
            if c == repo or repo in c.parents:
                return {"project": name, "repo": str(repo), "wiki": str(expand(entry["wiki"]))}
    return None


def cmd_resolve(args):
    found = resolve_project(args.cwd)
    if not found:
        print(f"未登録: {expand(args.cwd)}（/llm-wiki:setup で登録）", file=sys.stderr)
        return 1
    print(json.dumps(found, ensure_ascii=False))
    return 0


def cmd_add(args):
    repo, wiki = expand(args.repo), expand(args.wiki)
    if not repo.is_dir():
        print(f"repo が存在しない: {repo}", file=sys.stderr)
        return 1
    data = load_config()
    data["projects"][args.name] = {"repo": str(repo), "wiki": str(wiki)}
    save_config(data)
    print(f"登録: {args.name} -> {wiki}（{config_path()}）")
    if not (wiki / "index.md").is_file():
        print(f"注意: {wiki} に index.md が無い。init-wiki で雛形を作成できる")
    return 0


def cmd_remove(args):
    data = load_config()
    if data["projects"].pop(args.name, None) is None:
        print(f"未登録: {args.name}", file=sys.stderr)
        return 1
    save_config(data)
    print(f"削除: {args.name}")
    return 0


def cmd_list(_args):
    projects = load_config()["projects"]
    if not projects:
        print(f"登録なし（{config_path()}）")
        return 0
    for name, e in projects.items():
        print(f"{name}\n  repo: {e['repo']}\n  wiki: {e['wiki']}")
    return 0


def cmd_init_wiki(args):
    wiki = expand(args.wiki)
    created = []
    for src in sorted(TEMPLATE_DIR.rglob("*")):
        rel = src.relative_to(TEMPLATE_DIR)
        # リポジトリの .gitignore が CLAUDE.md を無視するため、雛形は .template 付きで持つ
        dst = wiki / (rel.with_suffix("") if rel.suffix == ".template" else rel)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            created.append(str(dst.relative_to(wiki)))
    print(f"{wiki}: 作成 {len(created)} 件（既存ファイルは上書きしない）")
    for c in created:
        print(f"  + {c}")
    return 0


def wiki_pages(wiki):
    for p in sorted(wiki.rglob("*.md")):
        rel = p.relative_to(wiki)
        if rel.parts[0] in SKIP_DIRS:
            continue
        yield p, rel


def page_links(text):
    return {m.group(1).strip() for m in LINK_RE.finditer(CODE_RE.sub("", text))}


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    return text[4:end] if end != -1 else None


def link_matches(link, rel):
    """Obsidian 風に、ファイル名だけ・wiki 相対パス・Vault 相対パスのどれでも一致とみなす。"""
    target = link[:-3] if link.endswith(".md") else link
    stem = rel.with_suffix("").as_posix()
    return target == rel.stem or stem == target or stem.endswith("/" + target) or target.endswith("/" + stem)


def cmd_lint(args):
    wiki = expand(args.wiki) if args.wiki else None
    if wiki is None:
        found = resolve_project(os.getcwd())
        if not found:
            print("wiki を特定できない。--wiki を指定するか /llm-wiki:setup で登録", file=sys.stderr)
            return 1
        wiki = Path(found["wiki"])
    if not (wiki / "index.md").is_file():
        print(f"index.md が無い: {wiki}", file=sys.stderr)
        return 1

    pages = list(wiki_pages(wiki))
    raw_rel = [p.relative_to(wiki) for p in (wiki / "raw").rglob("*")] if (wiki / "raw").is_dir() else []
    all_rel = [rel for _, rel in pages] + raw_rel
    texts = {rel: p.read_text(encoding="utf-8") for p, rel in pages}
    links = {rel: page_links(t) for rel, t in texts.items()}
    meta_pages = {Path("index.md"), Path("log.md"), Path("CLAUDE.md")}

    broken = sorted({(str(rel), l) for rel, ls in links.items() for l in ls
                     if not any(link_matches(l, r) for r in all_rel)})
    inbound = {rel: 0 for rel in texts}
    for src, ls in links.items():
        for l in ls:
            for r in texts:
                if r != src and link_matches(l, r):
                    inbound[r] += 1
    orphans = sorted(str(r) for r, n in inbound.items() if n == 0 and r not in meta_pages)
    index_links = links.get(Path("index.md"), set())
    not_indexed = sorted(str(r) for r in texts if r not in meta_pages
                         and not any(link_matches(l, r) for l in index_links))
    content_pages = {r: frontmatter(t) for r, t in texts.items() if r not in meta_pages}
    no_front = sorted(str(r) for r, fm in content_pages.items() if fm is None)
    no_updated = sorted(str(r) for r, fm in content_pages.items()
                        if fm is not None and not re.search(r"^updated:", fm, re.M))

    report = {
        "wiki": str(wiki),
        "pages": len(texts),
        "broken_links": [{"page": p, "link": l} for p, l in broken],
        "orphans": orphans,
        "not_in_index": not_indexed,
        "missing_frontmatter": no_front,
        "missing_updated": no_updated,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_hook_session_start(_args):
    """SessionStart hook。未登録・失敗時は何も出さずに終わる。"""
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except (ValueError, OSError):
        payload = {}
    try:
        found = resolve_project(payload.get("cwd") or os.getcwd())
    except Exception:
        return 0
    if not found or not (Path(found["wiki"]) / "index.md").is_file():
        return 0
    wiki = found["wiki"]
    context = (
        f"LLM Wiki: このリポジトリ（{found['project']}）の知識 wiki は {wiki} にある。"
        f"過去の設計判断・仕様・障害対応を聞かれたら、先に {wiki}/index.md から関連ページを読む。"
        f"wiki のルールは {wiki}/CLAUDE.md。取り込み・点検は /llm-wiki:ingest, /llm-wiki:query, /llm-wiki:lint。"
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}},
                     ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="llm_wiki.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("resolve", help="cwd に対応する wiki を JSON で出力")
    p.add_argument("--cwd", default=os.getcwd())
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("add", help="リポジトリと wiki の対応を登録（同名は上書き）")
    p.add_argument("--name", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--wiki", required=True)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("remove", help="登録を削除")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_remove)

    sub.add_parser("list", help="登録一覧").set_defaults(func=cmd_list)

    p = sub.add_parser("init-wiki", help="wiki の雛形を作成（既存ファイルは上書きしない）")
    p.add_argument("--wiki", required=True)
    p.set_defaults(func=cmd_init_wiki)

    p = sub.add_parser("lint", help="リンク切れ・孤立ページ・index 漏れなどを JSON で報告")
    p.add_argument("--wiki")
    p.set_defaults(func=cmd_lint)

    sub.add_parser("hook-session-start", help=argparse.SUPPRESS).set_defaults(func=cmd_hook_session_start)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
