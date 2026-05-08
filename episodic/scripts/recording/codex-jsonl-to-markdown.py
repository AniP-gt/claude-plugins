#!/usr/bin/env python3
"""Codex CLI 会話履歴の JSONL を Markdown に変換する。

Claude Code の JSONL 変換は `jsonl-to-markdown.py` に残し、Codex CLI 固有の
`session_meta` / `response_item` 形式だけをここで扱う。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Iterable

HELPER_PATH = Path(__file__).with_name("jsonl-to-markdown.py")
spec = importlib.util.spec_from_file_location("claude_jsonl_to_markdown", HELPER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"failed to load helper: {HELPER_PATH}")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def iter_lines(path: str | None) -> Iterable[str]:
    if path is None:
        yield from sys.stdin
        return
    with open(path, encoding="utf-8") as f:
        yield from f


def parse_json_object(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def codex_content_blocks(content: Any) -> list[str]:
    blocks: list[str] = []
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            btype = item.get("type")
            text = item.get("text")
            if btype in ("input_text", "output_text", "text") and isinstance(text, str) and text.strip():
                blocks.append(helper.fence(text.strip()))
            elif btype == "image":
                blocks.append("[image] (省略)")
    elif isinstance(content, str) and content.strip():
        blocks.append(helper.fence(content.strip()))
    return blocks


def is_process_error(output: str) -> bool:
    marker = "Process exited with code "
    idx = output.find(marker)
    if idx == -1:
        return False
    tail = output[idx + len(marker):idx + len(marker) + 8]
    return not tail.startswith("0")


def render_codex_record(record: dict[str, Any],
                        tool_name_by_id: dict[str, str],
                        tool_input_by_id: dict[str, dict[str, Any]]) -> str | None:
    if record.get("type") != "response_item":
        return None
    item = record.get("payload") or {}
    if not isinstance(item, dict):
        return None

    ts = helper.format_timestamp(record.get("timestamp"))
    itype = item.get("type")

    if itype == "message":
        role = item.get("role", "unknown")
        if role not in ("user", "assistant"):
            return None
        blocks = codex_content_blocks(item.get("content"))
        if not blocks:
            return None
        header = f"## {role}"
        if ts:
            header += f" — {ts}"
        return header + "\n\n" + "\n\n".join(blocks)

    if itype == "function_call":
        name = item.get("name", "unknown")
        if name in helper.TOOL_USE_FULLY_SKIP:
            return None
        raw_args = item.get("arguments")
        parsed_args = parse_json_object(raw_args)
        inline = helper._tool_use_inline(name, parsed_args or {})
        if inline is not None:
            body = inline
        elif parsed_args is not None:
            body = f"`{name}`\n{helper.fence(helper.stringify(helper.compress_tool_input(parsed_args)), 'json')}"
        else:
            body = f"`{name}`\n{helper.fence(helper.stringify(raw_args), 'json')}"
        header = "## tool_call"
        if ts:
            header += f" — {ts}"
        return header + "\n\n" + body

    if itype == "function_call_output":
        call_id = item.get("call_id", "")
        tool_name = tool_name_by_id.get(call_id) if call_id else None
        output = helper.stringify(item.get("output", ""))
        if not output.strip():
            return None
        tool_input = tool_input_by_id.get(call_id) if call_id else None
        rendered = helper.compress_tool_result(output, tool_name, is_process_error(output), tool_input)
        label = f"`{tool_name}` result" if tool_name else "tool_result"
        header = "## tool_result"
        if ts:
            header += f" — {ts}"
        return header + "\n\n" + label + "\n" + helper.fence(rendered)

    return None


def main(argv: list[str]) -> int:
    if len(argv) > 3 or any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__, file=sys.stderr)
        return 0

    input_path = argv[1] if len(argv) >= 2 else None
    output_path = argv[2] if len(argv) == 3 else None
    records: list[dict[str, Any]] = []
    tool_name_by_id: dict[str, str] = {}
    tool_input_by_id: dict[str, dict[str, Any]] = {}
    session_id: str | None = None
    first_ts: str | None = None
    last_ts: str | None = None

    for raw in iter_lines(input_path):
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"warn: 行をスキップしました: {e}", file=sys.stderr)
            continue

        if record.get("type") == "session_meta":
            payload = record.get("payload") or {}
            if isinstance(payload, dict):
                session_id = session_id or payload.get("id")

        ts = record.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts

        payload = record.get("payload") or {}
        if isinstance(payload, dict) and payload.get("type") == "function_call":
            call_id = payload.get("call_id")
            name = payload.get("name")
            parsed_args = parse_json_object(payload.get("arguments"))
            if call_id and name:
                tool_name_by_id[call_id] = name
            if call_id and parsed_args is not None:
                tool_input_by_id[call_id] = parsed_args

        records.append(record)

    sections = [
        section
        for section in (
            render_codex_record(record, tool_name_by_id, tool_input_by_id)
            for record in records
        )
        if section
    ]

    meta_lines: list[str] = []
    if session_id:
        meta_lines.append(f"- session: `{session_id}`")
    if first_ts:
        meta_lines.append(f"- 開始: {helper.format_timestamp(first_ts)}")
    if last_ts and last_ts != first_ts:
        meta_lines.append(f"- 最終: {helper.format_timestamp(last_ts)}")
    if input_path:
        meta_lines.append(f"- source: `{input_path}`")

    output_parts: list[str] = ["# 会話履歴"]
    if meta_lines:
        output_parts.append("\n".join(meta_lines))
    output_parts.extend(sections)
    output = "\n\n".join(output_parts) + "\n"

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
        print(f"wrote: {out}", file=sys.stderr)
        return 0

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
