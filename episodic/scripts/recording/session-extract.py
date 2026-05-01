#!/usr/bin/env python3
"""Claude Code会話履歴（JSONL）から必要な情報だけを抽出するCLI。

recording で生成した session レポートの `source_jsonl` を起点に、
再調査時にコンテキスト溢れを避けながら特定情報を取得する。

USAGE
  session-extract.py <jsonl_path> <subcommand> [options]

SUBCOMMANDS
  list-reads              Read/Glob/Grep の呼び出し一覧（時刻 / ファイル / サイズ）
  list-edits              Edit/Write/NotebookEdit の呼び出し一覧
  list-bash               Bash コマンドの呼び出し一覧
  list-tools [--name N]   tool_use の呼び出し一覧（任意ツールに絞る）
  list-decisions          ユーザー指示・AskUserQuestion・コミット等の「決定箇所」抽出
  grep <keyword>          キーワードを含むメッセージ周辺を抽出（--context N）
  tool <name>             特定ツールの全呼び出しを本文付きで抽出
  range                   時刻範囲で抽出（--from HH:MM --to HH:MM）
  around <message_uuid>   指定メッセージID周辺を抽出（--window N）
  meta                    セッションメタ情報のみ出力（メッセージ数・期間等）

COMMON OPTIONS
  --format {md,json,csv}  出力形式（既定: list系=csv, その他=md）
  --context N             grep/range で前後Nメッセージを含める（既定: 0）
  --window N              around で前後Nメッセージ（既定: 5）
  --with-result           tool の結果本文も含める（list-tools/tool のみ、既定: off）
  --compress              md 出力時に jsonl-to-markdown.py と同じ圧縮を適用
  --no-header             CSV ヘッダ行を出さない

EXAMPLES
  # 読み込んだファイル一覧
  session-extract.py xxx.jsonl list-reads

  # REQ-002 の議論箇所を前後3メッセージ込みで抽出
  session-extract.py xxx.jsonl grep "REQ-002" --context 3 --compress

  # 全 Bash 呼び出しを時刻順に
  session-extract.py xxx.jsonl list-bash

  # 特定時刻範囲の会話を圧縮Markdownで
  session-extract.py xxx.jsonl range --from 10:00 --to 10:30 --compress
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
# jsonl-to-markdown.py をモジュールとして取り込み、圧縮・レンダリング関数を再利用
sys.path.insert(0, str(SCRIPT_DIR))
import importlib.util

_spec = importlib.util.spec_from_file_location("jsonl_to_md", SCRIPT_DIR / "jsonl-to-markdown.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def build_tool_maps(records: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    tool_name_by_id: dict[str, str] = {}
    tool_input_by_id: dict[str, dict[str, Any]] = {}
    for r in records:
        content = r.get("message", {}).get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tid = b.get("id")
                    name = b.get("name")
                    inp = b.get("input")
                    if tid and name:
                        tool_name_by_id[tid] = name
                    if tid and isinstance(inp, dict):
                        tool_input_by_id[tid] = inp
    return tool_name_by_id, tool_input_by_id


def fmt_ts(ts: str | None, short: bool = False) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%H:%M:%S") if short else dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def iter_tool_uses(records: list[dict[str, Any]]) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    """(record, tool_use_block) を返す。"""
    for r in records:
        content = r.get("message", {}).get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    yield r, b


def iter_tool_results(records: list[dict[str, Any]]) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    for r in records:
        content = r.get("message", {}).get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    yield r, b


def extract_result_text(block: dict[str, Any]) -> str:
    c = block.get("content", "")
    if isinstance(c, list):
        parts = []
        for x in c:
            if isinstance(x, dict) and x.get("type") == "text":
                parts.append(x.get("text", ""))
            else:
                parts.append(json.dumps(x, ensure_ascii=False))
        return "\n\n".join(p for p in parts if p)
    return str(c)


# ---------- subcommand implementations ----------


def cmd_meta(records: list[dict[str, Any]], args: argparse.Namespace) -> int:
    session_id = next((r.get("sessionId") for r in records if r.get("sessionId")), None)
    first_ts = next((r.get("timestamp") for r in records if r.get("timestamp")), None)
    last_ts = next((r.get("timestamp") for r in reversed(records) if r.get("timestamp")), None)
    cwd = next((r.get("cwd") for r in records if r.get("cwd")), None)
    branch = next((r.get("gitBranch") for r in records if r.get("gitBranch")), None)
    total_msgs = sum(1 for r in records if r.get("type") in ("user", "assistant") and not r.get("isMeta"))
    user_msgs = sum(1 for r in records if r.get("type") == "user" and not r.get("isMeta"))

    tool_counts: dict[str, int] = {}
    for _r, b in iter_tool_uses(records):
        n = b.get("name", "unknown")
        tool_counts[n] = tool_counts.get(n, 0) + 1

    out = {
        "session_id": session_id,
        "started_at": fmt_ts(first_ts),
        "ended_at": fmt_ts(last_ts),
        "cwd": cwd,
        "git_branch": branch,
        "total_messages": total_msgs,
        "user_messages": user_msgs,
        "tool_counts": dict(sorted(tool_counts.items(), key=lambda x: -x[1])),
    }

    if args.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"session_id    : {out['session_id']}")
        print(f"period        : {out['started_at']}  →  {out['ended_at']}")
        print(f"cwd           : {out['cwd']}")
        print(f"git_branch    : {out['git_branch']}")
        print(f"messages      : total={out['total_messages']}  user={out['user_messages']}")
        print("tool_counts   :")
        for name, n in out["tool_counts"].items():
            print(f"  {n:>4}  {name}")
    return 0


def cmd_list_tool_generic(
    records: list[dict[str, Any]],
    args: argparse.Namespace,
    filter_names: set[str] | None,
    columns: list[tuple[str, callable]],
) -> int:
    rows = []
    for r, b in iter_tool_uses(records):
        name = b.get("name", "unknown")
        if filter_names is not None and name not in filter_names:
            continue
        if getattr(args, "name", None) and name != args.name:
            continue
        ts = fmt_ts(r.get("timestamp"), short=True)
        inp = b.get("input") or {}
        row = {"time": ts, "tool": name, "id": b.get("id", "")}
        for col, fn in columns:
            row[col] = fn(inp)
        rows.append(row)

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    fieldnames = ["time", "tool"] + [c for c, _ in columns]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    if not args.no_header:
        writer.writeheader()
    for row in rows:
        writer.writerow(row)
    sys.stdout.write(buf.getvalue())
    return 0


def cmd_list_reads(records, args):
    return cmd_list_tool_generic(
        records, args,
        filter_names={"Read", "Glob", "Grep", "NotebookRead",
                      "mcp__serena__find_symbol", "mcp__serena__get_symbols_overview",
                      "mcp__serena__search_for_pattern", "mcp__serena__list_dir",
                      "mcp__serena__find_file"},
        columns=[
            ("path_or_pattern", lambda i: i.get("file_path") or i.get("path") or i.get("pattern")
                                         or i.get("query") or i.get("name_path") or ""),
            ("extra", lambda i: i.get("relative_path") or i.get("glob") or ""),
        ],
    )


def cmd_list_edits(records, args):
    return cmd_list_tool_generic(
        records, args,
        filter_names={"Edit", "Write", "NotebookEdit", "MultiEdit"},
        columns=[
            ("file_path", lambda i: i.get("file_path") or i.get("notebook_path") or ""),
            ("summary", lambda i: _edit_summary(i)),
        ],
    )


def _edit_summary(inp: dict[str, Any]) -> str:
    if "old_string" in inp:
        old = str(inp.get("old_string", ""))[:60]
        new = str(inp.get("new_string", ""))[:60]
        return f"- {old!r}  →  + {new!r}"
    if "content" in inp:
        c = str(inp.get("content", ""))
        return f"write {len(c)} chars"
    return ""


def cmd_list_bash(records, args):
    return cmd_list_tool_generic(
        records, args,
        filter_names={"Bash"},
        columns=[
            ("command", lambda i: (i.get("command") or "").replace("\n", " ⏎ ")[:200]),
            ("description", lambda i: i.get("description", "")),
        ],
    )


def cmd_list_tools(records, args):
    return cmd_list_tool_generic(
        records, args,
        filter_names=None,  # all tools
        columns=[
            ("summary", lambda i: _tool_summary(i)),
        ],
    )


def _tool_summary(inp: dict[str, Any]) -> str:
    for key in ("file_path", "command", "pattern", "query", "url", "skill", "description", "name_path"):
        if key in inp:
            v = str(inp[key]).replace("\n", " ⏎ ")
            return f"{key}={v[:120]}"
    return ""


def cmd_list_decisions(records, args):
    """ユーザー指示・AskUserQuestion・コミットなど「決定箇所」を抽出。"""
    rows = []

    # 1. ユーザー発話（生メッセージ）。システム通知・ツール完了通知・ペーストはスキップ
    skip_patterns = (
        "<task-notification>",
        "<system-reminder>",
        "<local-command-",
        "<command-name>",
        "<command-message>",
    )
    for r in records:
        if r.get("type") != "user" or r.get("isMeta"):
            continue
        content = r.get("message", {}).get("content")
        if not isinstance(content, str):
            continue
        text = content.strip()
        if not text:
            continue
        if any(pat in text for pat in skip_patterns):
            continue
        if _mod.is_pasted_slash_command(text):
            continue
        rows.append({
            "time": fmt_ts(r.get("timestamp"), short=True),
            "kind": "user_prompt",
            "detail": text.replace("\n", " ⏎ ")[:200],
        })

    # 2. AskUserQuestion のレスポンス
    for r, b in iter_tool_uses(records):
        if b.get("name") == "AskUserQuestion":
            rows.append({
                "time": fmt_ts(r.get("timestamp"), short=True),
                "kind": "ask_user",
                "detail": (b.get("input", {}).get("question") or "")[:200],
            })

    for r, b in iter_tool_results(records):
        # AskUserQuestion の回答は tool_result に来る
        txt = extract_result_text(b)
        if txt and "ユーザーが選択" in txt or "User selected" in txt:
            rows.append({
                "time": fmt_ts(r.get("timestamp"), short=True),
                "kind": "ask_user_answer",
                "detail": txt[:200],
            })

    # 3. git commit 実行
    for r, b in iter_tool_uses(records):
        if b.get("name") == "Bash":
            cmd = (b.get("input", {}).get("command") or "")
            if re.search(r'\bgit\s+commit\b', cmd):
                rows.append({
                    "time": fmt_ts(r.get("timestamp"), short=True),
                    "kind": "git_commit",
                    "detail": cmd.replace("\n", " ⏎ ")[:200],
                })

    rows.sort(key=lambda x: x["time"])

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["time", "kind", "detail"], extrasaction="ignore")
    if not args.no_header:
        writer.writeheader()
    for row in rows:
        writer.writerow(row)
    sys.stdout.write(buf.getvalue())
    return 0


def _record_matches_keyword(r: dict[str, Any], keyword: str) -> bool:
    content = r.get("message", {}).get("content", "")
    if isinstance(content, str):
        return keyword in content
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text" and keyword in b.get("text", ""):
                return True
            if t == "thinking" and keyword in b.get("thinking", ""):
                return True
            if t == "tool_use":
                if keyword in json.dumps(b.get("input", {}), ensure_ascii=False):
                    return True
                if keyword in (b.get("name") or ""):
                    return True
            if t == "tool_result":
                txt = extract_result_text(b)
                if keyword in txt:
                    return True
    return False


def _select_with_context(records: list[dict[str, Any]], hit_indices: list[int], context: int) -> list[int]:
    """ヒットした index 群の前後 context を含めた index の和集合。"""
    chosen: set[int] = set()
    for i in hit_indices:
        for j in range(max(0, i - context), min(len(records), i + context + 1)):
            chosen.add(j)
    return sorted(chosen)


def _render_selected(records: list[dict[str, Any]], indices: list[int], compress: bool) -> str:
    tool_name_by_id, tool_input_by_id = build_tool_maps(records)
    sections: list[str] = []
    for i in indices:
        r = records[i]
        if _mod.should_skip(r):
            continue
        if compress:
            s = _mod.render_message(r, tool_name_by_id, tool_input_by_id)
        else:
            # 非圧縮版: jsonl-to-markdown の DROP_BODY / LONG_KEYS を一時的に空にして呼び出し
            saved_drop = _mod.TOOL_RESULT_DROP_BODY
            saved_long = _mod.TOOL_INPUT_LONG_KEYS
            saved_skip = _mod.TOOL_USE_FULLY_SKIP
            _mod.TOOL_RESULT_DROP_BODY = set()
            _mod.TOOL_INPUT_LONG_KEYS = set()
            _mod.TOOL_USE_FULLY_SKIP = set()
            try:
                s = _mod.render_message(r, tool_name_by_id, tool_input_by_id)
            finally:
                _mod.TOOL_RESULT_DROP_BODY = saved_drop
                _mod.TOOL_INPUT_LONG_KEYS = saved_long
                _mod.TOOL_USE_FULLY_SKIP = saved_skip
        if s:
            sections.append(s)
    return "\n\n".join(sections) + "\n"


def cmd_grep(records, args):
    hits = [i for i, r in enumerate(records) if _record_matches_keyword(r, args.keyword)]
    if not hits:
        print(f"no match for keyword: {args.keyword}", file=sys.stderr)
        return 1
    indices = _select_with_context(records, hits, args.context)

    if args.format == "json":
        dump = [records[i] for i in indices]
        print(json.dumps(dump, ensure_ascii=False, indent=2))
        return 0

    print(f"# grep: {args.keyword!r} (hits={len(hits)}, context={args.context})\n")
    print(_render_selected(records, indices, compress=args.compress))
    return 0


def cmd_tool(records, args):
    """特定ツール名の全呼び出しを tool_use / tool_result ペアで抽出する。"""
    tool_name_by_id, _ = build_tool_maps(records)
    wanted = args.name
    selected: list[int] = []
    for i, r in enumerate(records):
        content = r.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == wanted:
                selected.append(i)
                break
            if args.with_result and b.get("type") == "tool_result":
                tid = b.get("tool_use_id")
                if tid and tool_name_by_id.get(tid) == wanted:
                    selected.append(i)
                    break
    selected = sorted(set(selected))
    if not selected:
        print(f"no tool_use found for: {wanted}", file=sys.stderr)
        return 1

    if args.format == "json":
        dump = [records[i] for i in selected]
        print(json.dumps(dump, ensure_ascii=False, indent=2))
        return 0

    print(f"# tool: {wanted} (count={len(selected)})\n")
    print(_render_selected(records, selected, compress=args.compress))
    return 0


def cmd_range(records, args):
    def _parse(t: str | None) -> datetime | None:
        if not t:
            return None
        today = datetime.now().astimezone().date()
        for fmt in ("%H:%M:%S", "%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(t, fmt)
                if fmt.startswith("%H"):
                    dt = datetime.combine(today, dt.time()).astimezone()
                else:
                    dt = dt.astimezone()
                return dt
            except ValueError:
                continue
        raise ValueError(f"invalid time: {t}")

    from_t = _parse(args.from_)
    to_t = _parse(args.to)
    indices = []
    for i, r in enumerate(records):
        ts = r.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        except ValueError:
            continue
        if from_t and dt < from_t:
            continue
        if to_t and dt > to_t:
            continue
        indices.append(i)

    if not indices:
        print("no records in range", file=sys.stderr)
        return 1

    if args.format == "json":
        dump = [records[i] for i in indices]
        print(json.dumps(dump, ensure_ascii=False, indent=2))
        return 0
    print(_render_selected(records, indices, compress=args.compress))
    return 0


def cmd_around(records, args):
    target_uuid = args.uuid
    hit = None
    for i, r in enumerate(records):
        if r.get("uuid") == target_uuid or r.get("message", {}).get("id") == target_uuid:
            hit = i
            break
    if hit is None:
        print(f"uuid not found: {target_uuid}", file=sys.stderr)
        return 1
    start = max(0, hit - args.window)
    end = min(len(records), hit + args.window + 1)
    indices = list(range(start, end))

    if args.format == "json":
        dump = [records[i] for i in indices]
        print(json.dumps(dump, ensure_ascii=False, indent=2))
        return 0
    print(_render_selected(records, indices, compress=args.compress))
    return 0


# ---------- argparse wiring ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="session-extract",
        description="Claude Code JSONL 履歴から再調査向けに部分抽出する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("jsonl_path", help="Claude Code のセッション JSONL パス")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser, *, format_default: str, with_context: bool = False,
                   with_window: bool = False, with_compress: bool = False) -> None:
        sp.add_argument("--format", choices=["md", "json", "csv"], default=format_default)
        sp.add_argument("--no-header", action="store_true")
        if with_context:
            sp.add_argument("--context", type=int, default=0, help="前後 N メッセージを含める")
        if with_window:
            sp.add_argument("--window", type=int, default=5)
        if with_compress:
            sp.add_argument("--compress", action="store_true",
                            help="圧縮（tool_result/tool_use 削減）を適用")

    sp = sub.add_parser("meta", help="セッションメタ情報")
    add_common(sp, format_default="md")

    sp = sub.add_parser("list-reads", help="Read/Grep/Glob の一覧")
    add_common(sp, format_default="csv")

    sp = sub.add_parser("list-edits", help="Edit/Write の一覧")
    add_common(sp, format_default="csv")

    sp = sub.add_parser("list-bash", help="Bash 実行の一覧")
    add_common(sp, format_default="csv")

    sp = sub.add_parser("list-tools", help="全 tool_use の一覧（--name で絞り込み可）")
    sp.add_argument("--name", help="特定ツール名に絞る")
    add_common(sp, format_default="csv")

    sp = sub.add_parser("list-decisions", help="決定箇所（ユーザー指示・AskUser・commit）")
    add_common(sp, format_default="csv")

    sp = sub.add_parser("grep", help="キーワードを含むメッセージ周辺")
    sp.add_argument("keyword")
    add_common(sp, format_default="md", with_context=True, with_compress=True)

    sp = sub.add_parser("tool", help="特定ツールの全呼び出しを本文付きで抽出")
    sp.add_argument("name")
    sp.add_argument("--with-result", action="store_true")
    add_common(sp, format_default="md", with_compress=True)

    sp = sub.add_parser("range", help="時刻範囲で抽出")
    sp.add_argument("--from", dest="from_", required=True, help="開始時刻 HH:MM[:SS]")
    sp.add_argument("--to", required=True, help="終了時刻 HH:MM[:SS]")
    add_common(sp, format_default="md", with_compress=True)

    sp = sub.add_parser("around", help="指定メッセージUUID周辺")
    sp.add_argument("uuid")
    add_common(sp, format_default="md", with_window=True, with_compress=True)

    return p


DISPATCH = {
    "meta": cmd_meta,
    "list-reads": cmd_list_reads,
    "list-edits": cmd_list_edits,
    "list-bash": cmd_list_bash,
    "list-tools": cmd_list_tools,
    "list-decisions": cmd_list_decisions,
    "grep": cmd_grep,
    "tool": cmd_tool,
    "range": cmd_range,
    "around": cmd_around,
}


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    jsonl = Path(args.jsonl_path)
    if not jsonl.exists():
        print(f"error: JSONL not found: {jsonl}", file=sys.stderr)
        return 2
    records = load_records(jsonl)
    return DISPATCH[args.cmd](records, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
