#!/usr/bin/env python3
"""
Slack MCP CLI

Slack MCPクライアントのCLIエントリーポイント。
OAuth認証、ワークスペース管理、Slackツール実行を行う。

Usage:
    python slack_cli.py login
    python slack_cli.py logout <workspace>
    python slack_cli.py workspaces
    python slack_cli.py set-default <workspace>
    python slack_cli.py tools
    python slack_cli.py call <tool_name> --arg key=value
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError
from oauth import login, login_url_only, login_with_code, OAuthError
from slack_client import SlackMCPClient, SlackMCPError


def extract_text(content: list) -> str:
    """MCPレスポンスのcontentリストからテキストを抽出"""
    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item["text"])
        elif isinstance(item, str):
            parts.append(item)
    return "\n".join(parts) if parts else json.dumps(content, ensure_ascii=False, indent=2)


def parse_arg_value(value_str: str):
    """引数値を適切な型に変換（数値・bool・JSON）"""
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return value_str


def cmd_login(args):
    """OAuth PKCEフローでログイン"""
    if args.url_only:
        login_url_only()
    elif args.code:
        login_with_code(args.code)
    else:
        login()


def cmd_logout(args):
    """ワークスペースのトークンを削除"""
    store = TokenStore()
    if store.remove_workspace(args.workspace):
        print(f"Logged out: {args.workspace}")
    else:
        print(f"Workspace not found: {args.workspace}", file=sys.stderr)
        sys.exit(1)


def cmd_workspaces(args):
    """保存済みワークスペース一覧を表示"""
    store = TokenStore()
    workspaces = store.list_workspaces()
    default_key = store.get_default_key()

    if not workspaces:
        print("No workspaces configured. Run 'login' first.")
        return

    for key, ws in workspaces.items():
        marker = " [default]" if key == default_key else ""
        team_name = ws.get("team_name", "?")
        team_id = ws.get("team_id", "?")
        print(f"  {key}{marker}")
        print(f"    Team: {team_name} ({team_id})")
        print(f"    Scope: {ws.get('scope', 'N/A')}")
        print()


def cmd_set_default(args):
    """デフォルトワークスペースを設定"""
    store = TokenStore()
    if store.set_default(args.workspace):
        print(f"Default workspace set: {args.workspace}")
    else:
        print(f"Workspace not found: {args.workspace}", file=sys.stderr)
        sys.exit(1)


def cmd_tools(args):
    """利用可能なSlack MCPツール一覧を表示"""
    with SlackMCPClient(
        workspace=args.workspace,
        debug=args.debug,
    ) as client:
        tools = client.list_tools()
        for tool in tools:
            name = tool.get("name", "?")
            desc = tool.get("description", "")
            print(f"  {name}")
            if desc:
                first_line = desc.strip().split("\n")[0]
                print(f"    {first_line}")
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            required = schema.get("required", [])
            if props:
                for pname, pinfo in props.items():
                    req_mark = "*" if pname in required else " "
                    ptype = pinfo.get("type", "")
                    pdesc = pinfo.get("description", "")
                    print(f"    {req_mark} {pname} ({ptype}): {pdesc}")
            print()


def cmd_call(args):
    """Slack MCPツールを実行"""
    # --arg key=value を辞書に変換
    arguments = {}
    if args.arg:
        for item in args.arg:
            if "=" not in item:
                print(f"Error: Invalid argument format: {item} (expected key=value)", file=sys.stderr)
                sys.exit(1)
            key, value = item.split("=", 1)
            arguments[key] = parse_arg_value(value)

    with SlackMCPClient(
        workspace=args.workspace,
        debug=args.debug,
    ) as client:
        result = client.call_tool(args.tool_name, arguments)
        print(extract_text(result))


def main():
    parser = argparse.ArgumentParser(
        description="Slack MCP CLI - Slack操作（検索・送信・チャンネル読み取り等）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ログイン
  %(prog)s login

  # ワークスペース確認
  %(prog)s workspaces

  # ツール一覧
  %(prog)s tools

  # メッセージ検索
  %(prog)s call slack_search_public --arg query="hello" --arg count=3

  # メッセージ送信
  %(prog)s call slack_send_message --arg channel_id="C..." --arg message="Hello!"

  # チャンネル読み取り
  %(prog)s call slack_read_channel --arg channel_id="C..."
        """
    )
    parser.add_argument("--debug", action="store_true", help="デバッグログを出力")
    parser.add_argument("--workspace", default=None, help="ワークスペースキー（省略時はデフォルト）")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # login
    p_login = subparsers.add_parser("login", help="OAuth PKCEフローでログイン")
    p_login.add_argument("--url-only", action="store_true",
                         help="認証URLのみ出力して終了（ヘッドレス環境用ステップ1）")
    p_login.add_argument("--code", metavar="CALLBACK_URL",
                         help="コールバックURLでトークン取得（ヘッドレス環境用ステップ2）")

    # logout
    p_logout = subparsers.add_parser("logout", help="ワークスペースのトークンを削除")
    p_logout.add_argument("workspace", help="ワークスペースキー")

    # workspaces
    subparsers.add_parser("workspaces", help="保存済みワークスペース一覧")

    # set-default
    p_default = subparsers.add_parser("set-default", help="デフォルトワークスペースを設定")
    p_default.add_argument("workspace", help="ワークスペースキー")

    # tools
    subparsers.add_parser("tools", help="利用可能なSlack MCPツール一覧")

    # call
    p_call = subparsers.add_parser("call", help="Slack MCPツールを実行")
    p_call.add_argument("tool_name", help="ツール名")
    p_call.add_argument("--arg", action="append", help="ツール引数 (key=value形式、複数指定可)")

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "workspaces": cmd_workspaces,
        "set-default": cmd_set_default,
        "tools": cmd_tools,
        "call": cmd_call,
    }

    try:
        commands[args.command](args)
    except (TokenStoreError, OAuthError, SlackMCPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
