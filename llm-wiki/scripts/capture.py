"""セッション終了時に、会話から wiki に残す候補を抜き出して raw/inbox/ に保存する。

SessionEnd hook から別プロセスで起動される（llm_wiki.py capture）。ページは更新しない。
候補は次のセッションの開始時に、/llm-wiki:ingest の手順で確認なしに整理される。
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

PROMPT = """あなたはソフトウェア開発チームの記録係です。下の <conversation> は、リポジトリ {project} で行われた Claude Code のセッションです。
このリポジトリの知識 wiki に残す価値のある「候補」だけを抜き出してください。

残す価値があるもの:
- 設計判断（何をどう決めたか、なぜか、却下した案）
- 障害・不具合の原因と対処
- コードや docs からは分かりにくいハマりどころ、仕様、運用上の注意
- 実測値や確認済みの事実（日付・Issue/PR 番号つき）

残さないもの:
- 作業の手順そのもの、雑談、コマンドの出力、一時的な進捗
- 一般的なプログラミング知識
- 下の <existing_index> に既にある内容（新しい事実が加わった場合だけ残す）
- 秘密情報（トークン、パスワード、鍵、個人の連絡先）

出力ルール:
- 残す候補が無ければ、NONE とだけ出力する。
- 候補があれば Markdown で、候補ごとに次の形式で書く。前置きや締めの文は書かない。

## <短いタイトル>
- 種別: decision | problem | gotcha | fact
- 内容: <1〜5行。事実だけ。推測は「推測:」と書く>
- 根拠: <会話で確認された根拠。ファイルパス、PR/Issue 番号、コマンド結果など>
- 確度: 高 | 中 | 低
- 関連しそうな既存ページ: <[[ページ名]] またはなし>

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
    """(role, text) の列と、最後に見えた git ブランチを返す。ツール入出力・思考・メタ行は除く。"""
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
    return body if len(body) <= max_chars else "…（前半省略）\n\n" + body[-max_chars:]


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
    # 再開したセッションは会話が前回の上位集合なので、同じセッションの古い候補は置き換える
    for old in inbox.glob(f"*-{session_id[:8]}.md"):
        old.unlink()
    dest = inbox / f"{now:%Y-%m-%d-%H%M}-{session_id[:8]}.md"
    header = (f"> 出典: Claude Code セッション `{session_id}`（{found['project']}"
              f"{', branch ' + branch if branch else ''}）を {now:%Y-%m-%d %H:%M} に自動抽出。"
              f"未検証の候補。/llm-wiki:ingest で整理する。\n\n")
    dest.write_text(header + output + "\n", encoding="utf-8")
    log(f"saved {label}: {dest}")
    return 0
