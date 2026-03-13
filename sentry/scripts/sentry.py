#!/usr/bin/env python3
"""
Sentry MCP Server Wrapper

npx @sentry/mcp-server を使用してSentryデータを取得・管理するラッパースクリプト

Usage:
    sentry url <sentry_url>
    sentry issue <issue_id>
    sentry projects [--org <organization>]
    sentry orgs
    sentry whoami
    sentry update <issue_id> [--status <status>] [--assignee <email>]

Examples:
    # URLからイシュー詳細を取得
    sentry url "https://sentry.io/organizations/myorg/issues/12345/"

    # プロジェクト一覧を表示
    sentry projects --org myorg
"""

import argparse
import json
import os
import re
import subprocess
import sys


def call_mcp_tool(tool_name, arguments=None, sentry_host=None):
    """
    Sentry MCPサーバーのツールを呼び出す

    npx @sentry/mcp-server@latest を起動し、JSON-RPCでツールを呼び出す

    Args:
        sentry_host: Sentryホスト（セルフホスト用）。指定時にSENTRY_HOST環境変数を設定する。
    """
    if arguments is None:
        arguments = {}

    token = os.environ.get("SENTRY_ACCESS_TOKEN")
    if not token:
        print("Error: SENTRY_ACCESS_TOKEN environment variable is not set", file=sys.stderr)
        print("\nSet the token with:", file=sys.stderr)
        print("  export SENTRY_ACCESS_TOKEN=<your-auth-token>", file=sys.stderr)
        print("\nGet your token from: Sentry > Settings > Account > API > Auth Tokens", file=sys.stderr)
        sys.exit(1)

    # MCP初期化リクエスト
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "sentry-cli", "version": "1.0.0"}
        },
        "id": 1
    }

    # ツール呼び出しリクエスト
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
        if sentry_host:
            env["SENTRY_HOST"] = sentry_host
        result = subprocess.run(
            ["npx", "-y", "@sentry/mcp-server@0.29.0"],
            input=messages,
            capture_output=True,
            text=True,
            env=env,
            timeout=60
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
            # stderrには進行状況やデバッグ情報が含まれることがあるのでフィルタ
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


def extract_sentry_host(url):
    """URLからSentryホストを抽出。sentry.ioの場合はNoneを返す。"""
    match = re.match(r'https?://([^/]+)', url)
    if not match:
        return None
    hostname = match.group(1)
    # sentry.io または *.sentry.io はデフォルトなのでNone
    if hostname == "sentry.io" or hostname.endswith(".sentry.io"):
        return None
    return f"https://{hostname}"


def parse_sentry_url(url):
    """SentryのURLからイシューIDと組織を抽出"""
    # https://sentry.io/organizations/{org}/issues/{issue_id}/
    match = re.search(r'/organizations/([^/]+)/issues/(\d+)', url)
    if match:
        return {"org": match.group(1), "issue_id": match.group(2)}

    # https://{org}.sentry.io/issues/{issue_id}/
    match = re.search(r'https://([^.]+)\.sentry\.io/issues/(\d+)', url)
    if match:
        return {"org": match.group(1), "issue_id": match.group(2)}

    # 数字のみのイシューID
    match = re.search(r'/issues/(\d+)', url)
    if match:
        return {"issue_id": match.group(1)}

    return None


def get_issue_from_url(url):
    """SentryのURLからイシュー詳細を取得"""
    print(f"Parsing URL: {url}\n")

    parsed = parse_sentry_url(url)
    if parsed is None:
        return {"error": True, "message": f"Could not parse issue ID from URL: {url}"}

    issue_id = parsed.get("issue_id")
    org = parsed.get("org")
    sentry_host = extract_sentry_host(url)
    print(f"   Issue ID: {issue_id}")
    if org:
        print(f"   Organization: {org}")
    if sentry_host:
        print(f"   Sentry Host: {sentry_host}")
    print()

    # URLを直接渡すか、ID+組織を渡す
    # セルフホストの場合はSENTRY_HOSTを自動設定
    return call_mcp_tool("get_issue_details", {"issueUrl": url}, sentry_host=sentry_host)


def get_issue_details(issue_id):
    """イシューIDから詳細を取得"""
    print(f"Getting issue details: {issue_id}\n")

    return call_mcp_tool("get_issue_details", {"issueId": str(issue_id)})



def find_projects(organization=None):
    """プロジェクト一覧を取得"""
    if organization:
        print(f"Finding projects for: {organization}\n")
        return call_mcp_tool("find_projects", {"organizationSlug": organization})
    else:
        print("Finding all accessible projects\n")
        return call_mcp_tool("find_projects", {})


def find_organizations():
    """組織一覧を取得"""
    print("Finding organizations\n")
    return call_mcp_tool("find_organizations", {})


def whoami():
    """認証ユーザー情報を取得"""
    print("Getting authenticated user info\n")
    return call_mcp_tool("whoami", {})


def get_stats(organization, project=None, period="14d", group_by="day", limit=30):
    """エラー統計を取得"""
    GROUP_BY_MAP = {
        "day": {
            "fields": ["count()", "timestamp.to_day"],
            "sort": "timestamp.to_day"
        },
        "error-type": {
            "fields": ["count()", "error.type"],
            "sort": "-count()"
        },
        "title": {
            "fields": ["count()", "title"],
            "sort": "-count()"
        }
    }
    config = GROUP_BY_MAP.get(group_by, GROUP_BY_MAP["day"])

    args = {
        "organizationSlug": organization,
        "dataset": "errors",
        "fields": config["fields"],
        "sort": config["sort"],
        "statsPeriod": period,
        "limit": limit
    }
    if project:
        args["projectSlug"] = project

    print(f"Getting error stats: org={organization}, group_by={group_by}, period={period}")
    if project:
        print(f"   Project: {project}")
    print()

    return call_mcp_tool("list_events", args)


def get_top_issues(organization, project=None, sort="freq", query="is:unresolved", limit=10):
    """頻出イシューランキングを取得"""
    args = {
        "organizationSlug": organization,
        "sort": sort,
        "query": query,
        "limit": limit
    }
    if project:
        args["projectSlugOrId"] = project

    print(f"Getting top issues: org={organization}, sort={sort}")
    if project:
        print(f"   Project: {project}")
    print(f"   Query: {query}")
    print()

    return call_mcp_tool("list_issues", args)


def update_issue(issue_id, status=None, assignee=None):
    """イシューを更新"""
    print(f"Updating issue: {issue_id}")
    if status:
        print(f"   Status: {status}")
    if assignee:
        print(f"   Assignee: {assignee}")
    print()

    args = {"issue_id": str(issue_id)}
    if status:
        args["status"] = status
    if assignee:
        args["assignee"] = assignee

    if len(args) == 1:
        return {"error": True, "message": "No update parameters provided"}

    return call_mcp_tool("update_issue", args)



def main():
    parser = argparse.ArgumentParser(
        description="Sentry MCP Server Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # url コマンド
    url_parser = subparsers.add_parser("url", help="Get issue details from Sentry URL")
    url_parser.add_argument("url", type=str, help="Sentry issue URL")

    # issue コマンド
    issue_parser = subparsers.add_parser("issue", help="Get issue details by ID")
    issue_parser.add_argument("issue_id", type=str, help="Issue ID")


    # projects コマンド
    projects_parser = subparsers.add_parser("projects", help="List projects")
    projects_parser.add_argument("--org", "-o", type=str, dest="organization",
                                 help="Organization slug (optional)")

    # orgs コマンド
    subparsers.add_parser("orgs", help="List organizations")

    # whoami コマンド
    subparsers.add_parser("whoami", help="Get authenticated user info")

    # stats コマンド
    stats_parser = subparsers.add_parser("stats", help="Error statistics and trends")
    stats_parser.add_argument("organization", type=str, help="Organization slug")
    stats_parser.add_argument("--project", "-p", type=str, help="Project slug")
    stats_parser.add_argument("--period", "-t", type=str, default="14d",
                              help="Time period (1h, 24h, 7d, 14d, 30d)")
    stats_parser.add_argument("--group-by", "-g", type=str, default="day",
                              choices=["day", "error-type", "title"],
                              help="Aggregation axis")
    stats_parser.add_argument("--limit", "-l", type=int, default=30,
                              help="Max results")

    # top-issues コマンド
    top_parser = subparsers.add_parser("top-issues", help="Top issues ranking")
    top_parser.add_argument("organization", type=str, help="Organization slug")
    top_parser.add_argument("--project", "-p", type=str, help="Project slug")
    top_parser.add_argument("--sort", "-s", type=str, default="freq",
                            choices=["freq", "date", "new"],
                            help="Sort order")
    top_parser.add_argument("--query", "-q", type=str, default="is:unresolved",
                            help="Sentry search query")
    top_parser.add_argument("--limit", "-l", type=int, default=10,
                            help="Max results")

    # update コマンド
    update_parser = subparsers.add_parser("update", help="Update issue")
    update_parser.add_argument("issue_id", type=str, help="Issue ID")
    update_parser.add_argument("--status", "-s", type=str,
                               choices=["resolved", "unresolved", "ignored"],
                               help="New status")
    update_parser.add_argument("--assignee", "-a", type=str, help="Assignee email or ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "url":
            result = get_issue_from_url(args.url)
        elif args.command == "issue":
            result = get_issue_details(args.issue_id)
        elif args.command == "projects":
            result = find_projects(getattr(args, 'organization', None))
        elif args.command == "orgs":
            result = find_organizations()
        elif args.command == "whoami":
            result = whoami()
        elif args.command == "stats":
            result = get_stats(
                args.organization,
                project=args.project,
                period=args.period,
                group_by=getattr(args, 'group_by', 'day'),
                limit=args.limit
            )
        elif args.command == "top-issues":
            result = get_top_issues(
                args.organization,
                project=args.project,
                sort=args.sort,
                query=args.query,
                limit=args.limit
            )
        elif args.command == "update":
            result = update_issue(
                args.issue_id,
                status=args.status,
                assignee=getattr(args, 'assignee', None)
            )
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
