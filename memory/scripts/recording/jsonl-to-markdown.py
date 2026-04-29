#!/usr/bin/env python3
"""Claude Code会話履歴のJSONLをMarkdownに変換する。

AIに分析させる前提で、以下を常に適用する:
- type が user / assistant のメッセージのみ抽出
- isMeta, <local-command-*> / <command-*> タグ付きメッセージ, `❯ /...` のペーストはスキップ
- tool_use / tool_result / thinking も保持（文脈保持のため）

Usage:
    jsonl-to-markdown.py <input.jsonl> [<output.md>]
入力省略時は stdin、出力省略時は入力の拡張子を .md に置換（stdin→stdout）。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

LOCAL_COMMAND_TAGS = (
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<command-stdout>",
    "<command-stderr>",
)

# tool_result 圧縮ポリシー
# 入力（tool_use の引数）から内容が推測でき、要約に本文そのものが不要なツール
TOOL_RESULT_DROP_BODY = {
    "Read", "Grep", "Glob", "WebFetch", "WebSearch", "NotebookRead",
    "mcp__serena__find_symbol",
    "mcp__serena__get_symbols_overview",
    "mcp__serena__find_referencing_symbols",
    "mcp__serena__search_for_pattern",
    "mcp__serena__list_dir",
    "mcp__serena__find_file",
}

# 要約への寄与がゼロで、件数が多く累積コストが高いツールは完全スキップ
TOOL_USE_FULLY_SKIP = {
    "TaskUpdate",  # status 遷移のみ
}
# 本文を部分的に残すツール（長ければ先頭/末尾のみ残す）
TOOL_RESULT_HEAD_BYTES = 800
TOOL_RESULT_TAIL_BYTES = 400
TOOL_RESULT_KEEP_LIMIT = 2000  # これ以下ならそのまま残す
TOOL_RESULT_ERROR_HEAD_BYTES = 2000  # エラー時は先頭 2KB まで残す

# tool_use input 圧縮ポリシー
# 長大な自由記述（コード・プロンプト本文）が入るキーを頭尾カットする
TOOL_INPUT_LONG_KEYS = {"args", "prompt", "content", "new_string", "old_string", "command"}
TOOL_INPUT_LONG_THRESHOLD = 1000
TOOL_INPUT_LONG_HEAD = 500
TOOL_INPUT_LONG_TAIL = 200


def iter_lines(path: str | None) -> Iterable[str]:
    if path is None:
        yield from sys.stdin
        return
    with open(path, encoding="utf-8") as f:
        yield from f


def format_timestamp(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def fence(content: str, lang: str = "") -> str:
    """長さに応じた三連バッククォート以上のフェンスでコードブロックを生成する。"""
    text = content.rstrip("\n")
    max_backticks = 0
    run = 0
    for ch in text:
        if ch == "`":
            run += 1
            max_backticks = max(max_backticks, run)
        else:
            run = 0
    fence_len = max(3, max_backticks + 1)
    bar = "`" * fence_len
    return f"{bar}{lang}\n{text}\n{bar}"


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        # 要約用なので改行・インデントを省いてコンパクト化する（AI解析用途）
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def is_pasted_slash_command(text: str) -> bool:
    """ターミナルからペーストされたスラッシュコマンド実行結果を判定する。

    `❯ /xxx` で始まる、または先頭行に `/` を含み `⎿` ボックス文字を含むテキストを対象とする。
    """
    stripped = text.lstrip()
    if stripped.startswith("❯ /") or stripped.startswith("> /"):
        return True
    lines = text.splitlines()
    if lines and "⎿" in text and "/" in lines[0]:
        return True
    return False


# tool_use input のうち「何をしたか」の文脈として残すべきキーの優先順位
TOOL_INPUT_SUMMARY_KEYS = (
    "file_path", "path", "notebook_path",
    "pattern", "query", "url",
    "command",
    "name_path", "relative_path", "substring",
    "symbol_name",
)


def compress_tool_input(inp: Any) -> Any:
    """tool_use input の長文キー（args/prompt/content/new_string/old_string/command 等）を頭尾圧縮する。

    - 識別系キー（file_path/url/pattern/skill/description 等）は一切触らない
    - 長大値のみ先頭/末尾を残して中間を `[... N chars truncated ...]` に置換
    - 元の dict は破壊せず、新しい dict を返す
    """
    if not isinstance(inp, dict):
        return inp
    out: dict[str, Any] = {}
    for k, v in inp.items():
        if k in TOOL_INPUT_LONG_KEYS and isinstance(v, str) and len(v) > TOOL_INPUT_LONG_THRESHOLD:
            omitted = len(v) - TOOL_INPUT_LONG_HEAD - TOOL_INPUT_LONG_TAIL
            out[k] = (
                v[:TOOL_INPUT_LONG_HEAD]
                + f"\n[... {omitted} chars truncated ...]\n"
                + v[-TOOL_INPUT_LONG_TAIL:]
            )
        else:
            out[k] = v
    return out


def _tool_use_inline(name: str, inp: dict[str, Any]) -> str | None:
    """tool_use を `ToolName: [...]` 形式の 1 行に圧縮する。

    主要な識別キー（file_path / command / pattern 等）がある場合はその値を角括弧で囲む。
    どの識別キーも見つからない複雑な input の場合は None を返し、呼び出し側で
    JSON フェンスにフォールバックする。

    例:
        Read   -> `Read: [/path/to/file]`
        Bash   -> `Bash: [make ci]`
        Agent  -> `Agent: [description=xxx | subagent_type=yyy]`
        Skill  -> `Skill: [implement]`
    """
    if not isinstance(inp, dict) or not inp:
        return f"{name}: []"
    # 単一値で完結するケース
    for key in ("file_path", "path", "notebook_path", "url"):
        if key in inp and isinstance(inp[key], str):
            return f"{name}: [{inp[key]}]"
    if "pattern" in inp and isinstance(inp["pattern"], str):
        extra = ""
        for k in ("path", "glob", "type"):
            if k in inp:
                extra = f" {k}={inp[k]}"
                break
        return f"{name}: [{inp['pattern']}{extra}]"
    if "query" in inp and isinstance(inp["query"], str):
        return f"{name}: [{inp['query'][:200]}]"
    if "command" in inp and isinstance(inp["command"], str):
        cmd = inp["command"].replace("\n", " ⏎ ")
        if len(cmd) > 200:
            cmd = cmd[:200] + "…"
        return f"{name}: [{cmd}]"
    if "skill" in inp and isinstance(inp["skill"], str):
        return f"{name}: [{inp['skill']}]"
    # Agent / AskUserQuestion / SendMessage 等
    if "description" in inp or "subagent_type" in inp:
        parts = []
        if "description" in inp:
            parts.append(str(inp["description"])[:120])
        if "subagent_type" in inp:
            parts.append(f"subagent={inp['subagent_type']}")
        return f"{name}: [{' | '.join(parts)}]"
    if "question" in inp and isinstance(inp["question"], str):
        q = inp["question"].replace("\n", " ⏎ ")[:200]
        return f"{name}: [{q}]"
    if "name_path" in inp and isinstance(inp["name_path"], str):
        return f"{name}: [{inp['name_path']}]"
    # Edit/Write などは file_path で上で拾われるのでここには来ない。
    # 識別キーが無いツールはフォールバックで JSON を残す。
    return None


def summarize_tool_input(inp: dict[str, Any] | None) -> str:
    """tool_use の input から「何を対象にしたか」を短く取り出す。"""
    if not isinstance(inp, dict):
        return ""
    parts: list[str] = []
    for key in TOOL_INPUT_SUMMARY_KEYS:
        if key in inp:
            val = inp[key]
            if isinstance(val, str):
                # command だけはやや長めを許容、その他は短縮
                limit = 200 if key == "command" else 120
                if len(val) > limit:
                    val = val[:limit] + "…"
                parts.append(f"{key}={val}")
            if len(parts) >= 2:
                break
    return " | ".join(parts)


def compress_tool_result(rendered: str, tool_name: str | None, is_error: bool,
                         tool_input: dict[str, Any] | None = None) -> str:
    """tool_result 本文を要約用に圧縮する。

    - エラー時は先頭 TOOL_RESULT_ERROR_HEAD_BYTES まで残す（診断に必要）
    - Read/Grep 等の「入力から推測可能」ツールは本文を削除しサマリのみ
      （このとき tool_input から file_path 等を抽出して省略メッセージに含める）
    - Bash 等は TOOL_RESULT_KEEP_LIMIT 以下ならそのまま、超過分は先頭/末尾のみ
    """
    n = len(rendered)
    if is_error:
        if n <= TOOL_RESULT_ERROR_HEAD_BYTES:
            return rendered
        return rendered[:TOOL_RESULT_ERROR_HEAD_BYTES] + f"\n\n[... {n - TOOL_RESULT_ERROR_HEAD_BYTES} chars truncated (error tail) ...]"

    if tool_name in TOOL_RESULT_DROP_BODY and n > 200:
        summary = summarize_tool_input(tool_input)
        if summary:
            return f"[... {tool_name} result body omitted: {n} chars | {summary} ...]"
        return f"[... {tool_name} result body omitted: {n} chars ...]"

    if n <= TOOL_RESULT_KEEP_LIMIT:
        return rendered

    head = rendered[:TOOL_RESULT_HEAD_BYTES]
    tail = rendered[-TOOL_RESULT_TAIL_BYTES:]
    omitted = n - TOOL_RESULT_HEAD_BYTES - TOOL_RESULT_TAIL_BYTES
    return f"{head}\n\n[... {omitted} chars truncated ...]\n\n{tail}"


def render_content_block(block: dict[str, Any],
                         tool_name_by_id: dict[str, str] | None = None,
                         tool_input_by_id: dict[str, dict[str, Any]] | None = None) -> list[str]:
    btype = block.get("type")
    out: list[str] = []

    if btype == "text":
        text = block.get("text", "").rstrip()
        if text:
            # assistant/user の発話テキストは Markdown 見出しや区切りを含むことがあり、
            # そのまま転記するとロールヘッダと階層が混ざって codex が誤読する。
            # fence で包んで literal 扱いにすることで、役割ヘッダ以外が構造解釈されないようにする。
            out.append(fence(text))
    elif btype == "thinking":
        thinking = block.get("thinking", "").rstrip()
        if thinking:
            out.append("(thinking)\n" + fence(thinking))
    elif btype == "tool_use":
        name = block.get("name", "unknown")
        if name in TOOL_USE_FULLY_SKIP:
            return out
        raw_input = block.get("input", {}) or {}
        inline = _tool_use_inline(name, raw_input)
        if inline is not None:
            out.append(inline)
        else:
            # 主要キーで1行化できない複雑なツールは従来通り JSON を残す（ただし圧縮）
            compressed = stringify(compress_tool_input(raw_input))
            out.append(f"`{name}`\n{fence(compressed, 'json')}")
    elif btype == "tool_result":
        tool_id = block.get("tool_use_id", "")
        tool_name = (tool_name_by_id or {}).get(tool_id) if tool_id else None
        is_error = block.get("is_error", False)
        # tool_use を 1 行化した時点で結果は重複情報になるため、成功時は全て省略する。
        # エラー時のみ診断用に本文を残す（tool_name + ERROR ヘッダ付き）。
        if not is_error:
            return out
        content = block.get("content", "")
        if isinstance(content, list):
            parts: list[str] = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c.get("text", ""))
                else:
                    parts.append(stringify(c))
            rendered = "\n\n".join(p for p in parts if p)
        else:
            rendered = stringify(content)
        tool_input = (tool_input_by_id or {}).get(tool_id) if tool_id else None
        rendered = compress_tool_result(rendered, tool_name, is_error, tool_input)
        label = f"`{tool_name}` ERROR" if tool_name else "ERROR"
        out.append(f"{label}\n{fence(rendered)}")
    elif btype == "image":
        out.append("[image] (省略)")
    else:
        out.append(f"[{btype}]\n\n{fence(stringify(block), 'json')}")

    return out


def render_message(record: dict[str, Any],
                   tool_name_by_id: dict[str, str] | None = None,
                   tool_input_by_id: dict[str, dict[str, Any]] | None = None) -> str | None:
    msg = record.get("message", {})
    role = msg.get("role", record.get("type", "unknown"))
    content = msg.get("content", "")

    blocks: list[str] = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict):
                blocks.extend(render_content_block(b, tool_name_by_id, tool_input_by_id))
    else:
        text = str(content).strip()
        if text:
            # user/assistant の素テキストも fence で literal 化してロール階層と分離する
            blocks.append(fence(text))

    if not blocks:
        return None

    ts = format_timestamp(record.get("timestamp"))
    header = f"## {role}"
    if ts:
        header += f" — {ts}"

    return header + "\n\n" + "\n\n".join(blocks)


def should_skip(record: dict[str, Any]) -> bool:
    if record.get("type") not in ("user", "assistant"):
        return True
    if record.get("isMeta"):
        return True

    content = record.get("message", {}).get("content")
    if isinstance(content, str):
        if any(tag in content for tag in LOCAL_COMMAND_TAGS):
            return True
        if is_pasted_slash_command(content):
            return True
    elif isinstance(content, list):
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        if texts and all(
            any(tag in t for tag in LOCAL_COMMAND_TAGS) or is_pasted_slash_command(t)
            for t in texts
        ):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) > 3 or any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__, file=sys.stderr)
        return 0

    input_path = argv[1] if len(argv) >= 2 else None
    output_path = argv[2] if len(argv) == 3 else None

    sections: list[str] = []
    session_id: str | None = None
    first_ts: str | None = None
    last_ts: str | None = None

    # 2パス構成: 1パス目は生のレコードを収集しつつ tool_use の id→name/input を記録
    records: list[dict[str, Any]] = []
    tool_name_by_id: dict[str, str] = {}
    tool_input_by_id: dict[str, dict[str, Any]] = {}

    for raw in iter_lines(input_path):
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"warn: 行をスキップしました: {e}", file=sys.stderr)
            continue

        session_id = session_id or record.get("sessionId")
        ts = record.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts

        # 1パス目: tool_use の id→name/input マッピングを構築
        content = record.get("message", {}).get("content")
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

        records.append(record)

    # 2パス目: マッピングを参照して圧縮しつつ render
    for record in records:
        if should_skip(record):
            continue
        section = render_message(record, tool_name_by_id, tool_input_by_id)
        if section:
            sections.append(section)

    meta_lines: list[str] = []
    if session_id:
        meta_lines.append(f"- session: `{session_id}`")
    if first_ts:
        meta_lines.append(f"- 開始: {format_timestamp(first_ts)}")
    if last_ts and last_ts != first_ts:
        meta_lines.append(f"- 最終: {format_timestamp(last_ts)}")
    if input_path:
        meta_lines.append(f"- source: `{input_path}`")

    output_parts: list[str] = ["# 会話履歴"]
    if meta_lines:
        output_parts.append("\n".join(meta_lines))
    output_parts.extend(sections)
    output = "\n\n".join(output_parts) + "\n"

    if output_path:
        out = Path(output_path)
    elif input_path:
        out = Path(input_path).with_suffix(".md")
    else:
        sys.stdout.write(output)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    print(f"wrote: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
