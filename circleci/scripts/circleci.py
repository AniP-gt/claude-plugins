#!/usr/bin/env python3
"""
CircleCI Watch CLI

CircleCI REST API v2 を直接叩いて、ワークフローの状態を取得・監視するスクリプト。
MCP ツールによる調査系コマンド（failures / tests / status / flaky / rerun / config 等）は
.mcp.json 経由の MCP サーバーで提供されるため、本スクリプトは watch / workflow-status のみを担う。

Usage:
    circleci.py workflow-status [--workflow-id <uuid> | --workflow-url <url>]
    circleci.py watch [--workflow-id <uuid> | --workflow-url <url> | --project-url <url> | --project-slug <slug> --branch <branch>]
                      [--target-state terminal|success] [--interval <sec>] [--max-wait <sec>] [--notify-on change|every]

Examples:
    # ワークフロー状態を1度だけ取得
    circleci.py workflow-status --workflow-id 73a9e721-...

    # ワークフローを目的状態まで監視
    circleci.py watch --project-url "https://app.circleci.com/.../workflows/73a9e721-..."
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


WORKFLOW_TERMINAL_STATES = {
    "success", "failed", "error", "canceled", "unauthorized",
}
WORKFLOW_FAILURE_STATES = {
    "failed", "error", "canceled", "unauthorized",
}

_WORKFLOW_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _circleci_base_url():
    base = os.environ.get("CIRCLECI_BASE_URL", "https://circleci.com").rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        print(
            f"Error: CIRCLECI_BASE_URL must be an http(s) URL, got: {base!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    return base


def _require_token():
    token = os.environ.get("CIRCLECI_TOKEN")
    if not token:
        print("Error: CIRCLECI_TOKEN environment variable is not set", file=sys.stderr)
        print("\nGet your token from: https://app.circleci.com/settings/user/tokens", file=sys.stderr)
        sys.exit(1)
    return token


def _api_get(path):
    """CircleCI REST API v2 に GET リクエストを送る。"""
    token = _require_token()
    url = f"{_circleci_base_url()}/api/v2/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={
        "Circle-Token": token,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_workflow_id_from_url(url):
    """CircleCI の workflow / job URL から workflow UUID を抽出する。"""
    if not url:
        return None
    m = re.search(r"/workflows/(" + _WORKFLOW_UUID_RE.pattern + r")", url)
    if m:
        return m.group(1)
    m = _WORKFLOW_UUID_RE.search(url)
    return m.group(0) if m else None


def fetch_workflow_status(workflow_id):
    """workflow と jobs を REST 経由で取得し、watch が扱いやすい形に整える。"""
    workflow = _api_get(f"workflow/{workflow_id}")
    jobs_resp = _api_get(f"workflow/{workflow_id}/job")
    jobs = []
    for j in jobs_resp.get("items", []):
        jobs.append({
            "id": j.get("id"),
            "job_number": j.get("job_number"),
            "name": j.get("name"),
            "status": j.get("status"),
            "type": j.get("type"),
            "started_at": j.get("started_at"),
            "stopped_at": j.get("stopped_at"),
            "dependencies": j.get("dependencies", []),
        })
    return {
        "workflow": {
            "id": workflow.get("id"),
            "name": workflow.get("name"),
            "status": workflow.get("status"),
            "pipeline_id": workflow.get("pipeline_id"),
            "pipeline_number": workflow.get("pipeline_number"),
            "project_slug": workflow.get("project_slug"),
            "created_at": workflow.get("created_at"),
            "stopped_at": workflow.get("stopped_at"),
        },
        "jobs": jobs,
    }


def fetch_latest_workflow_id(project_slug, branch=None):
    """project_slug（必須）+ branch（任意）から最新パイプラインの最新ワークフロー UUID を取得する。"""
    quoted_slug = urllib.parse.quote(project_slug, safe="/")
    path = f"project/{quoted_slug}/pipeline"
    if branch:
        path += f"?branch={urllib.parse.quote(branch)}"
    pipelines = _api_get(path)
    items = pipelines.get("items", [])
    if not items:
        return None
    pipeline_id = items[0].get("id")
    if not pipeline_id:
        return None
    workflows = _api_get(f"pipeline/{pipeline_id}/workflow")
    wf_items = workflows.get("items", [])
    return wf_items[0].get("id") if wf_items else None


def workflow_status_command(workflow_id=None, workflow_url=None):
    if not workflow_id:
        workflow_id = extract_workflow_id_from_url(workflow_url)
    if not workflow_id:
        return {"error": True, "message": "Specify --workflow-id or --workflow-url"}
    print(f"Fetching workflow status: {workflow_id}\n")
    try:
        return fetch_workflow_status(workflow_id)
    except urllib.error.HTTPError as e:
        return {"error": True, "message": f"CircleCI API error: {e.code} {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": True, "message": f"Network error: {e.reason}"}


def _resolve_workflow_id_for_watch(args):
    """watch の入力からワークフローIDを決定する。

    優先順位:
      1. --workflow-id
      2. --workflow-url / --project-url（URL から抽出可能なら抽出）
      3. --project-slug (+--branch) → REST で最新ワークフローを取得
    """
    if args.workflow_id:
        return args.workflow_id

    for url in (args.workflow_url, args.project_url):
        wid = extract_workflow_id_from_url(url)
        if wid:
            return wid

    if args.project_slug:
        try:
            return fetch_latest_workflow_id(args.project_slug, args.branch)
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None
    return None


def _now():
    return datetime.now(timezone.utc)


def _fmt_elapsed(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def _job_diff(prev_jobs, curr_jobs):
    """前回と今回のジョブ状態差分を返す。

    Returns:
      List[(name, prev_status, curr_status)]
        - prev_status が None なら新規追加ジョブ
    """
    prev_by_name = {j["name"]: j for j in (prev_jobs or [])}
    diffs = []
    for j in curr_jobs:
        name = j["name"]
        prev = prev_by_name.get(name)
        if prev is None:
            diffs.append((name, None, j["status"]))
        elif prev["status"] != j["status"]:
            diffs.append((name, prev["status"], j["status"]))
    return diffs


def _print_tick(elapsed, workflow_status, diffs):
    print(
        f"[circleci-watch] tick elapsed={_fmt_elapsed(elapsed)} "
        f"workflow={workflow_status} changed={len(diffs)}",
        flush=True,
    )
    for name, prev, curr in diffs:
        if prev is None:
            print(f"  + {name}: {curr}", flush=True)
        else:
            print(f"  ~ {name}: {prev} → {curr}", flush=True)


def _print_final(elapsed, snapshot, target_state, status_label):
    wf = snapshot["workflow"]
    print("", flush=True)
    print(
        f"[circleci-watch] FINAL status={status_label} "
        f"elapsed={_fmt_elapsed(elapsed)}",
        flush=True,
    )
    print(
        f"  pipeline=#{wf.get('pipeline_number')} workflow={wf.get('id')}",
        flush=True,
    )
    print(f"  workflow_status={wf.get('status')} target={target_state}", flush=True)
    print("  jobs:", flush=True)
    for j in snapshot["jobs"]:
        dur = ""
        if j.get("started_at") and j.get("stopped_at"):
            try:
                s = datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(j["stopped_at"].replace("Z", "+00:00"))
                dur = _fmt_elapsed((e - s).total_seconds())
            except ValueError:
                dur = ""
        print(
            f"    {j['name']:<40} {j.get('status', ''):<10} {dur}",
            flush=True,
        )
    proj = wf.get("project_slug")
    if proj and wf.get("id"):
        print(
            f"  url: https://app.circleci.com/pipelines/{proj}/{wf.get('pipeline_number')}/workflows/{wf.get('id')}",
            flush=True,
        )


def _evaluate_stop(workflow_status, jobs, target_state):
    """終了判定。

    Returns:
      (stop: bool, label: 'success'|'failure'|None)
    """
    if target_state == "success":
        if workflow_status == "success":
            return True, "success"
        if workflow_status in WORKFLOW_FAILURE_STATES:
            return True, "failure"
        for j in jobs:
            if j.get("status") in WORKFLOW_FAILURE_STATES:
                return True, "failure"
        return False, None
    # default: terminal
    if workflow_status in WORKFLOW_TERMINAL_STATES:
        return True, ("success" if workflow_status == "success" else "failure")
    return False, None


def watch_command(args):
    workflow_id = _resolve_workflow_id_for_watch(args)
    if not workflow_id:
        msg = (
            "Could not resolve workflow id. "
            "Specify --workflow-id, --workflow-url, --project-url, "
            "or --project-slug + --branch."
        )
        print(f"[circleci-watch] error: {msg}", file=sys.stderr, flush=True)
        return {"error": True, "message": msg}

    interval = max(30, min(args.interval, 600))
    max_wait = max(60, min(args.max_wait, 7200))
    target_state = args.target_state
    notify_on = args.notify_on

    print(
        f"[circleci-watch] start workflow={workflow_id} "
        f"target={target_state} interval={interval}s max_wait={_fmt_elapsed(max_wait)} notify_on={notify_on}",
        flush=True,
    )

    started = _now()
    snapshot = None
    try:
        snapshot = fetch_workflow_status(workflow_id)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        return {"error": True, "message": f"Initial fetch failed: {e}"}

    _print_tick(
        0,
        snapshot["workflow"].get("status"),
        [(j["name"], None, j["status"]) for j in snapshot["jobs"]],
    )

    stop, label = _evaluate_stop(
        snapshot["workflow"].get("status"), snapshot["jobs"], target_state,
    )
    if stop:
        elapsed = (_now() - started).total_seconds()
        _print_final(elapsed, snapshot, target_state, label)
        return {"final": True, "status": label, "snapshot": snapshot}

    while True:
        time.sleep(interval)
        elapsed = (_now() - started).total_seconds()
        if elapsed > max_wait:
            _print_final(elapsed, snapshot, target_state, "timeout")
            return {"final": True, "status": "timeout", "snapshot": snapshot}

        try:
            latest = fetch_workflow_status(workflow_id)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"[circleci-watch] warn fetch failed: {e}", flush=True)
            continue

        diffs = _job_diff(snapshot["jobs"], latest["jobs"])
        wf_changed = (
            snapshot["workflow"].get("status") != latest["workflow"].get("status")
        )
        if notify_on == "every" or diffs or wf_changed:
            _print_tick(elapsed, latest["workflow"].get("status"), diffs)

        snapshot = latest

        stop, label = _evaluate_stop(
            latest["workflow"].get("status"), latest["jobs"], target_state,
        )
        if stop:
            _print_final(elapsed, snapshot, target_state, label)
            return {"final": True, "status": label, "snapshot": snapshot}


def main():
    parser = argparse.ArgumentParser(
        description="CircleCI Watch CLI (REST API based)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # workflow-status コマンド（特定ワークフローの状態とジョブを取得）
    wfstatus_parser = subparsers.add_parser(
        "workflow-status", help="Fetch a specific workflow's status and jobs"
    )
    wfstatus_parser.add_argument("--workflow-id", "-w", type=str, dest="workflow_id",
                                 help="Workflow UUID")
    wfstatus_parser.add_argument("--workflow-url", "-u", type=str, dest="workflow_url",
                                 help="Workflow / job URL containing UUID")

    # watch コマンド（target_state まで監視）
    watch_parser = subparsers.add_parser(
        "watch", help="Watch a workflow until it reaches target_state"
    )
    watch_parser.add_argument("--workflow-id", "-w", type=str, dest="workflow_id",
                              help="Workflow UUID")
    watch_parser.add_argument("--workflow-url", type=str, dest="workflow_url",
                              help="Workflow URL containing UUID")
    watch_parser.add_argument("--project-url", "-u", type=str, dest="project_url",
                              help="CircleCI pipeline/workflow/job URL")
    watch_parser.add_argument("--project-slug", "-p", type=str, dest="project_slug",
                              help="Project slug (e.g., 'github/org/repo')")
    watch_parser.add_argument("--branch", "-b", type=str, help="Git branch name")
    watch_parser.add_argument("--target-state", type=str, dest="target_state",
                              choices=["terminal", "success"], default="terminal",
                              help="Stop condition (default: terminal)")
    watch_parser.add_argument("--interval", type=int, default=90,
                              help="Polling interval seconds (30-600, default 90)")
    watch_parser.add_argument("--max-wait", type=int, dest="max_wait", default=1800,
                              help="Total timeout seconds (60-7200, default 1800)")
    watch_parser.add_argument("--notify-on", type=str, dest="notify_on",
                              choices=["change", "every"], default="change",
                              help="When to emit progress ticks (default: change)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "workflow-status":
            result = workflow_status_command(
                workflow_id=args.workflow_id,
                workflow_url=args.workflow_url,
            )
        elif args.command == "watch":
            result = watch_command(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        if args.command != "watch":
            print("=" * 50)
            print("Result:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

        if isinstance(result, dict) and result.get("error"):
            sys.exit(1)
        if isinstance(result, dict) and result.get("status") == "failure":
            sys.exit(2)
        if isinstance(result, dict) and result.get("status") == "timeout":
            sys.exit(3)
        sys.exit(0)

    except Exception as e:
        error_result = {"error": str(e), "command": args.command}
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
