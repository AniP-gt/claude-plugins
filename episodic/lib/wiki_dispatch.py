"""people_extract の Codex capture から person を取り出し enqueue.py を呼ぶ。

bash wiki-runner.sh の dispatch_person_enqueues_from_capture を Python 化。
capture file には `<<<PEOPLE_JSON_BEGIN>>> ... <<<PEOPLE_JSON_END>>>` で
JSON ペイロード（{"people": [...]} 形式）が囲まれている。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable


_MARKER_RE = re.compile(
    r"<<<PEOPLE_JSON_BEGIN>>>\s*(.*?)\s*<<<PEOPLE_JSON_END>>>",
    re.DOTALL,
)


def dispatch_person_enqueues_from_capture(
    capture_file: Path,
    raw_path: Path | str,
    source_kind: str,
    enqueue_script: Path,
    log: Callable[[str], None] | None = None,
    python_executable: str | None = None,
) -> tuple[bool, int, int]:
    """capture file をパースして人物ごとに enqueue.py --kind person を呼ぶ。

    Returns: (parsed_ok, appended, errors)
        parsed_ok=False は capture / JSON が読めなかった場合（失敗扱い）。
        appended は enqueue 成功件数、errors は失敗件数。
    """
    cap = Path(capture_file)
    if not cap.exists():
        if log:
            log("dispatch_person_enqueues: capture file missing")
        return False, 0, 0

    try:
        text = cap.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        if log:
            log(f"dispatch_person_enqueues: capture read failed: {e}")
        return False, 0, 0

    m = _MARKER_RE.search(text)
    if not m:
        if log:
            log("dispatch_person_enqueues: no JSON markers in capture")
        return False, 0, 0

    try:
        payload = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        if log:
            log(f"dispatch_person_enqueues: JSON parse error: {e}")
        return False, 0, 0

    people = payload.get("people") if isinstance(payload, dict) else None
    if not isinstance(people, list):
        if log:
            log("dispatch_person_enqueues: invalid people field")
        return False, 0, 0

    py = python_executable or sys.executable
    errors = 0
    appended = 0
    for p in people:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        slug = (p.get("slug") or "").strip()
        # source_raw は payload 優先、未指定なら呼び出し側 raw_path を fallback で使う
        source_raw = (p.get("source_raw") or str(raw_path) or "").strip()
        s_kind = (p.get("source_kind") or source_kind or "").strip()
        if not (name and slug and source_raw and s_kind in ("minutes", "diary")):
            if log:
                log(
                    f"dispatch_person_enqueues: skip incomplete entry: "
                    f"name={name!r} slug={slug!r} source_raw={source_raw!r} source_kind={s_kind!r}"
                )
            continue
        aliases = p.get("aliases") or []
        aliases_str = ",".join(a for a in aliases if isinstance(a, str) and a.strip())
        context = (p.get("context") or "")[:500]
        cmd = [
            py,
            str(enqueue_script),
            source_raw,
            "--kind",
            "person",
            "--name",
            name,
            "--slug",
            slug,
            "--source-kind",
            s_kind,
            "--aliases",
            aliases_str,
            "--context",
            context,
        ]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            errors += 1
            if log:
                log(f"dispatch_person_enqueues: enqueue exception slug={slug}: {e}")
            continue
        if cp.returncode != 0:
            errors += 1
            if log:
                log(f"dispatch_person_enqueues: enqueue failed (rc={cp.returncode}) slug={slug}: {cp.stderr.strip()}")
        else:
            appended += 1

    if log:
        log(f"dispatch_person_enqueues: appended={appended} errors={errors}")
    return errors == 0, appended, errors
