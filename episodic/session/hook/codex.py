"""Codex session JSONL handling for the episodic Stop hook."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

HOME = Path.home()
CODEX_SESSIONS = HOME / ".codex" / "sessions"
MAX_TEXT_CHARS = 4000
MAX_TOOL_OUTPUT_CHARS = 1200


def find_jsonl(session_id: str, cwd: str, transcript_path: str | None) -> Path | None:
    if transcript_path:
        p = Path(transcript_path).expanduser()
        if p.exists():
            return p
    if not session_id or not CODEX_SESSIONS.exists():
        return None
    candidates = sorted(
        CODEX_SESSIONS.glob(f"**/rollout-*{session_id}.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def looks_like_codex_jsonl(jsonl: Path) -> bool:
    try:
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                return record.get("type") == "session_meta" or "payload" in record
    except (OSError, json.JSONDecodeError):
        return False
    return False


def scan_metadata(jsonl: Path) -> dict[str, Any]:
    first_ts: str | None = None
    last_ts: str | None = None
    session_id: str | None = None
    cwd: str | None = None
    model = "unknown"
    message_count = 0
    user_prompt_count = 0

    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = record.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts

            payload = record.get("payload") or {}
            ptype = payload.get("type")
            if record.get("type") == "session_meta":
                session_id = session_id or payload.get("id")
                cwd = cwd or payload.get("cwd")
                first_ts = payload.get("timestamp") or first_ts
                model = payload.get("model") or payload.get("model_provider") or model
                continue

            if ptype == "message":
                role = payload.get("role")
                if role in ("user", "assistant"):
                    message_count += 1
                    if role == "user":
                        user_prompt_count += 1
            elif ptype == "user_message":
                message_count += 1
                user_prompt_count += 1
            elif ptype == "agent_message":
                message_count += 1
            elif ptype in ("function_call", "function_call_output", "custom_tool_call"):
                message_count += 1

    return {
        "session_id": session_id,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "git_branch": current_git_branch(cwd),
        "cwd": cwd or "",
        "message_count": message_count,
        "user_prompt_count": user_prompt_count,
        "model": model,
    }


def current_git_branch(cwd: str | None) -> str:
    if not cwd:
        return "unknown"
    head = Path(cwd) / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    if text.startswith("ref: refs/heads/"):
        return text.removeprefix("ref: refs/heads/")
    return text[:12] if text else "unknown"


def write_markdown(jsonl: Path, output: Path, jsonl_to_md: Path,
                   meta: dict[str, Any] | None = None) -> None:
    """JSONL を Markdown 化する。meta を渡すと scan_metadata の再スキャンを省略する。"""
    if meta is None:
        meta = scan_metadata(jsonl)
    sections: list[str] = ["# 会話履歴"]
    meta_lines: list[str] = []
    if meta.get("session_id"):
        meta_lines.append(f"- session: `{meta['session_id']}`")
    if meta.get("first_ts"):
        meta_lines.append(f"- 開始: {format_timestamp(meta['first_ts'])}")
    if meta.get("last_ts") and meta.get("last_ts") != meta.get("first_ts"):
        meta_lines.append(f"- 最終: {format_timestamp(meta['last_ts'])}")
    meta_lines.append(f"- source: `{jsonl}`")
    sections.append("\n".join(meta_lines))

    call_names: dict[str, str] = {}
    seen_messages: set[tuple[str, str]] = set()
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rendered = render_record(record, call_names, seen_messages)
            if rendered:
                sections.append(rendered)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def render_record(record: dict[str, Any], call_names: dict[str, str],
                  seen_messages: set[tuple[str, str]]) -> str | None:
    ts = format_timestamp(record.get("timestamp"))
    payload = record.get("payload") or {}
    ptype = payload.get("type")

    if ptype == "message":
        role = payload.get("role")
        if role not in ("user", "assistant"):
            return None
        text = render_content(payload.get("content"))
        if not text:
            return None
        if role == "user" and is_context_message(text):
            return None
        if is_duplicate_message(role, text, seen_messages):
            return None
        return section(role, ts, fence(text))

    if ptype == "user_message":
        text = str(payload.get("message") or "").strip()
        if is_duplicate_message("user", text, seen_messages):
            return None
        return section("user", ts, fence(text)) if text else None

    if ptype == "agent_message":
        text = str(payload.get("message") or "").strip()
        phase = payload.get("phase")
        role = "assistant" if not phase else f"assistant/{phase}"
        if is_duplicate_message("assistant", text, seen_messages):
            return None
        return section(role, ts, fence(text)) if text else None

    if ptype in ("function_call", "custom_tool_call"):
        name = str(payload.get("name") or "unknown")
        call_id = str(payload.get("call_id") or "")
        if call_id:
            call_names[call_id] = name
        arguments = payload.get("arguments", payload.get("input", ""))
        summary = summarize_arguments(arguments)
        return section("tool_call", ts, f"{name}: [{summary}]")

    if ptype == "function_call_output":
        call_id = str(payload.get("call_id") or "")
        name = call_names.get(call_id, "tool")
        output = truncate(str(payload.get("output") or ""), MAX_TOOL_OUTPUT_CHARS)
        return section("tool_result", ts, f"`{name}`\n{fence(output)}") if output else None

    if ptype == "tool_search_call":
        args = payload.get("arguments") or {}
        return section("tool_call", ts, f"tool_search: [{summarize_arguments(args)}]")

    if ptype == "tool_search_output":
        tools = payload.get("tools") or []
        return section("tool_result", ts, f"tool_search: {len(tools)} tools exposed")

    if ptype == "turn_aborted":
        return section("event", ts, "turn_aborted")

    return None


def render_content(content: Any) -> str:
    if isinstance(content, str):
        return truncate(content.strip(), MAX_TEXT_CHARS)
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        typ = item.get("type")
        if typ in ("input_text", "output_text", "text"):
            text = str(item.get("text") or "").strip()
            if text:
                parts.append(text)
        elif typ == "image":
            parts.append("[image] (省略)")
    return truncate("\n\n".join(parts).strip(), MAX_TEXT_CHARS)


def is_context_message(text: str) -> bool:
    stripped = text.lstrip()
    return (
        stripped.startswith("# AGENTS.md instructions")
        or "<environment_context>" in text
        or "<developer_context>" in text
    )


def is_duplicate_message(role: str, text: str, seen_messages: set[tuple[str, str]]) -> bool:
    key = ("assistant" if role.startswith("assistant") else role, text.strip())
    if not key[1]:
        return False
    if key in seen_messages:
        return True
    seen_messages.add(key)
    return False


def summarize_arguments(arguments: Any) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return one_line(truncate(arguments, 300))
    if isinstance(arguments, dict):
        for key in ("cmd", "command", "path", "file_path", "query", "q"):
            value = arguments.get(key)
            if isinstance(value, str) and value:
                return one_line(truncate(value, 300))
        return one_line(truncate(json.dumps(arguments, ensure_ascii=False, separators=(",", ":")), 300))
    return one_line(truncate(str(arguments), 300))


def section(role: str, ts: str, body: str) -> str:
    header = f"## {role}"
    if ts:
        header += f" — {ts}"
    return f"{header}\n\n{body}"


def format_timestamp(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def fence(content: str, lang: str = "") -> str:
    text = content.rstrip("\n")
    max_backticks = 0
    run = 0
    for ch in text:
        if ch == "`":
            run += 1
            max_backticks = max(max_backticks, run)
        else:
            run = 0
    bar = "`" * max(3, max_backticks + 1)
    return f"{bar}{lang}\n{text}\n{bar}"


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = max(0, limit - 120)
    tail = 80
    omitted = len(text) - head - tail
    return f"{text[:head]}\n[... {omitted} chars truncated ...]\n{text[-tail:]}"


def one_line(text: str) -> str:
    return " ".join(text.split())
