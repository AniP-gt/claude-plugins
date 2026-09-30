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

import capture

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PLUGIN_ROOT / "templates" / "wiki"
DEFAULT_CONFIG = Path("~/.config/llm-wiki/projects.json")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
SKIP_DIRS = {"raw", ".obsidian", ".git"}
INDEX_MAX_CHARS = 6000


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


def read_hook_payload():
    try:
        return json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except (ValueError, OSError):
        return {}


def hook_target(payload):
    """hook の対象 wiki。候補抽出の子プロセス内・未登録・失敗時は None。"""
    if os.environ.get(capture.GUARD_ENV):
        return None
    try:
        return resolve_project(payload.get("cwd") or os.getcwd())
    except Exception:
        return None


def read_index(wiki):
    try:
        return (Path(wiki) / "index.md").read_text(encoding="utf-8")
    except OSError:
        return None


def cmd_hook_session_start(_args):
    """SessionStart hook。未登録・失敗時は何も出さずに終わる。"""
    found = hook_target(read_hook_payload())
    index = read_index(found["wiki"]) if found else None
    if index is None:
        return 0
    inbox = Path(found["wiki"]) / "raw" / "inbox"
    pending = len(list(inbox.glob("*.md"))) if inbox.is_dir() else 0
    context = session_context(found["project"], found["wiki"], index, pending)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}},
                     ensure_ascii=False))
    return 0


def cmd_hook_session_end(_args):
    """SessionEnd hook。候補抽出を別プロセスで起動し、すぐに終わる。"""
    payload = read_hook_payload()
    found = hook_target(payload)
    transcript = payload.get("transcript_path")
    if not found or not transcript or not capture.settings(load_config())["enabled"]:
        return 0
    cmd = [sys.executable, str(Path(__file__).resolve()), "capture", "--transcript", transcript,
           "--session", payload.get("session_id") or Path(transcript).stem,
           "--cwd", payload.get("cwd") or os.getcwd()]
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=dict(os.environ, **{capture.GUARD_ENV: "1"}))
    except OSError as e:
        capture.log(f"error spawn {found['project']}: {e}")
    return 0


def cmd_capture(args):
    found = resolve_project(args.cwd)
    if not found:
        return 0
    try:
        return capture.run(found, load_config(), args.transcript, args.session, read_index(found["wiki"]) or "")
    except Exception as e:  # バックグラウンド実行なので、落ちた理由はログにしか残らない
        capture.log(f"error {found['project']} session={args.session[:8]}: {type(e).__name__}: {e}")
        return 1


def cmd_capture_config(args):
    data = load_config()
    opts = data.setdefault("capture", {})
    if args.enable or args.disable:
        opts["enabled"] = bool(args.enable)
    if args.model:
        opts["model"] = args.model
    if args.enable or args.disable or args.model:
        save_config(data)
    print(json.dumps(capture.settings(data), ensure_ascii=False))
    return 0


def index_excerpt(index):
    """frontmatter を除いた index.md。長すぎる場合は先頭だけ渡し、残りは読みに行かせる。"""
    fm = frontmatter(index)
    body = index[index.find("\n---", 4) + 4:] if fm is not None else index
    body = body.strip()
    if len(body) > INDEX_MAX_CHARS:
        body = body[:INDEX_MAX_CHARS].rstrip() + "\n…（以下省略。全体は index.md を読む）"
    return body


def session_context(project, wiki, index, pending=0):
    inbox_note = (f"\n- 前のセッションから自動抽出した未整理の候補が {pending} 件ある（{wiki}/raw/inbox/）。"
                  "最初の返答でユーザーに一言伝え、/llm-wiki:ingest で整理するか聞く。今の依頼の妨げになるなら後回しでよい。"
                  if pending else "")
    return f"""LLM Wiki（{project}）: {wiki}
このリポジトリの設計判断・仕様・障害対応・ハマりどころを集めた wiki。書き方のルールは {wiki}/CLAUDE.md。
使い方:
- 調査・実装・レビューを始める前に、下の目次から関連ページを探して読む。`[[名前]]` は {wiki}/wiki/ 以下の `名前.md`。
- 仕様・過去の経緯・既知の不具合で迷ったら、推測で進めずに wiki を確認する。目次に無ければ {wiki} を Grep する（raw/ も対象）。
- サブエージェントに調査や実装を任せるときは、関連する wiki ページのパスをプロンプトに含める。
- wiki の記述がコードと食い違っていたらコードを正とし、食い違いをユーザーに伝える。
- 作業中に新しい設計判断・障害の原因・ハマりどころが分かったときだけ、作業の最後に /llm-wiki:ingest での記録をユーザーに提案する。{inbox_note}
目次（index.md）:
{index_excerpt(index)}"""


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

    p = sub.add_parser("capture-config", help="セッション終了時の候補自動抽出の設定を表示・変更")
    p.add_argument("--enable", action="store_true")
    p.add_argument("--disable", action="store_true")
    p.add_argument("--model", help="抽出に使う claude のモデル（既定 sonnet）")
    p.set_defaults(func=cmd_capture_config)

    p = sub.add_parser("capture", help="transcript から候補を抽出して raw/inbox/ に保存（通常は hook が呼ぶ）")
    p.add_argument("--transcript", required=True)
    p.add_argument("--session", required=True)
    p.add_argument("--cwd", default=os.getcwd())
    p.set_defaults(func=cmd_capture)

    sub.add_parser("hook-session-start", help=argparse.SUPPRESS).set_defaults(func=cmd_hook_session_start)
    sub.add_parser("hook-session-end", help=argparse.SUPPRESS).set_defaults(func=cmd_hook_session_end)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
