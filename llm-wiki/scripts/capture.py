"""At session end, extract candidates worth keeping in the wiki from the conversation and save them to raw/inbox/.

Started as a separate process from the SessionEnd hook (llm_wiki.py capture). Does not update pages.
At the start of the next session, the candidates are triaged without asking, following /llm-wiki:ingest.
"""
import datetime
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

GUARD_ENV = "LLM_WIKI_CAPTURE"
LOG_PATH = Path("~/.config/llm-wiki/capture.log")
DEFAULTS = {"enabled": False, "model": "sonnet", "min_chars": 3000, "max_chars": 80000, "timeout": 300}
MESSAGE_MAX_CHARS = 4000
TAG_RE = re.compile(r"<(system-reminder|command-[a-z-]+|local-command-[a-z-]+|task-notification)>.*?</\1>", re.S)
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "<redacted-private-key>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted-aws-key>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<redacted-api-key>"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "<redacted-slack-token>"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)(\s*[:=]\s*)(\S+)"), r"\1\2<redacted>"),
]

PROMPT = """You are the record keeper for a software development team. The <conversation> below is a Claude Code session in the repository {project}.
Extract only the "candidates" worth keeping in this repository's knowledge wiki.

Worth keeping:
- Design decisions (what was decided and how, why, and rejected alternatives)
- Causes of and fixes for incidents and bugs
- Gotchas, specs, and operational notes that are hard to see from the code or docs
- Measured values and confirmed facts (with dates and Issue/PR numbers)

Not worth keeping:
- The work steps themselves, small talk, command output, transient progress
- General programming knowledge
- Anything already in <existing_index> below (keep it only when a new fact was added)
- Secrets (tokens, passwords, keys, personal contact details)

Output rules:
- If there is nothing worth keeping, output only NONE.
- Otherwise, write Markdown with one entry per candidate in the format below. Do not write any introduction or closing.
- Write the candidates in English (the wiki is written in English). Translate even when the conversation is in Japanese. Keep code, identifiers, paths, commands, error messages, and proper names exactly as they appear.

## <short title>
- Type: decision | problem | gotcha | fact
- Content: <1-5 lines. Facts only. Mark guesses with "Speculation:">
- Evidence: <evidence confirmed in the conversation: file paths, PR/Issue numbers, command results, etc.>
- Confidence: high | medium | low
- Related existing pages: <[[page name]] or none>

<existing_index>
{index}
</existing_index>

<conversation>
{conversation}
</conversation>
"""


def settings(config):
    merged = dict(DEFAULTS)
    merged.update(config.get("capture") or {})
    return merged


def log(message):
    try:
        path = LOG_PATH.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {message}\n")
    except OSError:
        pass


def redact(text):
    for pattern, repl in SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def message_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def read_transcript(path):
    """Return a list of (role, text) and the last git branch seen. Excludes tool input/output, thinking, and meta lines."""
    turns, branch = [], ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") not in ("user", "assistant") or entry.get("isMeta") or entry.get("isSidechain"):
                continue
            branch = entry.get("gitBranch") or branch
            text = TAG_RE.sub("", message_text((entry.get("message") or {}).get("content"))).strip()
            if text:
                turns.append((entry["type"], text[:MESSAGE_MAX_CHARS]))
    return turns, branch


def build_conversation(turns, max_chars):
    lines = [f"[{role}] {text}" for role, text in turns]
    body = "\n\n".join(lines)
    return body if len(body) <= max_chars else "… (earlier part omitted)\n\n" + body[-max_chars:]


def summarize(prompt, model, timeout):
    env = dict(os.environ, **{GUARD_ENV: "1"})
    cmd = ["claude", "-p", "--model", model, "--setting-sources", "project", "--tools", "",
           "--no-session-persistence", "--disable-slash-commands"]
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                timeout=timeout, cwd=tmp, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"claude exit {result.returncode}: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def run(found, config, transcript, session_id, index_text):
    opts = settings(config)
    label = f"{found['project']} session={session_id[:8]}"
    turns, branch = read_transcript(transcript)
    conversation = redact(build_conversation(turns, opts["max_chars"]))
    if len(conversation) < opts["min_chars"]:
        log(f"skip {label}: chars={len(conversation)}")
        return 0
    prompt = PROMPT.format(project=found["project"], index=index_text, conversation=conversation)
    try:
        output = redact(summarize(prompt, opts["model"], opts["timeout"]))
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        log(f"error {label}: {e}")
        return 1
    if not output or output.upper().startswith("NONE"):
        log(f"none {label}")
        return 0
    now = datetime.datetime.now()
    inbox = Path(found["wiki"]) / "raw" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    # A resumed session's conversation is a superset of the previous one, so replace older candidates from the same session
    for old in inbox.glob(f"*-{session_id[:8]}.md"):
        old.unlink()
    dest = inbox / f"{now:%Y-%m-%d-%H%M}-{session_id[:8]}.md"
    header = (f"> Source: Claude Code session `{session_id}` ({found['project']}"
              f"{', branch ' + branch if branch else ''}), auto-extracted at {now:%Y-%m-%d %H:%M}. "
              f"Unverified candidates. Triage them with /llm-wiki:ingest.\n\n")
    dest.write_text(header + output + "\n", encoding="utf-8")
    log(f"saved {label}: {dest}")
    return 0
