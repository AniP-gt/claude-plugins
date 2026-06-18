#!/usr/bin/env python3
"""組織 Wiki（wiki/orgs/<slug>.md）の web 裏取り保守 CLI。

web_checked_at が未設定（null）の組織について、codex exec の web 検索
（`-c tools.web_search=true`）で公式情報（事業内容・公式 URL）を **1 回だけ** 裏取りし、
frontmatter の website / web_status / web_checked_at と「## 概要」を更新する。

設計方針:
  - 検索は codex 側で行い、**Claude のトークンは使わない**。
  - 冪等性: web_checked_at が既に入っている組織は再検索しない（--force で強制）。
  - 見つからない場合は web_status=not_found を記録し web_checked_at を刻む（以後 skip）。
  - codex は sandbox 有効（read-only）で呼ぶ。`--dangerously-bypass-...` は使わない。
    web_search はサーバ側ツールのため read-only sandbox でも機能する。

Usage:
    python wiki/org_web_verify.py [--memories-dir PATH] [--model gpt-5.4-mini]
        [--only SLUG] [--force] [--dry-run] [--timeout SECONDS]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib import frontmatter as fm  # noqa: E402

# codex に返させる最終 JSON のスキーマ。
_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "found": {"type": "boolean"},
        "official_name": {"type": "string"},
        "website": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["found", "official_name", "website", "summary"],
}

_UNCHECKED = ("", "null", "~", "None")


def _build_prompt(title: str, aliases: str, category: str) -> str:
    return (
        f"次の組織について web 検索で公式情報を調べてください。\n"
        f"- 名称: {title}\n"
        f"- 別名: {aliases}\n"
        f"- 種別: {category}\n\n"
        "公式サイト・信頼できる情報源から、事業内容や所在地などの公的情報を確認し、"
        "最終メッセージを指定スキーマの JSON で返してください。\n"
        "- found: 信頼できる情報で組織を特定できたら true、できなければ false\n"
        "- official_name: 正式名称（不明なら入力の名称）\n"
        "- website: 公式サイトの URL（不明なら空文字）\n"
        "- summary: 事業内容・特徴を 1〜2 文で（80 字以内目安、個人の連絡先等の機微情報は含めない）\n"
        "特定できない場合は found=false とし、推測で URL や概要を埋めないこと。"
    )


def run_codex_search(
    title: str,
    aliases: str,
    category: str,
    model: str,
    timeout: int,
    codex_bin: str | None = None,
) -> dict | None:
    """codex exec を web 検索付きで起動し、構造化 JSON dict を返す。失敗時 None。"""
    binary = codex_bin or os.environ.get("CODEX_BINARY") or "codex"
    schema_fd, schema_path = tempfile.mkstemp(prefix="org-verify-schema.", suffix=".json")
    cap_fd, cap_path = tempfile.mkstemp(prefix="org-verify-cap.", suffix=".json")
    os.close(schema_fd)
    os.close(cap_fd)
    try:
        Path(schema_path).write_text(json.dumps(_OUTPUT_SCHEMA), encoding="utf-8")
        cmd = [
            binary,
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-c",
            "tools.web_search=true",
            "-m",
            model,
            "-c",
            "model_reasoning_effort=low",
            "--output-schema",
            schema_path,
            "-o",
            cap_path,
        ]
        prompt = _build_prompt(title, aliases, category)
        try:
            subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        try:
            raw = Path(cap_path).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # capture に前置きが混ざる場合に備え、最後の JSON オブジェクトを拾う。
            start = raw.rfind("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None
    finally:
        Path(schema_path).unlink(missing_ok=True)
        Path(cap_path).unlink(missing_ok=True)


def _update_overview(text: str, summary: str, today: str) -> str:
    """「## 概要」直下に公式情報の 1 行を挿入（既に同種の行があれば置換）。"""
    line = f"- 公式情報（web 裏取り {today}）: {summary}"
    lines = text.split("\n")
    out: list[str] = []
    inserted = False
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == "## 概要" and not inserted:
            # 見出し直後の空行を保持しつつ、既存の公式情報行があれば飛ばして差し替える。
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                out.append(lines[j])
                j += 1
            # 既存の「公式情報（web 裏取り...」行を除去
            while j < len(lines) and lines[j].startswith("- 公式情報（web 裏取り"):
                j += 1
            out.append(line)
            inserted = True
            i = j
            continue
        i += 1
    if not inserted:
        out.append("")
        out.append(line)
    return "\n".join(out)


def verify_org_file(
    path: Path,
    search_fn: Callable[[str, str, str], dict | None],
    today: str,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """1 つの org ファイルを裏取りし結果ステータス文字列を返す。

    Returns: "skip" | "verified" | "not_found" | "error"
    """
    front = fm.parse(path)
    checked = (front.get("web_checked_at", "") or "").strip()
    if checked not in _UNCHECKED and not force:
        return "skip"

    title = front.get("title", "") or path.stem
    aliases = front.get("aliases", "")
    category = front.get("category", "")

    result = search_fn(title, aliases, category)
    if result is None:
        return "error"

    found = bool(result.get("found"))
    # web 由来文字列は untrusted。改行を除去して frontmatter 行注入・本文 markdown
    # 構造破壊（見出し挿入等）を防ぎ、長さも防御的に clamp する。
    def _sanitize(v: object, limit: int) -> str:
        s = str(v or "").strip().replace("\r", " ").replace("\n", " ")
        return s[:limit]

    website = _sanitize(result.get("website"), 300)
    summary = _sanitize(result.get("summary"), 200)

    if found and website:
        patches = {"website": website, "web_status": "verified", "web_checked_at": today}
        status = "verified"
    else:
        patches = {"web_status": "not_found", "web_checked_at": today}
        status = "not_found"

    if dry_run:
        return status

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "error"
    new_text = fm.patch_text(text, patches)
    if new_text is None:
        return "error"
    if status == "verified" and summary:
        new_text = _update_overview(new_text, summary, today)
    path.write_text(new_text, encoding="utf-8")
    return status


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--memories-dir",
        default=Path(os.environ.get("MEMORIES_DIR", "/Volumes/memory")),
        type=Path,
    )
    p.add_argument("--model", default="gpt-5.4-mini")
    p.add_argument("--only", default=None, help="特定 slug のみ処理")
    p.add_argument("--force", action="store_true", help="web_checked_at 済みも再検索")
    p.add_argument("--dry-run", action="store_true", help="書き込まず判定のみ")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args(argv)

    orgs_dir = Path(args.memories_dir) / "wiki" / "orgs"
    if not orgs_dir.is_dir():
        print(f"orgs dir not found: {orgs_dir}", file=sys.stderr)
        return 1

    today = datetime.now().strftime("%Y-%m-%d")
    files = sorted(p for p in orgs_dir.glob("*.md") if not p.name.startswith("."))
    if args.only:
        files = [f for f in files if f.stem == args.only]

    def search_fn(title: str, aliases: str, category: str) -> dict | None:
        return run_codex_search(title, aliases, category, args.model, args.timeout)

    counts = {"skip": 0, "verified": 0, "not_found": 0, "error": 0}
    for f in files:
        status = verify_org_file(f, search_fn, today, force=args.force, dry_run=args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        print(f"[{status}] {f.stem}")
    print(
        f"done: verified={counts['verified']} not_found={counts['not_found']} "
        f"skip={counts['skip']} error={counts['error']}"
        + (" (dry-run)" if args.dry_run else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
