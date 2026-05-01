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
"""

import argparse
import json
import os
import subprocess
import sys


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
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        print("=" * 50)
        print("Result:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if isinstance(result, dict) and result.get("error"):
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        error_result = {"error": str(e), "command": args.command}
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
