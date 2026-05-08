#!/usr/bin/env python3
"""
Devin Session API CLI

Devin REST Session API（https://api.devin.ai）にタスク委任・状態確認・メッセージ送信を行う CLI。
DeepWiki などの調査系ツールは .mcp.json 経由の Devin MCP サーバー（https://mcp.devin.ai/mcp）で
提供されるため、本スクリプトは Session API のみを担う。

Usage:
    python deepwiki_cli.py run "タスク指示"
    python deepwiki_cli.py status <session_id>
    python deepwiki_cli.py message <session_id> "メッセージ"
"""

import argparse
import json
import os
import sys

sys.path.insert(0, sys.path[0] or ".")
from devin_session_client import DevinSessionClient, DevinSessionError


def get_api_key(args) -> str:
    return args.api_key or os.environ.get("DEVIN_API_KEY") or ""


def make_session_client(args) -> DevinSessionClient:
    return DevinSessionClient(
        api_key=get_api_key(args),
        debug=args.debug,
    )


def cmd_run(args):
    client = make_session_client(args)

    tags = None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]

    result = client.create_session(
        prompt=args.prompt,
        title=args.title,
        tags=tags,
        idempotent=args.idempotent,
    )

    session_id = result.get("session_id", "")
    url = result.get("url", "")
    is_new = result.get("is_new_session", True)

    print(f"Session ID: {session_id}")
    print(f"URL: {url}")
    if not is_new:
        print("(既存セッションを再利用)")

    if args.wait:
        print(f"\n完了待機中（interval={args.interval}s, timeout={args.timeout}s）...")
        final = client.wait_for_completion(session_id, interval=args.interval, timeout=args.timeout)
        _print_session_summary(final)


def cmd_status(args):
    client = make_session_client(args)
    result = client.get_session(args.session_id)
    _print_session_summary(result)


def cmd_message(args):
    client = make_session_client(args)
    client.send_message(args.session_id, args.message)
    print(f"Message sent to session {args.session_id}")


def _print_session_summary(session: dict):
    print(f"\nSession: {session.get('session_id', '')}")
    print(f"Status: {session.get('status_enum', session.get('status', ''))}")
    print(f"Title: {session.get('title', '')}")

    pr = session.get("pull_request")
    if pr and pr.get("url"):
        print(f"PR: {pr['url']}")

    structured = session.get("structured_output")
    if structured:
        print(f"Output: {json.dumps(structured, ensure_ascii=False, indent=2)}")

    messages = session.get("messages", [])
    if messages:
        print(f"\n--- Messages ({len(messages)}) ---")
        for msg in messages[-5:]:
            role = msg.get("role", "") or msg.get("type", "") or msg.get("origin", "")
            content = msg.get("content", "") or msg.get("message", "")
            if len(content) > 500:
                content = content[:500] + "..."
            print(f"[{role}] {content}")


def main():
    parser = argparse.ArgumentParser(
        description="Devin Session API CLI - タスク委任・状態確認・メッセージ送信",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run "docsディレクトリの中身を確認して報告してください"
  %(prog)s status <session_id>
  %(prog)s message <session_id> "追加の指示"

  環境変数 DEVIN_API_KEY が設定されていれば --api-key は省略可
        """
    )
    parser.add_argument("--debug", action="store_true", help="デバッグログを出力")
    parser.add_argument("--api-key", default=None, help="Bearer認証用APIキー（環境変数 DEVIN_API_KEY でも可）")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_run = subparsers.add_parser("run", help="セッション作成・タスク実行")
    p_run.add_argument("prompt", help="タスク指示")
    p_run.add_argument("--title", default=None, help="セッションタイトル")
    p_run.add_argument("--tags", default=None, help="タグ（カンマ区切り）")
    p_run.add_argument("--idempotent", action="store_true", help="べき等モード")
    p_run.add_argument("--wait", action="store_true", help="完了まで待機")
    p_run.add_argument("--interval", type=int, default=15, help="ポーリング間隔秒数（デフォルト: 15）")
    p_run.add_argument("--timeout", type=int, default=600, help="ポーリングタイムアウト秒数（デフォルト: 600）")

    p_status = subparsers.add_parser("status", help="セッション状態確認")
    p_status.add_argument("session_id", help="セッションID")

    p_message = subparsers.add_parser("message", help="セッションにメッセージ送信")
    p_message.add_argument("session_id", help="セッションID")
    p_message.add_argument("message", help="メッセージ本文")

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "status": cmd_status,
        "message": cmd_message,
    }

    try:
        commands[args.command](args)
    except DevinSessionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
