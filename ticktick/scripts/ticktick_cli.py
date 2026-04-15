#!/usr/bin/env python3
"""
TickTick CLI

TickTick APIクライアントのCLIエントリーポイント。
OAuth認証、認証管理、TickTickタスク・プロジェクト操作を行う。

Usage:
    python ticktick_cli.py setup
    python ticktick_cli.py login
    python ticktick_cli.py logout
    python ticktick_cli.py status
    python ticktick_cli.py call <operation> [--arg key=value ...]
"""

import sys
import os
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError
from oauth import login, login_url_only, login_with_code, OAuthError
from ticktick_client import TickTickClient, TickTickClientError


class CLIError(Exception):
    """CLIの引数・入力エラー"""
    pass


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


def parse_args_to_dict(arg_list) -> dict:
    """--arg key=value リストを辞書に変換。不正な形式は CLIError を raise。"""
    result = {}
    if not arg_list:
        return result
    for item in arg_list:
        if "=" not in item:
            raise CLIError(f"Invalid argument format: {item} (expected key=value)")
        key, value = item.split("=", 1)
        result[key] = parse_arg_value(value)
    return result


def _require_arg(kwargs: dict, *keys: str) -> None:
    """必須引数が全て存在するか検証。不足時は CLIError を raise。"""
    missing = [k for k in keys if not kwargs.get(k)]
    if missing:
        raise CLIError(f"{', '.join(missing)} is required")


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_setup(args):
    if args.client_id and args.client_secret:
        client_id = args.client_id
        client_secret = args.client_secret
    else:
        print("TickTick developer portal (https://developer.ticktick.com/) でアプリ登録後、")
        print("以下の情報を入力してください。")
        print()
        try:
            client_id = input("Client ID: ").strip()
            client_secret = input("Client Secret: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(1)

    if not client_id or not client_secret:
        raise CLIError("client_id と client_secret は必須です")

    store = TokenStore()
    store.save_client_credentials(client_id, client_secret)
    print("Client credentials saved.")
    print("次に 'login' を実行して認証してください:")
    print("  python ticktick_cli.py login --url-only")


def cmd_login(args):
    if args.url_only:
        login_url_only()
    elif args.code:
        login_with_code(args.code)
    else:
        login()


def cmd_logout(args):
    store = TokenStore()
    if store.is_authenticated():
        store.remove_auth()
        print("Logged out successfully.")
    else:
        print("Not currently authenticated.")


def cmd_status(args):
    store = TokenStore()
    auth = store.get_auth()
    creds = store.get_client_credentials()

    if not auth or not auth.get("access_token"):
        print("Status: Not authenticated")
        print("Run 'setup' then 'login' to authenticate with TickTick.")
        return

    authenticated_at = auth.get("authenticated_at", 0)
    elapsed_days = (int(time.time()) - authenticated_at) // 86400

    print("Status: Authenticated")
    print(f"  Scope: {auth.get('scope', 'N/A')}")
    print(f"  Authenticated: {elapsed_days} days ago")
    if creds:
        print(f"  Client ID: {creds['client_id'][:16]}...")


def _handle_get_projects(client: TickTickClient, kwargs: dict) -> None:
    _print_json(client.get_projects())


def _handle_get_project(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId")
    _print_json(client.get_project(kwargs["projectId"]))


def _handle_get_project_data(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId")
    _print_json(client.get_project_data(kwargs["projectId"]))


def _handle_create_project(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "name")
    _print_json(client.create_project(
        name=kwargs["name"],
        color=kwargs.get("color", ""),
        view_mode=kwargs.get("viewMode", "list"),
        kind=kwargs.get("kind", "TASK"),
    ))


def _handle_update_project(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId")
    project_id = kwargs.pop("projectId")
    _print_json(client.update_project(project_id, **kwargs))


def _handle_delete_project(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId")
    client.delete_project(kwargs["projectId"])
    print("Project deleted.")


def _handle_get_task(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId", "taskId")
    _print_json(client.get_task(kwargs["projectId"], kwargs["taskId"]))


def _handle_create_task(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "title")
    _print_json(client.create_task(
        title=kwargs["title"],
        project_id=kwargs.get("projectId", ""),
        content=kwargs.get("content", ""),
        due_date=kwargs.get("dueDate", ""),
        priority=int(kwargs.get("priority", 0)),
        tags=kwargs.get("tags"),
        is_all_day=bool(kwargs.get("isAllDay", False)),
    ))


def _handle_update_task(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "taskId")
    task_id = kwargs.pop("taskId")
    _print_json(client.update_task(task_id, **kwargs))


def _handle_complete_task(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId", "taskId")
    client.complete_task(kwargs["projectId"], kwargs["taskId"])
    print("Task completed.")


def _handle_delete_task(client: TickTickClient, kwargs: dict) -> None:
    _require_arg(kwargs, "projectId", "taskId")
    client.delete_task(kwargs["projectId"], kwargs["taskId"])
    print("Task deleted.")


def _handle_batch_tasks(client: TickTickClient, kwargs: dict) -> None:
    _print_json(client.batch_tasks(
        add=kwargs.get("add"),
        update=kwargs.get("update"),
        delete=kwargs.get("delete"),
    ))


_OPERATION_HANDLERS = {
    "get-projects": _handle_get_projects,
    "get-project": _handle_get_project,
    "get-project-data": _handle_get_project_data,
    "create-project": _handle_create_project,
    "update-project": _handle_update_project,
    "delete-project": _handle_delete_project,
    "get-task": _handle_get_task,
    "create-task": _handle_create_task,
    "update-task": _handle_update_task,
    "complete-task": _handle_complete_task,
    "delete-task": _handle_delete_task,
    "batch-tasks": _handle_batch_tasks,
}


def cmd_call(args):
    kwargs = parse_args_to_dict(args.arg)
    client = TickTickClient(debug=args.debug)
    op = args.operation

    handler = _OPERATION_HANDLERS.get(op)
    if handler is None:
        raise CLIError(f"Unknown operation '{op}'. Run 'help' to see available operations.")
    handler(client, kwargs)


def cmd_help(args):
    print("""
TickTick CLI - 利用可能な操作

セットアップ:
  setup                   client_id, client_secret を設定
  login [--url-only]      OAuth認証（--url-only でURL取得のみ）
  login --code <URL>      コールバックURLでトークン取得
  logout                  認証トークンを削除
  status                  認証状態を確認

プロジェクト操作:
  call get-projects                           全プロジェクト一覧
  call get-project --arg projectId=<id>       プロジェクト詳細
  call get-project-data --arg projectId=<id>  プロジェクト＋タスク一覧
  call create-project --arg name=<name>       プロジェクト作成
  call update-project --arg projectId=<id> --arg name=<name>  プロジェクト更新
  call delete-project --arg projectId=<id>   プロジェクト削除

タスク操作:
  call get-task --arg projectId=<id> --arg taskId=<id>   タスク取得
  call create-task --arg title=<title> [--arg projectId=<id>]  タスク作成
  call update-task --arg taskId=<id> --arg title=<title>  タスク更新
  call complete-task --arg projectId=<id> --arg taskId=<id>  タスク完了
  call delete-task --arg projectId=<id> --arg taskId=<id>   タスク削除
  call batch-tasks --arg add='[{...}]'       バッチ操作

タスク優先度: 0=なし, 1=低, 3=中, 5=高
""")


def main():
    parser = argparse.ArgumentParser(
        description="TickTick CLI - タスク管理・プロジェクト操作",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--debug", action="store_true", help="デバッグログを出力")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_setup = subparsers.add_parser("setup", help="client_id, client_secretを設定")
    p_setup.add_argument("--client-id", metavar="CLIENT_ID", help="TickTick Client ID")
    p_setup.add_argument("--client-secret", metavar="CLIENT_SECRET", help="TickTick Client Secret")

    p_login = subparsers.add_parser("login", help="OAuth認証")
    p_login.add_argument("--url-only", action="store_true",
                         help="認証URLのみ出力して終了（ヘッドレス環境用ステップ1）")
    p_login.add_argument("--code", metavar="CALLBACK_URL",
                         help="コールバックURLでトークン取得（ヘッドレス環境用ステップ2）")

    subparsers.add_parser("logout", help="認証トークンを削除")
    subparsers.add_parser("status", help="認証状態を表示")

    p_call = subparsers.add_parser("call", help="TickTick API操作を実行")
    p_call.add_argument("operation", help="操作名")
    p_call.add_argument("--arg", action="append", help="引数 (key=value形式、複数指定可)")

    subparsers.add_parser("help", help="利用可能な操作一覧")

    args = parser.parse_args()

    commands = {
        "setup": cmd_setup,
        "login": cmd_login,
        "logout": cmd_logout,
        "status": cmd_status,
        "call": cmd_call,
        "help": cmd_help,
    }

    try:
        commands[args.command](args)
    except (CLIError, TokenStoreError, OAuthError, TickTickClientError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
