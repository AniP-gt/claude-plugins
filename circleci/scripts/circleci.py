#!/usr/bin/env python3
"""
CircleCI MCP Server Wrapper

npx @circleci/mcp-server-circleci を使用してCircleCIデータを取得・操作するラッパースクリプト

Usage:
    circleci url <circleci_url> [--tests | --status | --artifacts | --flaky]
    circleci failures [--project-slug <slug>] [--branch <branch>] [--project-url <url>] [--output-dir <dir>]
    circleci tests [--project-slug <slug>] [--branch <branch>] [--project-url <url>]
    circleci status [--project-slug <slug>] [--branch <branch>] [--project-url <url>]
    circleci artifacts [--project-slug <slug>] [--branch <branch>] [--project-url <url>]
    circleci flaky [--project-slug <slug>] [--project-url <url>]
    circleci projects
    circleci rerun [--workflow-id <uuid> | --workflow-url <url>] [--from-failed]
    circleci run-pipeline [--project-slug <slug>] [--branch <branch>] [--project-url <url>] [--pipeline-name <name>]
    circleci config <config_path>
    circleci workflow-status [--workflow-id <uuid> | --workflow-url <url>]
    circleci watch [--workflow-id <uuid> | --workflow-url <url> | --project-url <url> | --project-slug <slug> --branch <branch>]
                   [--target-state terminal|success] [--interval <sec>] [--max-wait <sec>] [--notify-on change|every]

Examples:
    # CircleCI URLからビルド失敗ログを取得
    circleci url "https://app.circleci.com/pipelines/github/org/repo/123/workflows/abc/jobs/456"

    # プロジェクトslugとブランチで失敗ログ取得
    circleci failures --project-slug "github/org/repo" --branch main

    # flakyテストを検出
    circleci flaky --project-slug "github/org/repo"

    # ワークフローを失敗箇所から再実行
    circleci rerun --workflow-url "https://app.circleci.com/.../workflows/abc" --from-failed

    # config.ymlの妥当性を検証
    circleci config .circleci/config.yml

    # ワークフローのジョブ状態を1度だけ取得
    circleci workflow-status --workflow-id 73a9e721-...

    # ワークフローを目的状態まで監視（進捗を逐次標準出力にストリーム）
    circleci watch --project-url "https://app.circleci.com/.../workflows/73a9e721-..."
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


MCP_SERVER_VERSION = "@circleci/mcp-server-circleci@0.15.1"


def call_mcp_tool(tool_name, arguments=None):
    """
    CircleCI MCPサーバーのツールを呼び出す

    npx @circleci/mcp-server-circleci@<version> を起動し、JSON-RPCでツールを呼び出す
    """
    if arguments is None:
        arguments = {}

    token = os.environ.get("CIRCLECI_TOKEN")
    if not token:
        print("Error: CIRCLECI_TOKEN environment variable is not set", file=sys.stderr)
        print("\nSet the token with:", file=sys.stderr)
        print("  export CIRCLECI_TOKEN=<your-personal-api-token>", file=sys.stderr)
        print("\nGet your token from: https://app.circleci.com/settings/user/tokens", file=sys.stderr)
        sys.exit(1)

    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "circleci-cli", "version": "1.0.0"}
        },
        "id": 1
    }

    tool_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 2
    }

    messages = json.dumps(init_request) + "\n" + json.dumps(tool_request) + "\n"

    try:
        env = os.environ.copy()
        result = subprocess.run(
            ["npx", "-y", MCP_SERVER_VERSION],
            input=messages,
            capture_output=True,
            text=True,
            env=env,
            timeout=120
        )

        responses = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        for resp in responses:
            if resp.get("id") == 2:
                if "error" in resp:
                    return {"error": True, "message": resp["error"]}
                return resp.get("result", {})

        if result.stderr:
            stderr_lines = [l for l in result.stderr.split("\n") if "error" in l.lower()]
            if stderr_lines:
                return {"error": True, "message": "\n".join(stderr_lines)}

        return {"error": True, "message": "No response from MCP server", "raw_output": result.stdout}

    except subprocess.TimeoutExpired:
        return {"error": True, "message": "MCP server timeout"}
    except FileNotFoundError:
        return {"error": True, "message": "npx not found. Please install Node.js"}
    except Exception as e:
        return {"error": True, "message": str(e)}


def build_target_args(project_slug=None, branch=None, project_url=None,
                      workspace_root=None, git_remote_url=None):
    """
    CircleCI MCPツールが共通で受け取るターゲット指定引数を組み立てる。

    入力パターン（以下のいずれかを指定）:
      1. projectSlug + branch
      2. projectURL（pipeline/workflow/job のいずれかのURL）
      3. workspaceRoot + gitRemoteURL + branch
    """
    args = {}
    if project_slug:
        args["projectSlug"] = project_slug
    if branch:
        args["branch"] = branch
    if project_url:
        args["projectURL"] = project_url
    if workspace_root:
        args["workspaceRoot"] = workspace_root
    if git_remote_url:
        args["gitRemoteURL"] = git_remote_url
    return args


def get_build_failure_logs(project_slug=None, branch=None, project_url=None, output_dir=None):
    print("Fetching build failure logs")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    if branch:
        print(f"   Branch: {branch}")
    print()

    args = build_target_args(project_slug=project_slug, branch=branch, project_url=project_url)
    if output_dir:
        args["outputDir"] = output_dir
    return call_mcp_tool("get_build_failure_logs", args)


def get_job_test_results(project_slug=None, branch=None, project_url=None):
    print("Fetching job test results")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    if branch:
        print(f"   Branch: {branch}")
    print()

    args = build_target_args(project_slug=project_slug, branch=branch, project_url=project_url)
    return call_mcp_tool("get_job_test_results", args)


def get_latest_pipeline_status(project_slug=None, branch=None, project_url=None):
    print("Fetching latest pipeline status")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    if branch:
        print(f"   Branch: {branch}")
    print()

    args = build_target_args(project_slug=project_slug, branch=branch, project_url=project_url)
    return call_mcp_tool("get_latest_pipeline_status", args)


def list_artifacts(project_slug=None, branch=None, project_url=None):
    print("Listing artifacts")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    if branch:
        print(f"   Branch: {branch}")
    print()

    args = build_target_args(project_slug=project_slug, branch=branch, project_url=project_url)
    return call_mcp_tool("list_artifacts", args)


def find_flaky_tests(project_slug=None, project_url=None):
    print("Finding flaky tests")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    print()

    args = build_target_args(project_slug=project_slug, project_url=project_url)
    return call_mcp_tool("find_flaky_tests", args)


def list_followed_projects():
    print("Listing followed CircleCI projects\n")
    return call_mcp_tool("list_followed_projects", {})


def rerun_workflow(workflow_id=None, workflow_url=None, from_failed=None):
    print("Rerunning workflow")
    if workflow_url:
        print(f"   URL: {workflow_url}")
    if workflow_id:
        print(f"   Workflow ID: {workflow_id}")
    if from_failed is not None:
        print(f"   From failed: {from_failed}")
    print()

    args = {}
    if workflow_id:
        args["workflowId"] = workflow_id
    if workflow_url:
        args["workflowURL"] = workflow_url
    if from_failed is not None:
        args["fromFailed"] = from_failed

    if not args:
        return {"error": True, "message": "Specify --workflow-id or --workflow-url"}

    return call_mcp_tool("rerun_workflow", args)


def run_pipeline(project_slug=None, branch=None, project_url=None, pipeline_name=None, config_content=None):
    print("Running pipeline")
    if project_url:
        print(f"   URL: {project_url}")
    if project_slug:
        print(f"   Project: {project_slug}")
    if branch:
        print(f"   Branch: {branch}")
    if pipeline_name:
        print(f"   Pipeline: {pipeline_name}")
    print()

    args = build_target_args(project_slug=project_slug, branch=branch, project_url=project_url)
    if pipeline_name:
        args["pipelineChoiceName"] = pipeline_name
    if config_content:
        args["configContent"] = config_content

    return call_mcp_tool("run_pipeline", args)


def config_helper(config_path):
    print(f"Validating CircleCI config: {config_path}\n")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_content = f.read()
    except FileNotFoundError:
        return {"error": True, "message": f"Config file not found: {config_path}"}
    except Exception as e:
        return {"error": True, "message": f"Failed to read config file: {e}"}

    return call_mcp_tool("config_helper", {"configFile": config_content})


# --- workflow-status / watch implementations ----------------------------------

WORKFLOW_TERMINAL_STATES = {
    "success", "failed", "error", "canceled", "unauthorized",
}
WORKFLOW_FAILURE_STATES = {
    "failed", "error", "canceled", "unauthorized",
}


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


_WORKFLOW_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


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
      3. --project-slug + --branch (もしくは --project-url のうち抽出失敗時) → status コマンドで最新を取得
    """
    if args.workflow_id:
        return args.workflow_id

    for url in (args.workflow_url, args.project_url):
        wid = extract_workflow_id_from_url(url)
        if wid:
            return wid

    # 最新パイプラインから推定
    if args.project_slug or args.project_url or args.branch:
        latest = get_latest_pipeline_status(
            project_slug=args.project_slug,
            branch=args.branch,
            project_url=args.project_url,
        )
        if isinstance(latest, dict) and not latest.get("error"):
            wid = _extract_workflow_id_from_status(latest)
            if wid:
                return wid
    return None


def _extract_workflow_id_from_status(status_result):
    """status コマンドの結果から workflow_id を抽出する（フォーマット差分を吸収）。"""
    blob = json.dumps(status_result, ensure_ascii=False)
    via_url = extract_workflow_id_from_url(blob)
    if via_url:
        return via_url
    m = _WORKFLOW_UUID_RE.search(blob)
    return m.group(0) if m else None


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


def add_target_args(parser, with_branch=True, with_url=True):
    """各サブコマンドで共通のターゲット指定引数を追加する。"""
    parser.add_argument("--project-slug", "-p", type=str, dest="project_slug",
                        help="Project slug (e.g., 'github/org/repo')")
    if with_branch:
        parser.add_argument("--branch", "-b", type=str, help="Git branch name")
    if with_url:
        parser.add_argument("--project-url", "-u", type=str, dest="project_url",
                            help="CircleCI project/pipeline/workflow/job URL")


def main():
    parser = argparse.ArgumentParser(
        description="CircleCI MCP Server Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # url コマンド（CircleCI URL を渡してビルド失敗ログ等を取得）
    url_parser = subparsers.add_parser("url", help="Fetch info from a CircleCI URL")
    url_parser.add_argument("url", type=str, help="CircleCI pipeline/workflow/job URL")
    url_parser.add_argument("--tests", action="store_true", help="Fetch test results instead")
    url_parser.add_argument("--status", action="store_true", help="Fetch latest pipeline status instead")
    url_parser.add_argument("--artifacts", action="store_true", help="List artifacts instead")
    url_parser.add_argument("--flaky", action="store_true", help="Find flaky tests instead")

    # failures コマンド
    failures_parser = subparsers.add_parser("failures", help="Get build failure logs")
    add_target_args(failures_parser)
    failures_parser.add_argument("--output-dir", "-o", type=str, dest="output_dir",
                                 help="Save full logs to this directory (avoids truncation)")

    # tests コマンド
    tests_parser = subparsers.add_parser("tests", help="Get job test results")
    add_target_args(tests_parser)

    # status コマンド
    status_parser = subparsers.add_parser("status", help="Get latest pipeline status")
    add_target_args(status_parser)

    # artifacts コマンド
    artifacts_parser = subparsers.add_parser("artifacts", help="List job artifacts")
    add_target_args(artifacts_parser)

    # flaky コマンド
    flaky_parser = subparsers.add_parser("flaky", help="Find flaky tests")
    add_target_args(flaky_parser, with_branch=False)

    # projects コマンド
    subparsers.add_parser("projects", help="List followed CircleCI projects")

    # rerun コマンド
    rerun_parser = subparsers.add_parser("rerun", help="Rerun a workflow")
    rerun_parser.add_argument("--workflow-id", "-w", type=str, dest="workflow_id",
                              help="Workflow UUID")
    rerun_parser.add_argument("--workflow-url", "-u", type=str, dest="workflow_url",
                              help="Workflow URL")
    rerun_parser.add_argument("--from-failed", action="store_true", dest="from_failed",
                              help="Rerun from the failed step (default: from start)")

    # run-pipeline コマンド
    run_parser = subparsers.add_parser("run-pipeline", help="Trigger a pipeline run")
    add_target_args(run_parser)
    run_parser.add_argument("--pipeline-name", "-n", type=str, dest="pipeline_name",
                            help="Pipeline definition name (when multiple exist)")

    # config コマンド
    config_parser = subparsers.add_parser("config", help="Validate a CircleCI config.yml")
    config_parser.add_argument("path", type=str, help="Path to .circleci/config.yml")

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
        if args.command == "url":
            if args.tests:
                result = get_job_test_results(project_url=args.url)
            elif args.status:
                result = get_latest_pipeline_status(project_url=args.url)
            elif args.artifacts:
                result = list_artifacts(project_url=args.url)
            elif args.flaky:
                result = find_flaky_tests(project_url=args.url)
            else:
                result = get_build_failure_logs(project_url=args.url)
        elif args.command == "failures":
            result = get_build_failure_logs(
                project_slug=args.project_slug,
                branch=args.branch,
                project_url=args.project_url,
                output_dir=getattr(args, "output_dir", None)
            )
        elif args.command == "tests":
            result = get_job_test_results(
                project_slug=args.project_slug,
                branch=args.branch,
                project_url=args.project_url
            )
        elif args.command == "status":
            result = get_latest_pipeline_status(
                project_slug=args.project_slug,
                branch=args.branch,
                project_url=args.project_url
            )
        elif args.command == "artifacts":
            result = list_artifacts(
                project_slug=args.project_slug,
                branch=args.branch,
                project_url=args.project_url
            )
        elif args.command == "flaky":
            result = find_flaky_tests(
                project_slug=args.project_slug,
                project_url=args.project_url
            )
        elif args.command == "projects":
            result = list_followed_projects()
        elif args.command == "rerun":
            from_failed = True if args.from_failed else None
            result = rerun_workflow(
                workflow_id=args.workflow_id,
                workflow_url=args.workflow_url,
                from_failed=from_failed
            )
        elif args.command == "run-pipeline":
            result = run_pipeline(
                project_slug=args.project_slug,
                branch=args.branch,
                project_url=args.project_url,
                pipeline_name=args.pipeline_name
            )
        elif args.command == "config":
            result = config_helper(args.path)
        elif args.command == "workflow-status":
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
