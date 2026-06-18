"""YAML frontmatter の単純 parser / patcher。

resolve_collision.py から共通切出。`key: value` の単純行のみ扱う薄い実装。
ネスト構造や複数行値は扱わない。
"""
from __future__ import annotations

import re
from pathlib import Path


_FM_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")


def parse(path: Path) -> dict[str, str]:
    """frontmatter を dict で返す。frontmatter 不在なら空 dict。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return parse_text(text)


def parse_text(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fm = text[4:end]
    out: dict[str, str] = {}
    for line in fm.split("\n"):
        m = _FM_LINE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        comment_pos = value.find(" #")
        if comment_pos >= 0:
            value = value[:comment_pos].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key] = value
    return out


def patch(path: Path, patches: dict[str, str]) -> None:
    """既存 .md の frontmatter を patch（指定キー置換、不在ならフロントマター末尾に追記）。

    frontmatter が無いファイルは何もしない。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    new_text = patch_text(text, patches)
    if new_text is None:
        return
    path.write_text(new_text, encoding="utf-8")


def patch_text(text: str, patches: dict[str, str]) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fm_block = text[4:end]
    body = text[end:]
    lines = fm_block.split("\n")
    applied: set[str] = set()
    new_lines = []
    for ln in lines:
        m = _FM_LINE.match(ln)
        if m and m.group(1) in patches:
            new_lines.append(f"{m.group(1)}: {patches[m.group(1)]}")
            applied.add(m.group(1))
        else:
            new_lines.append(ln)
    for key, value in patches.items():
        if key not in applied:
            new_lines.append(f"{key}: {value}")
    new_fm = "\n".join(new_lines)
    return f"---\n{new_fm}{body}"
