"""Claude Code session JSONL handling for the episodic Stop hook."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

HOME = Path.home()


def encode_cwd(cwd: str) -> str:
    """cwdをClaude Codeのprojectsディレクトリ命名規則に変換する。"""
    return cwd.replace("/", "-")


def find_jsonl(session_id: str, cwd: str, transcript_path: str | None) -> Path | None:
    if transcript_path:
        p = Path(transcript_path).expanduser()
        if p.exists():
            return p
    if session_id and cwd:
        candidate = HOME / ".claude" / "projects" / encode_cwd(cwd) / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


def scan_metadata(jsonl: Path) -> dict[str, Any]:
    first_ts: str | None = None
    last_ts: str | None = None
    git_branch: str | None = None
    cwd: str | None = None
    message_count = 0
    user_prompt_count = 0
    model_counts: dict[str, int] = {}

    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts

            git_branch = git_branch or d.get("gitBranch")
            cwd = cwd or d.get("cwd")

            rtype = d.get("type")
            if rtype in ("user", "assistant") and not d.get("isMeta"):
                msg = d.get("message", {})
                content = msg.get("content")
                if isinstance(content, str):
                    if (
                        "<local-command-caveat>" in content
                        or "<command-name>" in content
                        or "<local-command-stdout>" in content
                    ):
                        continue
                    stripped = content.lstrip()
                    if stripped.startswith("❯ /") or stripped.startswith("> /"):
                        continue
                message_count += 1
                if rtype == "user":
                    user_prompt_count += 1
                model = (d.get("message") or {}).get("model")
                if model:
                    model_counts[model] = model_counts.get(model, 0) + 1

    model = max(model_counts, key=model_counts.get) if model_counts else "unknown"
    return {
        "session_id": None,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "git_branch": git_branch or "unknown",
        "cwd": cwd or "",
        "message_count": message_count,
        "user_prompt_count": user_prompt_count,
        "model": model,
    }


def write_markdown(jsonl: Path, output: Path, jsonl_to_md: Path) -> None:
    subprocess.run(
        ["python3", str(jsonl_to_md), str(jsonl), str(output)],
        check=True,
        timeout=60,
    )
