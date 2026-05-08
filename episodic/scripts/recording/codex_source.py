"""Codex CLI session source adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


def _safe_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_session_meta(jsonl: Path, log: Callable[[str], None]) -> dict[str, Any]:
    try:
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "session_meta":
                    continue
                payload = record.get("payload")
                return payload if isinstance(payload, dict) else {}
    except OSError as e:
        log(f"warn: codex session meta read failed: {jsonl}: {e}")
    return {}


def find_latest_jsonl(cwd: str, start_epoch: float | None, log: Callable[[str], None]) -> Path | None:
    if not CODEX_SESSIONS_DIR.exists():
        log(f"codex sessions dir not found: {CODEX_SESSIONS_DIR}")
        return None

    threshold = (start_epoch - 10) if start_epoch else 0
    candidates: list[Path] = []
    try:
        for p in CODEX_SESSIONS_DIR.rglob("*.jsonl"):
            try:
                if p.stat().st_mtime >= threshold:
                    candidates.append(p)
            except OSError:
                continue
    except OSError as e:
        log(f"warn: codex sessions scan failed: {e}")
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    fallback = candidates[0] if candidates else None
    for p in candidates[:200]:
        meta = read_session_meta(p, log)
        if not cwd or meta.get("cwd") == cwd:
            return p
    return fallback


def build_payload(args: list[str], log: Callable[[str], None]) -> dict[str, Any]:
    exit_status = os.environ.get("CODEX_EXIT_STATUS") or (args[0] if args else "")
    cwd = os.environ.get("CODEX_WRAPPER_CWD") or os.environ.get("PWD") or os.getcwd()
    start_epoch = _safe_float(os.environ.get("CODEX_WRAPPER_START_EPOCH"))
    jsonl = find_latest_jsonl(cwd, start_epoch, log)
    if jsonl is None:
        log(f"error: Codex JSONL not found cwd={cwd} status={exit_status}")
        return {}

    meta = read_session_meta(jsonl, log)
    session_id = meta.get("id") or ""
    payload = {
        "session_id": session_id,
        "cwd": meta.get("cwd") or cwd,
        "transcript_path": str(jsonl),
        "codex_exit_status": exit_status,
        "source": "codex-wrapper",
    }
    log(f"codex payload synthesized: session={session_id} cwd={payload['cwd']} transcript={jsonl} status={exit_status}")
    return payload


def scan_metadata(jsonl: Path) -> dict[str, Any]:
    first_ts: str | None = None
    last_ts: str | None = None
    cwd: str | None = None
    message_count = 0
    user_prompt_count = 0
    model_counts: dict[str, int] = {}

    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = record.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts

            if record.get("type") == "session_meta":
                payload = record.get("payload") or {}
                if isinstance(payload, dict):
                    cwd = cwd or payload.get("cwd")
                    model = payload.get("model")
                    if model:
                        model_counts[model] = model_counts.get(model, 0) + 1
                continue

            payload = record.get("payload") or {}
            if not isinstance(payload, dict) or payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in ("user", "assistant") or not payload.get("content"):
                continue
            message_count += 1
            if role == "user":
                user_prompt_count += 1

    model = max(model_counts, key=model_counts.get) if model_counts else "unknown"
    return {
        "first_ts": first_ts,
        "last_ts": last_ts,
        "git_branch": "unknown",
        "cwd": cwd or "",
        "message_count": message_count,
        "user_prompt_count": user_prompt_count,
        "model": model,
    }
