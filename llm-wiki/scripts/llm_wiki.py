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
    wiki = resolve_wiki(args.wiki)
    if wiki is None:
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


# パスには @ ( ) [ ] も入りうる（Next.js の app/(group)/[id] など）ので、末尾の @<sha> を手がかりに最短一致で切る。
# sha の直後に英数字が続くものは参照とみなさない（日本語が続くのは許す）。
CLAIM_RE = re.compile(r"repo://([A-Za-z0-9._-]+)/((?:(?!repo://)[^\s`]){1,512}?)(?:#L(\d+)(?:-L(\d+))?)?@([0-9a-fA-F]{7,40})(?![0-9A-Za-z_])")
FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[^\n]*$|\Z)", re.S | re.M)
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.M)
GIT_TIMEOUT = 10


def git(repo, *args, binary=False):
    """git を実行する。UTF-8 でない出力でも落ちないよう、binary=False のときは置換文字で復号する。"""
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=GIT_TIMEOUT)
    if not binary:
        proc.stdout = proc.stdout.decode("utf-8", errors="replace")
        proc.stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc


def count_lines(data):
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def repo_relpath(repo, path):
    """repo 内の POSIX 相対パスを返す。repo の外を指す（.. や絶対パス、symlink 経由）なら None。"""
    p = Path(path)
    target = (p if p.is_absolute() else repo / p).resolve()
    try:
        rel = target.relative_to(repo)
    except ValueError:
        return None
    return rel.as_posix() if rel.parts else None


def parse_lines(spec):
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", spec or "")
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return (a, b) if 1 <= a <= b else None


def cmd_claim_ref(args):
    found = resolve_project(args.cwd)
    if not found:
        print(f"未登録: {expand(args.cwd)}（/llm-wiki:setup で登録）", file=sys.stderr)
        return 1
    rng = None
    if args.lines is not None:
        rng = parse_lines(args.lines)
        if rng is None:
            print(f"行範囲が不正: {args.lines}（A-B または A、1 始まり）", file=sys.stderr)
            return 1
    try:
        # worktree では本体ではなく worktree 自身の HEAD を根拠にする（オブジェクトは本体と共有される）
        top = git(expand(args.cwd), "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            print(f"git リポジトリではない: {expand(args.cwd)}", file=sys.stderr)
            return 1
        repo = Path(top.stdout.strip()).resolve()
        rel = repo_relpath(repo, args.path)
        if rel is None:
            print(f"リポジトリの外を指している: {args.path}", file=sys.stderr)
            return 1
        if re.search(r"[\s`]", rel):
            print(f"空白やバッククォートを含むパスは参照にできない: {rel}", file=sys.stderr)
            return 1
        head = git(repo, "rev-parse", "--short=12", "HEAD")
        if head.returncode != 0:
            print(f"HEAD を取得できない: {head.stderr.strip()}", file=sys.stderr)
            return 1
        kind = git(repo, "cat-file", "-t", f"HEAD:{rel}")
        if kind.returncode != 0 or kind.stdout.strip() != "blob":
            print(f"HEAD に無いファイル（未コミット・未追跡を含む）: {rel}", file=sys.stderr)
            return 1
        if git(repo, "diff", "--quiet", "--no-ext-diff", "--no-textconv", "HEAD", "--", rel).returncode != 0:
            print(f"未コミットの変更がある: {rel}（コミットしてから参照を作る）", file=sys.stderr)
            return 1
        if rng:
            total = count_lines(git(repo, "cat-file", "-p", f"HEAD:{rel}", binary=True).stdout)
            if rng[1] > total:
                print(f"行範囲が不正: {args.lines}（HEAD の {rel} は {total} 行）", file=sys.stderr)
                return 1
    except (OSError, subprocess.SubprocessError) as e:
        print(f"git の実行に失敗: {e}", file=sys.stderr)
        return 1
    sha = head.stdout.strip()
    anchor = ""
    if rng:
        anchor = f"#L{rng[0]}" if rng[0] == rng[1] else f"#L{rng[0]}-L{rng[1]}"
    ref = f"repo://{found['project']}/{rel}{anchor}@{sha}"
    # check-claims と同じ search（最短一致）で読み戻す。fullmatch だと後戻りで一致してしまう
    m = CLAIM_RE.search(ref)
    expected = (found["project"], rel, str(rng[0]) if rng else None,
                str(rng[1]) if rng and rng[1] != rng[0] else None, sha)
    if not m or m.span() != (0, len(ref)) or m.groups() != expected:
        print(f"check-claims で読み戻せない参照になるため出力しない: {ref}", file=sys.stderr)
        return 1
    print(ref)
    return 0


def renamed_to(repo, sha, path):
    out = git(repo, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "-M", "--name-status", "-z", sha, "HEAD")
    tokens = out.stdout.split("\0")
    i = 0
    while i < len(tokens) and tokens[i]:
        status = tokens[i]
        if status[:1] in ("R", "C"):
            old, new = tokens[i + 1:i + 3]
            if status[0] == "R" and old == path:
                return new
            i += 3
        else:
            i += 2
    return None


def file_change(repo, sha, path):
    """sha から HEAD までの path の変化。行範囲に依存しない部分だけを調べる（キャッシュ対象）。"""
    try:
        if git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
            return {"status": "unknown_commit"}
        if git(repo, "cat-file", "-e", f"{sha}:{path}").returncode != 0:
            return {"status": "invalid", "message": "参照したコミットにこのファイルが無い"}
        if git(repo, "cat-file", "-e", f"HEAD:{path}").returncode != 0:
            result = {"status": "missing"}
            new = renamed_to(repo, sha, path)
            if new:
                result["renamed_to"] = new
            return result
        lines = count_lines(git(repo, "cat-file", "-p", f"{sha}:{path}", binary=True).stdout)
        diff = git(repo, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "-U0", sha, "HEAD", "--", path)
        if diff.returncode != 0:
            return {"status": "error", "message": diff.stderr.strip()}
    except (OSError, subprocess.SubprocessError) as e:
        return {"status": "error", "message": str(e)}
    hunks = [(int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1), m.group(0))
             for m in HUNK_RE.finditer(diff.stdout)]
    binary = not hunks and "Binary files" in diff.stdout
    return {"status": "changed" if hunks or binary else "fresh", "hunks": hunks, "binary": binary, "lines": lines}


def judge_claim(change, rng):
    """ファイルの変化と行範囲から status を決める。"""
    if change["status"] not in ("changed", "fresh"):
        return dict(change)
    if rng and rng[1] > change.get("lines", rng[1]):
        return {"status": "invalid", "message": f"行範囲が参照したコミットのファイル（{change['lines']} 行）を超えている"}
    hunks = change["hunks"]
    if change["binary"]:
        return {"status": "stale", "message": "バイナリファイルが変更された"}
    if rng is None:
        if hunks:
            return {"status": "stale", "hunks": [h[4] for h in hunks]}
        return {"status": "fresh"}
    a, b = rng
    overlap, offset = [], 0
    for s, c, _s2, c2, header in hunks:
        if c > 0:
            if s <= b and s + c - 1 >= a:
                overlap.append(header)
            elif s + c - 1 < a:
                offset += c2 - c
        else:  # 純粋な挿入。s 行目の直後に入る
            if a <= s < b:
                overlap.append(header)
            elif s < a:
                offset += c2
    if overlap:
        return {"status": "stale", "hunks": overlap}
    result = {"status": "fresh"}
    if offset:
        na, nb = a + offset, b + offset
        result["current"] = f"#L{na}" if na == nb else f"#L{na}-L{nb}"
    return result


def resolve_wiki(arg):
    if arg:
        wiki = expand(arg)
    else:
        found = resolve_project(os.getcwd())
        if not found:
            print("wiki を特定できない。--wiki を指定するか /llm-wiki:setup で登録", file=sys.stderr)
            return None
        wiki = Path(found["wiki"])
    if not (wiki / "index.md").is_file():
        print(f"index.md が無い: {wiki}", file=sys.stderr)
        return None
    return wiki


def check_claim(m, projects, cache):
    project, path, a, b, sha = m.groups()
    rng = (int(a), int(b) if b else int(a)) if a else None
    entry = projects.get(project)
    if entry is None:
        return {"status": "unknown_project"}
    if rng and not 1 <= rng[0] <= rng[1]:
        return {"status": "invalid", "message": "行範囲が不正"}
    repo = expand(entry["repo"])
    relpath = None if Path(path).is_absolute() or ".." in Path(path).parts else repo_relpath(repo, path)
    if relpath is None:
        return {"status": "invalid", "message": "リポジトリの外を指している"}
    key = (str(repo), sha.lower(), relpath)
    if key not in cache:
        cache[key] = file_change(repo, sha, relpath)
    return judge_claim(cache[key], rng)


def cmd_check_claims(args):
    wiki = resolve_wiki(args.wiki)
    if wiki is None:
        return 1
    pages = list(wiki_pages(wiki))
    if args.page:
        pages = [(p, rel) for p, rel in pages if rel == Path(args.page)]
        if not pages:
            print(f"ページが無い: {args.page}（wiki からの相対パス）", file=sys.stderr)
            return 1
    projects = load_config()["projects"]
    cache = {}
    total, fresh, issues, shifted = 0, 0, [], []
    for p, rel in pages:
        text = FENCE_RE.sub("", p.read_text(encoding="utf-8", errors="replace"))
        for m in CLAIM_RE.finditer(text):
            total += 1
            try:
                result = check_claim(m, projects, cache)
            except Exception as e:  # 1 件の失敗で全体を止めない
                result = {"status": "error", "message": f"{type(e).__name__}: {e}"}
            status = result.pop("status")
            if status == "fresh":
                fresh += 1
                if "current" in result:
                    shifted.append({"page": str(rel), "ref": m.group(0), "current": result["current"]})
            else:
                issues.append({"page": str(rel), "ref": m.group(0), "status": status, **result})
    report = {"wiki": str(wiki), "claims": total, "fresh": fresh, "issues": issues, "shifted": shifted}
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
- wiki の記述がコードと食い違っていたらコードを正とし、ユーザーに確認せずに wiki を直す（古い記述は取り消し線と日付で残し、log.md に追記）。直したことは作業報告で一言伝える。
- 作業中に新しい設計判断・障害の原因・ハマりどころが分かったら、作業の最後に /llm-wiki:ingest の手順で確認なしに記録し、記録したページを報告する。{inbox_note}
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

    p = sub.add_parser("claim-ref", help="コードの根拠参照 repo://<project>/<path>#L<a>-L<b>@<sha> を出力")
    p.add_argument("path", help="リポジトリのルートからの相対パス（リポジトリ内の絶対パスも可）")
    p.add_argument("--lines", help="行範囲 A-B または A")
    p.add_argument("--cwd", default=os.getcwd())
    p.set_defaults(func=cmd_claim_ref)

    p = sub.add_parser("check-claims", help="wiki の repo:// 根拠が参照時点から変わっていないかを JSON で報告")
    p.add_argument("--wiki")
    p.add_argument("--page", help="点検するページ（wiki からの相対パス）")
    p.set_defaults(func=cmd_check_claims)

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
