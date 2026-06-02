#!/usr/bin/env python3
"""wiki-runner: ingest-queue.jsonl に溜まった Raw を消化し Wiki を更新する。

bash wiki/wiki-runner.sh の Python 化。詳細仕様は同 bash ファイルのヘッダー参照。

Usage:
    wiki_runner.py [--memories-dir PATH] [--no-codex]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib import config as cfg
from lib import frontmatter as fm
from lib import wiki_dispatch
from lib import wiki_index
from lib import wiki_prompt
from lib import wiki_queue
from lib.codex_runner import CodexRunner, CodexResult
from lib.cocoindex_trigger import trigger_cocoindex_update
from lib.lockfile import MkdirLock
from lib.log_rotate import rotate_log_if_needed
from lib.notify import Notifier, default_notifier


SCRIPT_DIR = Path(__file__).resolve().parent
ENQUEUE_SCRIPT = SCRIPT_DIR / "enqueue.py"
INSTRUCTION_SESSION = SCRIPT_DIR / "codex-instruction.md"
INSTRUCTION_WEB = SCRIPT_DIR / "codex-instruction-web.md"
INSTRUCTION_MINUTES = SCRIPT_DIR / "codex-instruction-minutes.md"
INSTRUCTION_DIARY = SCRIPT_DIR / "codex-instruction-diary.md"
INSTRUCTION_EXTRACT_PEOPLE = SCRIPT_DIR / "codex-instruction-extract-people.md"
INSTRUCTION_PERSON = SCRIPT_DIR / "codex-instruction-person.md"
INSTRUCTION_ORG = SCRIPT_DIR / "codex-instruction-org.md"

DEFAULT_MODELS = {
    "session": "gpt-5.4",
    "web": "gpt-5.4-mini",
    "minutes": "gpt-5.4-mini",
    "diary": "gpt-5.4-mini",
    "people_extract": "gpt-5.4-mini",
    "person": "gpt-5.4-mini",
    "org": "gpt-5.4-mini",
}
MODEL_ENV = {
    "session": "CODEX_MEMORY_WIKI_MODEL_SESSION",
    "web": "CODEX_MEMORY_WIKI_MODEL_WEB",
    "minutes": "CODEX_MEMORY_WIKI_MODEL_MINUTES",
    "diary": "CODEX_MEMORY_WIKI_MODEL_DIARY",
    "people_extract": "CODEX_MEMORY_WIKI_MODEL_EXTRACT_PEOPLE",
    "person": "CODEX_MEMORY_WIKI_MODEL_PERSON",
    "org": "CODEX_MEMORY_WIKI_MODEL_ORG",
}


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class _Logger:
    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, msg: str) -> None:
        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{_now_iso()}] {msg}\n")
        except OSError:
            pass


def _env_int(name: str, default: int, log: _Logger | None = None) -> int:
    val = os.environ.get(name, "").strip()
    if not val:
        return default
    if not val.isdigit() or val == "0":
        if log:
            log(f"warn: invalid {name}='{val}'; falling back to {default}")
        return default
    return int(val)


def resolve_model_for_kind(kind: str) -> str:
    env_name = MODEL_ENV.get(kind)
    if env_name and (v := os.environ.get(env_name, "").strip()):
        return v
    return DEFAULT_MODELS.get(kind, DEFAULT_MODELS["session"])


def _sanitize_project(raw: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9_-]", "", raw)
    return out[:64] or "unknown"


def _read_first_field(raw_path: Path, field: str) -> str:
    """Raw md の frontmatter から指定フィールドを読み出す。"""
    try:
        front = fm.parse(raw_path)
    except OSError:
        return ""
    return front.get(field, "") or ""


def _yyyymm_from_raw(raw_path: Path, log: _Logger) -> str:
    date_raw = _read_first_field(raw_path, "date")
    if not date_raw:
        date_raw = raw_path.parent.name
    digits = re.sub(r"[^0-9]", "", date_raw)[:6]
    if len(digits) != 6:
        log(
            f"warn: cannot derive YYYYMM from raw '{raw_path}' (date='{date_raw}'); fallback to 'unknown'"
        )
        return "unknown"
    return digits


def _resolve_wiki_target(
    entry: dict,
    wiki_dir: Path,
    log: _Logger,
) -> tuple[str, Path | None, Path, str, str]:
    """エントリから (kind, wiki_target, instruction, label, project_or_slug) を解決する。

    エラー時は wiki_target=None を返す（呼出側で immediate failed 扱い）。
    """
    kind = entry.get("kind") or "session"
    raw_path = Path(entry.get("raw_path", ""))

    if kind == "session":
        project_raw = _read_first_field(raw_path, "project")
        project = _sanitize_project(project_raw)
        if project_raw and project != project_raw:
            log(f"warn: project sanitized: '{project_raw}' -> '{project}'")
        wiki_target = wiki_dir / "projects" / f"{project}.md"
        return kind, wiki_target, INSTRUCTION_SESSION, project, project
    if kind == "web":
        return kind, wiki_dir / "references.md", INSTRUCTION_WEB, "references", "references"
    if kind == "minutes":
        ym = _yyyymm_from_raw(raw_path, log)
        return kind, wiki_dir / "minutes" / f"{ym}.md", INSTRUCTION_MINUTES, f"minutes/{ym}", ym
    if kind == "diary":
        ym = _yyyymm_from_raw(raw_path, log)
        return kind, wiki_dir / "diary" / f"{ym}.md", INSTRUCTION_DIARY, f"diary/{ym}", ym
    if kind == "people_extract":
        # 抽出ジョブは書き込み無し。CWD のために people/ を流用する。
        return (
            kind,
            wiki_dir / "people" / ".extract-placeholder",
            INSTRUCTION_EXTRACT_PEOPLE,
            "people_extract",
            "people_extract",
        )
    if kind == "person":
        slug = entry.get("slug", "")
        if not slug:
            log(f"  error: person entry without slug: raw={raw_path}")
            return kind, None, INSTRUCTION_PERSON, "person:missing-slug", ""
        wiki_target = wiki_dir / "people" / f"{slug}.md"
        # 防衛層: パスが wiki/people/ 配下に留まっているか
        real_target = os.path.realpath(wiki_target)
        wiki_people_real = os.path.realpath(wiki_dir / "people") + "/"
        if not (real_target.startswith(wiki_people_real) and real_target.endswith(".md")):
            log(f"  error: person slug escapes wiki/people/: slug='{slug}' target='{wiki_target}'")
            return kind, None, INSTRUCTION_PERSON, "person:unsafe-slug", slug
        return kind, wiki_target, INSTRUCTION_PERSON, f"people/{slug}", slug
    if kind == "org":
        slug = entry.get("slug", "")
        if not slug:
            log(f"  error: org entry without slug: raw={raw_path}")
            return kind, None, INSTRUCTION_ORG, "org:missing-slug", ""
        wiki_target = wiki_dir / "orgs" / f"{slug}.md"
        # 防衛層: パスが wiki/orgs/ 配下に留まっているか
        real_target = os.path.realpath(wiki_target)
        wiki_orgs_real = os.path.realpath(wiki_dir / "orgs") + "/"
        if not (real_target.startswith(wiki_orgs_real) and real_target.endswith(".md")):
            log(f"  error: org slug escapes wiki/orgs/: slug='{slug}' target='{wiki_target}'")
            return kind, None, INSTRUCTION_ORG, "org:unsafe-slug", slug
        return kind, wiki_target, INSTRUCTION_ORG, f"orgs/{slug}", slug

    log(f"warn: unknown kind '{kind}' for {raw_path}; treating as session")
    return ("session", wiki_dir / "projects" / "unknown.md", INSTRUCTION_SESSION, "unknown", "unknown")


def _entry_identity(entry: dict) -> tuple[str, str, str]:
    kind = entry.get("kind") or ""
    slug = entry.get("slug", "") if kind == "person" else ""
    return (entry.get("raw_path") or "", kind, slug)


def cleanup_trashbox(trashbox_dir: Path, retain_days: int, log: _Logger, dry_run: bool = False) -> int:
    """trashbox 配下で retain_days より古いエントリを削除。0 で無効。"""
    if retain_days <= 0:
        return 0
    if not trashbox_dir.is_dir():
        return 0
    cutoff = time.time() - retain_days * 86400
    removed = 0
    for child in trashbox_dir.iterdir():
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff:
            continue
        if dry_run:
            log(f"trashbox cleanup (dry-run): would remove {child} (older than {retain_days}d)")
        else:
            log(f"trashbox cleanup: removing {child} (older than {retain_days}d)")
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
            except OSError as e:
                log(f"trashbox cleanup: failed to remove {child}: {e}")
                continue
        removed += 1
    if removed:
        if dry_run:
            log(f"trashbox cleanup (dry-run): {removed} entr(y|ies) would be removed")
        else:
            log(f"trashbox cleanup: removed={removed}")
    return removed


def _build_groups(
    entries: list[dict],
    wiki_dir: Path,
    log: _Logger,
) -> tuple[
    list[tuple[str, Path, Path, str, str, str, list[dict]]],
    list[dict],
]:
    """pending entries を (kind, target, instruction, label, project, model) で
    グルーピングし、immediate failures (raw 不在 / 設定エラー等) を別途返す。

    返り値:
        groups: 各要素 = (kind, target, instruction, label, project, model, [entries])
        immediate_failures: process 前に決まる失敗 (label, raw, kind, slug を含む dict)
    """
    from collections import OrderedDict

    immediate_failures: list[dict] = []
    grouped: "OrderedDict[tuple, list[dict]]" = OrderedDict()

    for entry in entries:
        raw_path = Path(entry.get("raw_path", ""))
        slug_from_queue = entry.get("slug", "") if entry.get("kind") == "person" else ""
        if not raw_path.is_file():
            log(f"skip: raw file missing (kind={entry.get('kind')}): {raw_path}")
            immediate_failures.append(
                {
                    "status": "failed",
                    "label": f"missing:{raw_path.name}",
                    "raw_path": str(raw_path),
                    "kind": entry.get("kind") or "",
                    "slug": slug_from_queue,
                }
            )
            continue
        kind, wiki_target, instruction, label, project = _resolve_wiki_target(entry, wiki_dir, log)
        if wiki_target is None:
            immediate_failures.append(
                {
                    "status": "failed",
                    "label": label,
                    "raw_path": str(raw_path),
                    "kind": kind,
                    "slug": slug_from_queue,
                }
            )
            continue
        if not Path(instruction).is_file():
            log(f"  error: instruction template not found: {instruction}")
            immediate_failures.append(
                {
                    "status": "failed",
                    "label": label,
                    "raw_path": str(raw_path),
                    "kind": kind,
                    "slug": slug_from_queue,
                }
            )
            continue
        model = resolve_model_for_kind(kind)
        key = (kind, str(wiki_target), str(instruction), label, project, model)
        grouped.setdefault(key, []).append(entry)

    groups: list[tuple[str, Path, Path, str, str, str, list[dict]]] = []
    for key, items in grouped.items():
        kind, target_str, instruction_str, label, project, model = key
        groups.append(
            (kind, Path(target_str), Path(instruction_str), label, project, model, items)
        )
    return groups, immediate_failures


def _process_batch_job(
    *,
    job_id: str,
    kind: str,
    wiki_target: Path,
    instruction: Path,
    label: str,
    project: str,
    model: str,
    entries: list[dict],
    target_lock_root: Path,
    log: _Logger,
    skip_codex: bool,
    codex_runner_factory,
    log_file: Path,
    target_lock_timeout: int,
) -> list[dict]:
    """1 batch を処理し、結果（list of result dict）を返す。

    結果 dict 形式: {"status": "success"|"failed", "label", "raw_path", "kind", "slug"}
    """
    slug = project if kind in ("person", "org") else ""
    raw_count = len(entries)

    import hashlib

    lock_id = hashlib.sha256(str(wiki_target).encode("utf-8")).hexdigest()
    lock_dir = target_lock_root / f"{lock_id}.lock.d"

    def _result(status: str) -> list[dict]:
        out = []
        for e in entries:
            out.append(
                {
                    "status": status,
                    "label": label,
                    "raw_path": e.get("raw_path", ""),
                    "kind": kind,
                    "slug": e.get("slug", "") if kind == "person" else "",
                }
            )
        return out

    # target lock を取得
    lock = MkdirLock(lock_dir)
    acquired = False
    waited = 0
    while not acquired:
        if lock.acquire():
            acquired = True
            break
        if waited >= target_lock_timeout:
            log(f"warn: target lock timeout after {target_lock_timeout}s: {lock_dir}")
            return _result("failed")
        time.sleep(1)
        waited += 1
    try:
        log(f"processing batch: id={job_id} kind={kind} count={raw_count} model={model} -> {wiki_target}")
        if skip_codex:
            log(f"  --no-codex: skipped Codex invocation batch={job_id}")
            return _result("success")

        # prompt 組立 & codex 呼び出し
        wiki_target.parent.mkdir(parents=True, exist_ok=True)
        cwd_dir = wiki_target.parent
        web_search_enabled = False
        if kind == "person":
            mentions = []
            for entry in entries:
                mention = {
                    "name": entry.get("name", ""),
                    "slug": entry.get("slug", ""),
                    "aliases": entry.get("aliases", []),
                    "context": entry.get("context", ""),
                    "source_kind": entry.get("source_kind", ""),
                    "source_raw": entry.get("raw_path", ""),
                }
                sr = mention["source_raw"]
                if sr:
                    mention["source_basename"] = Path(sr).name
                    mention["source_date"] = Path(sr).parent.name
                mentions.append(mention)
            prompt_text = wiki_prompt.build_combined_prompt_person(
                instruction, wiki_target, mentions, slug
            )
        elif kind == "org":
            mentions = []
            for entry in entries:
                mention = {
                    "name": entry.get("name", ""),
                    "slug": entry.get("slug", ""),
                    "aliases": entry.get("aliases", []),
                    "category": entry.get("category", ""),
                    "context": entry.get("context", ""),
                    "source_kind": entry.get("source_kind", ""),
                    "source_raw": entry.get("raw_path", ""),
                }
                sr = mention["source_raw"]
                if sr:
                    mention["source_basename"] = Path(sr).name
                    mention["source_date"] = Path(sr).parent.name
                mentions.append(mention)
            # 既存 org wiki に web_checked_at があれば web 検索しない（冪等性確保）。
            web_checked_at = ""
            if wiki_target.is_file():
                web_checked_at = (fm.parse(wiki_target).get("web_checked_at", "") or "").strip()
            web_search_enabled = web_checked_at in ("", "null", "~", "None")
            prompt_text = wiki_prompt.build_combined_prompt_org(
                instruction, wiki_target, mentions, slug, web_search_enabled
            )
        else:
            raw_paths = [Path(e.get("raw_path", "")) for e in entries]
            prompt_text = wiki_prompt.build_combined_prompt_batch(
                instruction, wiki_target, raw_paths, kind, project=project
            )

        prompt_path = Path(tempfile.mkstemp(prefix="memory-wiki.", suffix=".md")[1])
        capture_path = Path(tempfile.mkstemp(prefix="memory-wiki-cap.", suffix=".log")[1])
        try:
            prompt_path.write_text(prompt_text, encoding="utf-8")
            sandbox_mode = "read-only" if kind == "people_extract" else "workspace-write"
            factory_kwargs = {"model": model, "sandbox_mode": sandbox_mode, "cwd_dir": cwd_dir}
            if kind == "org" and web_search_enabled:
                # 未裏取りの組織のみ codex の web 検索を有効化する。
                factory_kwargs["web_search"] = True
            runner = codex_runner_factory(**factory_kwargs)
            try:
                result: CodexResult = runner.run(prompt_path, log_file, capture_path)
            except (FileNotFoundError, PermissionError, OSError) as e:
                log(f"  codex invocation error batch={job_id}: {e}")
                return _result("failed")

            if result.returncode != 0:
                log(f"  codex failed batch={job_id} (rc={result.returncode})")
                return _result("failed")

            if kind == "people_extract":
                # capture から JSON 抽出して enqueue
                raw_for_dispatch = Path(entries[0].get("raw_path", "")) if entries else Path()
                source_kind = entries[0].get("source_kind", "") if entries else ""
                parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
                    capture_path,
                    raw_path=raw_for_dispatch,
                    source_kind=source_kind,
                    enqueue_script=ENQUEUE_SCRIPT,
                    log=log,
                )
                if parsed_ok:
                    log(f"  people_extract success batch={job_id} appended={appended}")
                    return _result("success")
                log(f"  people_extract JSON parse failed batch={job_id} (capture={capture_path})")
                return _result("failed")

            if kind == "person":
                log(f"  codex success batch={job_id} (person slug={slug})")
                return _result("success")

            if kind == "org":
                log(f"  codex success batch={job_id} (org slug={slug})")
                return _result("success")

            log(f"  codex success batch={job_id}")
            return _result("success")
        finally:
            prompt_path.unlink(missing_ok=True)
            capture_path.unlink(missing_ok=True)
    finally:
        lock.release()


def _default_codex_runner_factory(timeout_seconds: int):
    def make(
        model: str, sandbox_mode: str, cwd_dir: Path, web_search: bool = False
    ) -> CodexRunner:
        return CodexRunner(
            model=model,
            effort="low",
            timeout_seconds=timeout_seconds,
            sandbox_mode=sandbox_mode,
            # subagent（multi_agent）は full-history fork でトークン消費が数倍に
            # 膨らむため無効（CodexRunner の既定 multi_agent=False を継承する）。
            web_search=web_search,
        )

    return make


def run(
    memories_dir: Path | None = None,
    no_codex: bool = False,
    *,
    notifier: Notifier | None = None,
    codex_runner_factory=None,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
    max_iterations: int | None = None,
    batch_size: int | None = None,
    lead_max_raw: int | None = None,
    parallelism: int | None = None,
    max_attempts: int | None = None,
    retry_base_seconds: int | None = None,
    max_raw_missing_attempts: int | None = None,
    raw_missing_retry_base_seconds: int | None = None,
    target_lock_timeout: int | None = None,
    processing_timeout_seconds: int | None = None,
    trigger_cocoindex: bool = True,
) -> int:
    """wiki-runner 本体。bash 版と同じ制御フローで queue を消化する。"""
    if memories_dir is None:
        memories_dir = Path(os.environ.get("MEMORIES_DIR", "/Volumes/memory"))
    memories_dir = Path(memories_dir)

    state_dir = state_dir or (Path.home() / ".local" / "share" / "episodic" / "state")
    log_dir = log_dir or (Path.home() / ".local" / "state" / "episodic" / "logs")
    queue_path = state_dir / "ingest-queue.jsonl"
    deadletter_path = state_dir / "ingest-deadletter.jsonl"
    lock_dir = state_dir / "lock.d"
    target_lock_root = state_dir / "wiki-target-locks"
    log_file = log_dir / "wiki-runner.log"
    wiki_dir = memories_dir / "wiki"
    trashbox_dir = memories_dir / "trashbox"

    state_dir.mkdir(parents=True, exist_ok=True)
    target_lock_root.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "projects").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "minutes").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "diary").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "people").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "orgs").mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    for p in (state_dir, target_lock_root, log_dir):
        try:
            os.chmod(p, 0o700)
        except OSError:
            pass

    log = _Logger(log_file)
    rotate_log_if_needed(log_file)
    rotate_log_if_needed(log_dir / "cocoindex-update.log")

    log(f"wiki-runner start: pid={os.getpid()} memories={memories_dir}")

    # housekeeping
    retain_days_str = os.environ.get("MEMORIES_TRASHBOX_RETAIN_DAYS", "30")
    try:
        retain_days = int(retain_days_str)
    except ValueError:
        log(f"trashbox cleanup: invalid MEMORIES_TRASHBOX_RETAIN_DAYS='{retain_days_str}'; skipping")
        retain_days = 0
    dry_run = os.environ.get("MEMORIES_TRASHBOX_DRY_RUN", "0") == "1"
    cleanup_trashbox(trashbox_dir, retain_days, log, dry_run=dry_run)

    # codex バイナリ確認（no_codex でなければ）。失敗時は no_codex に降格。
    skip_codex = no_codex
    if not skip_codex:
        binary = os.environ.get("CODEX_BINARY") or shutil.which("codex")
        if not binary or not os.access(binary, os.X_OK):
            log(f"warn: codex binary not executable: '{binary or ''}'; falling back to --no-codex")
            skip_codex = True
        else:
            real = os.path.realpath(binary)
            for prefix in ("/tmp/", "/var/tmp/", "/private/tmp/", "/private/var/tmp/"):
                if real.startswith(prefix):
                    log(f"error: codex binary in world-writable dir: {real}")
                    return 126

    runner_lock = MkdirLock(lock_dir)
    if not runner_lock.acquire():
        pid = runner_lock._read_pid()
        log(f"skip: another wiki-runner is processing (pid={pid})")
        return 0

    notifier = notifier or default_notifier("Episodic Wiki")
    total_processed = 0
    total_failed = 0
    all_processed_labels: list[str] = []
    all_failed_labels: list[str] = []

    try:
        if not queue_path.exists() or queue_path.stat().st_size == 0:
            log("skip: queue is empty")
            return 0

        if max_raw_missing_attempts is None:
            max_raw_missing_attempts = _env_int("MEMORIES_WIKI_MAX_RAW_MISSING_ATTEMPTS", 5, log)
        if raw_missing_retry_base_seconds is None:
            raw_missing_retry_base_seconds = _env_int(
                "MEMORIES_WIKI_RAW_MISSING_RETRY_BASE_SECONDS", 60, log
            )

        wiki_queue.purge_missing_entries(
            queue_path,
            log=log,
            max_raw_missing_attempts=max_raw_missing_attempts,
            retry_base_seconds=raw_missing_retry_base_seconds,
        )

        if not queue_path.exists() or queue_path.stat().st_size == 0:
            log("skip: queue is empty (after purge)")
            return 0

        if max_iterations is None:
            max_iterations = _env_int("MEMORIES_WIKI_MAX_SELF_POLL", 10, log)
        if batch_size is None:
            batch_size = _env_int("MEMORIES_WIKI_BATCH_SIZE", 8, log)
        if lead_max_raw is None:
            # 1 target = 1 lead job が原則。lead 内 subagent が raw を分担するため
            # batch_size では割らず、この安全弁を超えたときだけ分割する。
            lead_max_raw = _env_int("MEMORIES_WIKI_LEAD_MAX_RAW", 40, log)
        if parallelism is None:
            parallelism = _env_int("MEMORIES_WIKI_PARALLELISM", 3, log)
        if max_attempts is None:
            max_attempts = _env_int("MEMORIES_WIKI_MAX_ATTEMPTS", 5, log)
        if retry_base_seconds is None:
            retry_base_seconds = _env_int("MEMORIES_WIKI_RETRY_BASE_SECONDS", 300, log)
        if target_lock_timeout is None:
            target_lock_timeout = _env_int(
                "MEMORIES_WIKI_TARGET_LOCK_TIMEOUT_SECONDS", 7200, log
            )
        if processing_timeout_seconds is None:
            processing_timeout_seconds = _env_int(
                "MEMORIES_WIKI_PROCESSING_TIMEOUT_SECONDS", 3600, log
            )

        timeout_seconds = cfg.resolve_wiki_codex_timeout_seconds()
        factory = codex_runner_factory or _default_codex_runner_factory(timeout_seconds)

        prev_identities: set[tuple[str, str, str]] | None = None
        iteration = 0

        while True:
            iteration += 1
            if iteration > max_iterations:
                log(f"warn: reached MAX_ITERATIONS={max_iterations} in self-poll; deferring rest to next runner")
                break
            if iteration > 1:
                log(f"self-poll iteration={iteration} (re-scanning queue for late additions)")

            pending = wiki_queue.read_pending_entries(
                queue_path, processing_timeout_seconds=processing_timeout_seconds
            )
            if not pending:
                if iteration == 1:
                    log("skip: no pending entries")
                break

            current_ids = {_entry_identity(e) for e in pending}
            if prev_identities is not None and current_ids == prev_identities:
                log(f"warn: no progress in iteration {iteration} (pending unchanged); breaking self-poll")
                break
            prev_identities = current_ids

            # mark processing
            wiki_queue.mark_processing(queue_path, [_entry_identity(e) for e in pending])

            groups, immediate_failures = _build_groups(pending, wiki_dir, log)

            # 1 target = 1 lead job 化。lead が multi_agent で raw を subagent に分担する
            # ため batch_size では割らない。ただし raw 件数が lead_max_raw を超える場合のみ、
            # プロンプト肥大とリソース過負荷を避けるため安全弁として分割する。
            batch_jobs: list[
                tuple[str, str, Path, Path, str, str, str, list[dict]]
            ] = []
            job_no = 0
            for kind, target, instruction, label, project, model, items in groups:
                step = lead_max_raw if (lead_max_raw > 0 and len(items) > lead_max_raw) else len(items)
                step = step or 1
                for i in range(0, len(items), step):
                    job_no += 1
                    sub = items[i : i + step]
                    batch_jobs.append(
                        (f"job-{job_no}", kind, target, instruction, label, project, model, sub)
                    )

            results: list[dict] = list(immediate_failures)

            if batch_jobs:
                def _runjob(job):
                    jid, kind, target, instr, lab, proj, model, entries = job
                    return _process_batch_job(
                        job_id=jid,
                        kind=kind,
                        wiki_target=target,
                        instruction=instr,
                        label=lab,
                        project=proj,
                        model=model,
                        entries=entries,
                        target_lock_root=target_lock_root,
                        log=log,
                        skip_codex=skip_codex,
                        codex_runner_factory=factory,
                        log_file=log_file,
                        target_lock_timeout=target_lock_timeout,
                    )

                if parallelism <= 1:
                    for job in batch_jobs:
                        results.extend(_runjob(job))
                else:
                    with ThreadPoolExecutor(max_workers=parallelism) as ex:
                        futs = [ex.submit(_runjob, job) for job in batch_jobs]
                        for fut in futs:
                            try:
                                results.extend(fut.result())
                            except Exception as e:
                                log(f"warn: batch job raised: {e}")

            # 集計（missing: ラベルは race 由来の deferred なので失敗扱いしない）
            iter_processed = 0
            iter_failed = 0
            for r in results:
                if r["status"] == "success":
                    iter_processed += 1
                    all_processed_labels.append(r["label"])
                elif r["status"] == "failed":
                    if r.get("label", "").startswith("missing:"):
                        continue
                    iter_failed += 1
                    all_failed_labels.append(r["label"])

            wiki_queue.update_queue_after_results(
                queue_path,
                results,
                max_attempts=max_attempts,
                retry_base_seconds=retry_base_seconds,
                max_raw_missing_attempts=max_raw_missing_attempts,
                raw_missing_retry_base_seconds=raw_missing_retry_base_seconds,
            )
            total_processed += iter_processed
            total_failed += iter_failed

            # 自己ポーリングは update_queue_after_results 後の queue 状態に依存。
            # 次イテレーションの read_pending_entries が空 / 同一なら break する。

        # index.md 再生成
        try:
            wiki_index.regenerate_index(wiki_dir, memories_dir)
        except Exception as e:
            log(f"warn: index regeneration failed: {e}")

        log(f"done: total_processed={total_processed} total_failed={total_failed} iterations={iteration}")

        if total_processed > 0 and trigger_cocoindex:
            try:
                trigger_cocoindex_update(str(memories_dir), log_dir=log_dir)
            except Exception as e:
                log(f"warn: cocoindex trigger failed: {e}")

        if total_failed > 0:
            summary = _unique_labels(all_failed_labels)
            notifier.notify("失敗", f"失敗: {summary or '?'} (log: {log_file})", "Basso")
        elif total_processed > 0:
            summary = _unique_labels(all_processed_labels)
            notifier.notify("完了", f"更新: {summary or '?'}", "Glass")

        return 0
    finally:
        runner_lock.release()


def _unique_labels(labels: list[str]) -> str:
    seen: list[str] = []
    for la in labels:
        if la and la not in seen:
            seen.append(la)
    return ", ".join(seen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--memories-dir", default=None)
    parser.add_argument("--no-codex", action="store_true")
    args = parser.parse_args(argv)
    memories_dir = Path(args.memories_dir) if args.memories_dir else None
    return run(memories_dir=memories_dir, no_codex=args.no_codex)


if __name__ == "__main__":
    sys.exit(main())
