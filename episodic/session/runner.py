#!/usr/bin/env python3
"""session 要約 Codex ランナー（bash runner.sh の Python 化）。

hook.py から spawn_runner で起動される。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib import config as cfg
from lib import frontmatter as fm
from lib import path_resolver as pr
from lib.codex_runner import CodexRunner, CodexResult
from lib.log_rotate import rotate_log_if_needed
from lib.notify import Notifier, default_notifier
from lib.snapshot import SnapshotResult, save_source_snapshot

PLUGIN_ROOT = REPO_ROOT
SCRIPTS_DIR = Path(__file__).resolve().parent
LOG_DIR_LOCAL = Path.home() / ".local" / "state" / "episodic" / "logs"
LOG_FILE = LOG_DIR_LOCAL / "session-runner.log"
RETRY_QUEUE_PY = SCRIPTS_DIR / "retry_queue.py"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
EFFORT_VALID = {"minimal", "low", "medium", "high", "xhigh"}


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _log(msg: str) -> None:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{_now_iso()}] {msg}\n")
    except OSError:
        pass


def _pick_latest_codex_md(session_dir: Path) -> tuple[Path | None, str | None]:
    """SESSION_DIR から最新 *.codex.md を選び (path, ts) を返す。"""
    if not session_dir.is_dir():
        return None, None
    candidates = sorted(
        session_dir.glob("*.codex.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None, None
    latest = candidates[0]
    ts = latest.name[: -len(".codex.md")]
    return latest, ts


def _load_meta(meta_path: Path | None) -> dict[str, str]:
    if not meta_path or not meta_path.is_file():
        return {}
    try:
        with meta_path.open(encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return {}
    result: dict[str, str] = {}
    for k in ("session_id", "cwd", "transcript_path", "first_ts", "report_path", "is_staged", "snapshot_path"):
        v = data.get(k, "")
        if isinstance(v, bool):
            v = "1" if v else "0"
        result[k] = str(v) if v is not None else ""
    return result


_CLASSIFY_TAIL_BYTES = 64 * 1024  # 末尾 200 行は十分この範囲に収まる


def _classify_failure_reason() -> str:
    # ログ全文ではなく末尾 64KB だけ seek して読む（巨大ログでのメモリ/IO を抑制）。
    try:
        with LOG_FILE.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - _CLASSIFY_TAIL_BYTES))
            data = f.read()
        text = data.decode("utf-8", errors="replace")
    except OSError:
        return "unknown"
    recent = "\n".join(text.splitlines()[-200:])
    low = recent.lower()
    if re.search(r"you've hit your usage limit|usage limit|rate[ -]?limit", low):
        return "usage_limit"
    if re.search(r"unauthorized|invalid api key|authentication|not logged in", low):
        return "auth_failure"
    return "unknown"


def _retry_queue_upsert(meta: dict[str, str], reason: str) -> None:
    sid = meta.get("session_id", "")
    if not sid:
        return
    if not UUID_RE.match(sid):
        _log(f"warn: skip retry queue upsert (invalid session_id): {sid}")
        return
    if not RETRY_QUEUE_PY.is_file():
        _log(f"warn: retry_queue.py not found at {RETRY_QUEUE_PY}")
        return
    args = [
        sys.executable,
        str(RETRY_QUEUE_PY),
        "upsert",
        "--cwd",
        meta.get("cwd", ""),
        "--transcript",
        meta.get("transcript_path", ""),
        "--first-ts",
        meta.get("first_ts", ""),
        "--report-path",
        meta.get("report_path", ""),
    ]
    if meta.get("is_staged", "") == "1":
        args.append("--is-staged")
    args += ["--reason", reason, "--", sid]
    try:
        subprocess.run(args, check=False, capture_output=True, text=True, timeout=30)
        _log(f"retry queue upserted: session={sid} reason={reason}")
    except (OSError, subprocess.SubprocessError) as e:
        _log(f"warn: retry queue upsert failed: session={sid}: {e}")


def _retry_queue_remove(meta: dict[str, str]) -> None:
    sid = meta.get("session_id", "")
    if not sid or not UUID_RE.match(sid):
        return
    if not RETRY_QUEUE_PY.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(RETRY_QUEUE_PY), "remove", "--", sid],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _enforce_supersedes_integrity(report: Path) -> None:
    if not report.is_file():
        return
    try:
        text = report.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if not text.startswith("---\n"):
        return
    end = text.find("\n---", 4)
    if end == -1:
        return
    fm_text = text[4:end]
    body = text[end:]
    raw_value = None
    for line in fm_text.split("\n"):
        m = re.match(r"^supersedes\s*:\s*(.*)$", line)
        if m:
            raw_value = m.group(1).strip()
            break
    if raw_value is None or raw_value in ("null", "~", "None", "", "'null'", '"null"'):
        return
    value = raw_value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    self_ref = value == str(report)
    exists = Path(value).exists() if value else False
    if self_ref:
        new_fm = re.sub(r"^supersedes\s*:.*$", "supersedes: null", fm_text, flags=re.MULTILINE)
        report.write_text(f"---\n{new_fm}{body}", encoding="utf-8")
        _log(f"enforce_supersedes: self-reference removed in {report}")
    elif value and not exists:
        _log(f"enforce_supersedes: warn: revision path does not exist: value={value} report={report}")


def _summarize_report(report: Path) -> str:
    front = fm.parse(report)
    project = front.get("project", "?") or "?"
    title = front.get("title", "")
    if title:
        return f"{project} — {title}"
    return project


def _trigger_memory_wiki(raw_path: Path) -> None:
    enqueue = PLUGIN_ROOT / "wiki" / "enqueue.py"
    if not enqueue.is_file():
        _log(f"warn: enqueue.py not found: {enqueue}")
        return
    try:
        subprocess.run(
            [sys.executable, str(enqueue), str(raw_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        _log(f"enqueued to wiki ingest: {raw_path}")
    except (OSError, subprocess.SubprocessError) as e:
        _log(f"warn: wiki enqueue failed for {raw_path}: {e}")
        return

    py_kick = PLUGIN_ROOT / "wiki" / "kick_runner.py"
    sh_kick = PLUGIN_ROOT / "wiki" / "kick-runner.sh"
    if py_kick.is_file():
        cmd = [sys.executable, str(py_kick)]
    elif sh_kick.is_file() and os.access(sh_kick, os.X_OK):
        cmd = [str(sh_kick)]
    else:
        return
    log_file = LOG_DIR_LOCAL / "wiki-runner.log"
    try:
        with log_file.open("ab") as f:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except (OSError, FileNotFoundError):
        pass


def _cleanup_session_dir(session_dir: Path | None, latest_ts: str | None, session_id: str | None) -> None:
    if not session_dir or not session_dir.is_dir():
        return
    pending_root = Path.home() / ".local" / "state" / "episodic" / "pending"
    try:
        session_dir.resolve().relative_to(pending_root.resolve())
    except (ValueError, OSError):
        return

    if latest_ts and session_id:
        latest_md = session_dir / f"{latest_ts}.codex.md"
        if latest_md.is_file():
            latest_mtime = latest_md.stat().st_mtime
            # codex 実行中に届いた Stop は *.payload.json しか残さない（重処理は
            # finalize 側）ため、codex.md と payload.json の両方を再 finalize 判定に含める。
            newer_candidates = list(session_dir.glob("*.codex.md")) + list(
                session_dir.glob("*.payload.json")
            )
            for child in newer_candidates:
                try:
                    if child.stat().st_mtime > latest_mtime:
                        _log(f"respawn finalize for newer timestamp: {child}")
                        lock_dir = session_dir / ".lock"
                        if lock_dir.exists():
                            shutil.rmtree(lock_dir, ignore_errors=True)
                        debounce = session_dir / ".debounce.pid"
                        if debounce.exists():
                            debounce.unlink(missing_ok=True)
                        hook_py = SCRIPTS_DIR / "hook.py"
                        with LOG_FILE.open("ab") as f:
                            subprocess.Popen(
                                [sys.executable, str(hook_py), "--finalize", session_id],
                                stdin=subprocess.DEVNULL,
                                stdout=f,
                                stderr=subprocess.STDOUT,
                                start_new_session=True,
                                close_fds=True,
                            )
                        return
                except OSError:
                    continue

    shutil.rmtree(session_dir, ignore_errors=True)


def _validate_codex_binary(binary: str) -> str:
    """codex binary を解決し、world-writable な /tmp 系を拒否。"""
    real = os.path.realpath(binary)
    for prefix in ("/tmp/", "/var/tmp/", "/private/tmp/", "/private/var/tmp/"):
        if real.startswith(prefix):
            raise PermissionError(f"codex binary in world-writable dir: {real}")
    return real


def _notify(notifier: Notifier, subtitle: str, message: str, sound: str | None = None) -> None:
    level = cfg.resolve_notification_level()
    if level == "none" or (level == "failure" and subtitle != "失敗"):
        _log(f"notify suppressed (level={level}): subtitle={subtitle} msg={message}")
        return
    notifier.notify(subtitle, message, sound)
    _log(f"notify: subtitle={subtitle} sound={sound or 'none'} msg={message}")


def run(
    input_md: Path,
    report_path: Path,
    stage_mode: str,
    meta_path: Path | None,
    *,
    model: str | None = None,
    effort: str | None = None,
    timeout_seconds: int | None = None,
    notifier: Notifier | None = None,
    codex_runner: CodexRunner | None = None,
) -> int:
    LOG_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LOG_DIR_LOCAL, 0o700)
    except OSError:
        pass
    rotate_log_if_needed(LOG_FILE)

    model = model or os.environ.get("CODEX_RECORDING_MODEL", "gpt-5.4-mini")
    effort = effort or os.environ.get("CODEX_RECORDING_EFFORT", "low")
    if effort not in EFFORT_VALID:
        effort = "low"
    if timeout_seconds is None:
        timeout_seconds = cfg.resolve_session_codex_timeout_seconds()

    session_dir = input_md.parent
    latest_md, latest_ts = _pick_latest_codex_md(session_dir)
    if latest_md is not None:
        input_md = latest_md
        meta_candidate = session_dir / f"{latest_ts}.codex.meta.json"
        if meta_candidate.is_file():
            meta_path = meta_candidate
        else:
            meta_path = None

    notifier = notifier or default_notifier("Episodic Recording")
    _log("---")
    _log(
        f"runner start: input={input_md} report={report_path} model={model} "
        f"effort={effort} stage={stage_mode} meta={meta_path} pid={os.getpid()} ts={latest_ts or '?'}"
    )

    meta = _load_meta(meta_path)

    session_id_from_dir = session_dir.name
    if not UUID_RE.match(session_id_from_dir):
        _log(f"warn: session_id from dir is not UUID, skip cleanup: {session_id_from_dir}")
        session_id_from_dir = ""

    # finalize 側のロック PID を runner 側に書き換える。
    if session_id_from_dir:
        lock_pid = session_dir / ".lock" / "pid"
        if lock_pid.parent.is_dir():
            try:
                lock_pid.write_text(f"{os.getpid()}\n")
                os.utime(session_dir / ".lock", None)
            except OSError:
                pass
            _log(f"runner claimed lock: session={session_id_from_dir} pid={os.getpid()}")

    if codex_runner is None:
        binary = os.environ.get("CODEX_BINARY") or shutil.which("codex")
        if not binary or not os.access(binary, os.X_OK):
            _log(f"error: codex binary not executable: '{binary or ''}'")
            _notify(notifier, "失敗", "codex コマンドが見つかりません。Codex CLI をインストールしてください。", "Basso")
            return 127
        try:
            binary = _validate_codex_binary(binary)
        except PermissionError as e:
            _log(f"error: {e}")
            _notify(notifier, "失敗", f"codex のパスが世界書き込み可能ディレクトリ配下にあります: {binary}", "Basso")
            return 126
        codex_runner = CodexRunner(
            model=model,
            effort=effort,
            timeout_seconds=timeout_seconds,
            codex_bin=binary,
        )

    if not input_md.is_file():
        _log(f"error: input not found: {input_md}")
        _notify(notifier, "失敗", f"入力Markdownが見つかりません: {input_md}", "Basso")
        return 1

    report_path.parent.mkdir(parents=True, exist_ok=True)

    # snapshot 保存
    snap_result = save_source_snapshot(
        meta.get("snapshot_path") or None,
        meta.get("transcript_path") or None,
    )
    if snap_result not in (
        SnapshotResult.SAVED,
        SnapshotResult.SAVED_FALLBACK,
        SnapshotResult.SKIP_NO_INPUT,
    ):
        _log(f"snapshot: {snap_result}")
    elif snap_result in (SnapshotResult.SAVED, SnapshotResult.SAVED_FALLBACK):
        _log(f"snapshot: {snap_result}: {meta.get('snapshot_path')}")

    # twin report 既存チェック → skip
    try:
        twin = pr.twin_report_path(report_path)
    except Exception:
        twin = None
    if twin and twin.is_file():
        _log(f"report already exists at twin path, skip codex: {twin}")
        _notify(notifier, "スキップ", f"同一セッションの要約が別側に保存済みです（{twin.name}）")
        _cleanup_session_dir(session_dir, latest_ts, session_id_from_dir or None)
        return 0

    capture = Path(tempfile.mkstemp(prefix="codex-session.", suffix="")[1])
    try:
        _log(f"model={model} effort={effort} input={input_md} report={report_path}")
        _log(f"codex exec start (hooks disabled, timeout={timeout_seconds}s)")
        result = codex_runner.run(input_md, LOG_FILE, capture)

        if result.returncode != 0:
            reason = _classify_failure_reason() if not result.timed_out else "timeout"
            _log(f"error: codex exec failed (rc={result.returncode} reason={reason})")
            _retry_queue_upsert(meta, reason)
            _notify(
                notifier,
                "失敗",
                f"codex exec に失敗しました（{reason}）。次回 SessionStart で自動リトライ。ログ: {LOG_FILE}",
                "Basso",
            )
            return 1

        last_msg = result.last_message
        if last_msg.lstrip().startswith("SKIP:"):
            first_line = last_msg.splitlines()[0] if last_msg else "SKIP"
            _log(f"skipped by codex: {last_msg}")
            _retry_queue_remove(meta)
            _notify(notifier, "スキップ", first_line)
            return 0

        # report 既書き込みパス
        if report_path.is_file():
            _enforce_supersedes_integrity(report_path)
            _log(f"report written by codex: {report_path}")
            _retry_queue_remove(meta)
            summary = _summarize_report(report_path)
            _notify(notifier, "完了", summary, "Glass")
            _log(f"report generated: {report_path}")
            if stage_mode != "staged":
                _trigger_memory_wiki(report_path)
            else:
                _log(f"post-process skipped (staged): {report_path}")
            return 0

        # フォールバック: last message に full report が含まれる
        if last_msg and last_msg.splitlines()[0].strip() == "---":
            report_path.write_text(last_msg, encoding="utf-8")
            _enforce_supersedes_integrity(report_path)
            _log(f"report written from last message: {report_path}")
            _retry_queue_remove(meta)
            summary = _summarize_report(report_path)
            _notify(notifier, "完了", summary, "Glass")
            if stage_mode != "staged":
                _trigger_memory_wiki(report_path)
            return 0

        _log(f"warn: codex produced no report; last message: {last_msg}")
        _retry_queue_upsert(meta, "no_report")
        _notify(notifier, "失敗", f"codex がレポートを生成しませんでした。次回 SessionStart で自動リトライ。ログ: {LOG_FILE}", "Basso")
        return 2
    finally:
        capture.unlink(missing_ok=True)
        if meta_path and meta_path.is_file():
            meta_path.unlink(missing_ok=True)
        _cleanup_session_dir(session_dir, latest_ts, session_id_from_dir or None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_md")
    parser.add_argument("report_path")
    parser.add_argument("stage_mode", choices=("staged", "normal"))
    parser.add_argument("meta_path", nargs="?", default=None)
    args = parser.parse_args(argv)
    return run(
        Path(args.input_md),
        Path(args.report_path),
        args.stage_mode,
        Path(args.meta_path) if args.meta_path else None,
    )


if __name__ == "__main__":
    sys.exit(main())
