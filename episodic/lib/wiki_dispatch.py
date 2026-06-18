"""people_extract の Codex capture から person / org を取り出し enqueue.py を呼ぶ。

bash wiki-runner.sh の dispatch_person_enqueues_from_capture を Python 化。
capture file には `<<<PEOPLE_JSON_BEGIN>>> ... <<<PEOPLE_JSON_END>>>` で
JSON ペイロード（{"people": [...], "orgs": [...]} 形式）が囲まれている。
people は kind=person、orgs は kind=org として enqueue.py へ dispatch する。
orgs キーが無い旧形式の capture でも従来どおり people のみ dispatch する（後方互換）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable


_MARKER_RE = re.compile(
    r"<<<PEOPLE_JSON_BEGIN>>>\s*(.*?)\s*<<<PEOPLE_JSON_END>>>",
    re.DOTALL,
)


def _memories_root(raw_path: Path | str) -> str | None:
    """trusted な raw_path から memories ルート（`/.../raw` の親）を導出する。

    Codex 由来の source_raw が memories 配下に収まるかを検証するための基準。
    raw_path に `raw` ディレクトリ成分が無く判定できない場合は None を返す。
    """
    parts = Path(raw_path).parts
    if "raw" in parts:
        i = parts.index("raw")
        if i > 0:
            return os.path.realpath(str(Path(*parts[:i])))
    return None


def _within_root(path_str: str, root: str | None) -> bool:
    """path_str が root 配下か判定する。root=None（判定不能）なら True（既存挙動維持）。"""
    if not root:
        return True
    try:
        rp = os.path.realpath(path_str)
    except OSError:
        return False
    return rp == root or rp.startswith(root + os.sep)


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

    # orgs は任意キー。無ければ空リスト（旧形式 capture との後方互換）。
    orgs = payload.get("orgs") if isinstance(payload, dict) else None
    if orgs is None:
        orgs = []
    elif not isinstance(orgs, list):
        if log:
            log("dispatch_person_enqueues: invalid orgs field; ignoring")
        orgs = []

    py = python_executable or sys.executable
    errors = 0
    appended = 0

    def _run_enqueue(cmd: list[str], slug: str) -> None:
        nonlocal errors, appended
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            errors += 1
            if log:
                log(f"dispatch_person_enqueues: enqueue exception slug={slug}: {e}")
            return
        if cp.returncode != 0:
            errors += 1
            if log:
                log(
                    f"dispatch_person_enqueues: enqueue failed (rc={cp.returncode}) slug={slug}: "
                    f"{cp.stderr.strip()}"
                )
        else:
            appended += 1

    # Codex 由来 source_raw のパストラバーサル検証基準（trusted な raw_path から導出）。
    trusted_root = _memories_root(raw_path)

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
        if not _within_root(source_raw, trusted_root):
            if log:
                log(f"dispatch_person_enqueues: skip source_raw outside memories root: {source_raw!r}")
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
        _run_enqueue(cmd, slug)

    valid_categories = ("company", "hospital", "government", "academic", "other")
    for o in orgs:
        if not isinstance(o, dict):
            continue
        name = (o.get("name") or "").strip()
        slug = (o.get("slug") or "").strip()
        source_raw = (o.get("source_raw") or str(raw_path) or "").strip()
        s_kind = (o.get("source_kind") or source_kind or "").strip()
        if not (name and slug and source_raw and s_kind in ("minutes", "diary")):
            if log:
                log(
                    f"dispatch_person_enqueues: skip incomplete org entry: "
                    f"name={name!r} slug={slug!r} source_raw={source_raw!r} source_kind={s_kind!r}"
                )
            continue
        if not _within_root(source_raw, trusted_root):
            if log:
                log(f"dispatch_person_enqueues: skip org source_raw outside memories root: {source_raw!r}")
            continue
        aliases = o.get("aliases") or []
        aliases_str = ",".join(a for a in aliases if isinstance(a, str) and a.strip())
        context = (o.get("context") or "")[:500]
        category = (o.get("category") or "other").strip()
        if category not in valid_categories:
            category = "other"
        cmd = [
            py,
            str(enqueue_script),
            source_raw,
            "--kind",
            "org",
            "--name",
            name,
            "--slug",
            slug,
            "--source-kind",
            s_kind,
            "--aliases",
            aliases_str,
            "--category",
            category,
            "--context",
            context,
        ]
        _run_enqueue(cmd, slug)

    if log:
        log(f"dispatch_person_enqueues: appended={appended} errors={errors}")
    return errors == 0, appended, errors
