#!/usr/bin/env python3
"""YouTube channel analytics and trending search CLI."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CONFIG_DIR = Path.home() / ".config" / "youtube-analyzer"
CONFIG_PATH = CONFIG_DIR / "config.json"

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"config.json のパースに失敗しました: {e}", file=sys.stderr)
            sys.exit(1)


def resolve_api_key(config: dict) -> str | None:
    return os.environ.get("YOUTUBE_API_KEY") or config.get("api_key")


def resolve_credentials_path() -> Path:
    env = os.environ.get("YOUTUBE_CREDENTIALS_PATH")
    if env:
        return Path(env)
    return CONFIG_DIR / "credentials.json"


def resolve_token_path() -> Path:
    env = os.environ.get("YOUTUBE_TOKEN_PATH")
    if env:
        return Path(env)
    return CONFIG_DIR / "token.json"


def _atomic_write_file(file_path: Path, content: str) -> None:
    """ファイルをアトミックかつ安全なパーミッション(0o600)で書き込む。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    fd_open = True
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd_open = False
            f.write(content)
        os.replace(tmp_path, file_path)
    except Exception:
        if fd_open:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def load_oauth_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_path = resolve_token_path()
    if not token_path.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), OAUTH_SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _atomic_write_file(token_path, creds.to_json())
        except Exception as e:
            print(f"トークンのリフレッシュに失敗しました: {e}", file=sys.stderr)
            return None
    return creds


def handle_api_error(e: Exception) -> None:
    try:
        from googleapiclient.errors import HttpError
        if isinstance(e, HttpError):
            status = e.resp.status
            content = json.loads(e.content.decode("utf-8")) if e.content else {}
            errors = content.get("error", {}).get("errors", [])
            reason = errors[0].get("reason", "") if errors else ""

            if status == 403 and reason in ("quotaExceeded", "rateLimitExceeded"):
                print(
                    "YouTube API クォータを超過しました（10,000 units/day）。"
                    "明日以降に再試行してください。",
                    file=sys.stderr,
                )
                sys.exit(1)

            print(f"YouTube API エラー (HTTP {status}): {e}", file=sys.stderr)
            sys.exit(1)
    except ImportError:
        pass
    print(f"エラー: {e}", file=sys.stderr)
    sys.exit(1)


def cmd_auth_status(_config: dict, _args: argparse.Namespace) -> None:
    token_path = resolve_token_path()
    creds_path = resolve_credentials_path()

    status = {
        "credentials_path": str(creds_path),
        "credentials_exists": creds_path.exists(),
        "token_path": str(token_path),
        "token_exists": token_path.exists(),
        "authenticated": False,
        "expiry": None,
    }

    if token_path.exists():
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(
                str(token_path), OAUTH_SCOPES
            )
            status["authenticated"] = creds.valid or (
                creds.expired and creds.refresh_token is not None
            )
            if creds.expiry:
                status["expiry"] = creds.expiry.isoformat()
        except Exception as e:
            print(f"トークンの読み込みに失敗しました: {e}", file=sys.stderr)
            status["authenticated"] = False

    print(json.dumps(status, ensure_ascii=False, indent=2))


def cmd_auth_login(_config: dict, args: argparse.Namespace) -> None:
    creds_path = resolve_credentials_path()
    token_path = resolve_token_path()

    if not creds_path.exists():
        print(
            f"credentials.json が見つかりません: {creds_path}\n"
            "GCPコンソールでOAuth 2.0クライアントIDを作成し、\n"
            "credentials.jsonを上記パスに配置してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path),
        scopes=OAUTH_SCOPES,
        redirect_uri="http://localhost:8080/",
    )

    state_path = CONFIG_DIR / ".oauth_state"

    if args.url_only:
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        _atomic_write_file(state_path, state)
        print(auth_url)
        return

    if args.code:
        callback_url = args.code
        parsed = urlparse(callback_url)
        qs = parse_qs(parsed.query)
        code = qs.get("code", [None])[0]

        if not code:
            print(
                "コールバックURLからcodeパラメータを取得できませんでした。",
                file=sys.stderr,
            )
            sys.exit(1)

        callback_state = qs.get("state", [None])[0]
        try:
            saved_state = state_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            print(
                "--url-only で認証URLを取得してから --code を実行してください。",
                file=sys.stderr,
            )
            sys.exit(1)

        if not callback_state or not secrets.compare_digest(callback_state, saved_state):
            print(
                "stateパラメータが一致しません（CSRF攻撃の可能性）",
                file=sys.stderr,
            )
            sys.exit(1)

        flow.fetch_token(code=code)
        creds = flow.credentials

        _atomic_write_file(token_path, creds.to_json())

        if state_path.exists():
            state_path.unlink()

        print(json.dumps({
            "status": "認証成功",
            "token_path": str(token_path),
        }, ensure_ascii=False, indent=2))
        return

    print("--url-only または --code を指定してください。", file=sys.stderr)
    sys.exit(1)


def cmd_analyze(_config: dict, args: argparse.Namespace) -> None:
    creds = load_oauth_credentials()
    if creds is None:
        print(
            "OAuth2認証が必要です。以下の手順で認証してください:\n"
            "  1. credentials.json を ~/.config/youtube-analyzer/ に配置\n"
            "  2. uv run python youtube.py auth login --url-only で認証URLを取得\n"
            "  3. ブラウザで認証後、コールバックURLを取得\n"
            "  4. uv run python youtube.py auth login --code '<URL>' でトークン保存",
            file=sys.stderr,
        )
        sys.exit(1)

    from googleapiclient.discovery import build

    try:
        youtube = build("youtube", "v3", credentials=creds)
        channels_resp = youtube.channels().list(
            part="id,snippet,statistics", mine=True
        ).execute()

        if not channels_resp.get("items"):
            print("チャンネル情報を取得できませんでした。", file=sys.stderr)
            sys.exit(1)

        channel = channels_resp["items"][0]
        channel_id = channel["id"]

        analytics = build("youtubeAnalytics", "v2", credentials=creds)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

        analytics_resp = analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
            dimensions="day",
            sort="-day",
        ).execute()

        top_videos_resp = analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="video",
            sort="-views",
            maxResults=10,
        ).execute()

        video_ids = [
            row[0] for row in top_videos_resp.get("rows", []) if row
        ]
        video_details = {}
        if video_ids:
            vids_resp = youtube.videos().list(
                part="snippet", id=",".join(video_ids)
            ).execute()
            for item in vids_resp.get("items", []):
                video_details[item["id"]] = item["snippet"]["title"]

        top_videos = []
        for row in top_videos_resp.get("rows", []):
            vid_id = row[0]
            top_videos.append({
                "video_id": vid_id,
                "title": video_details.get(vid_id, "不明"),
                "views": row[1],
                "estimated_minutes_watched": row[2],
            })

        total_views = sum(row[1] for row in analytics_resp.get("rows", []))
        total_minutes = sum(row[2] for row in analytics_resp.get("rows", []))

        result = {
            "channel": {
                "id": channel_id,
                "title": channel["snippet"]["title"],
                "subscribers": channel["statistics"].get("subscriberCount"),
                "total_videos": channel["statistics"].get("videoCount"),
            },
            "period": {
                "start": start_date,
                "end": end_date,
                "days": args.days,
            },
            "summary": {
                "total_views": total_views,
                "total_minutes_watched": total_minutes,
            },
            "top_videos": top_videos,
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        handle_api_error(e)


def cmd_trending(config: dict, args: argparse.Namespace) -> None:
    api_key = resolve_api_key(config)
    if not api_key:
        print(
            "YOUTUBE_API_KEY が設定されていません。\n"
            "環境変数 YOUTUBE_API_KEY を設定するか、\n"
            "~/.config/youtube-analyzer/config.json の api_key に設定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    from googleapiclient.discovery import build

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        search_resp = youtube.search().list(
            part="snippet",
            q=args.keyword,
            type="video",
            order="viewCount",
            regionCode=args.region,
            maxResults=args.max_results,
        ).execute()

        video_ids = [
            item["id"]["videoId"]
            for item in search_resp.get("items", [])
            if item["id"].get("videoId")
        ]

        videos_with_stats = []
        if video_ids:
            stats_resp = youtube.videos().list(
                part="statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()

            stats_map = {}
            for item in stats_resp.get("items", []):
                stats_map[item["id"]] = {
                    "view_count": item["statistics"].get("viewCount"),
                    "like_count": item["statistics"].get("likeCount"),
                    "comment_count": item["statistics"].get("commentCount"),
                    "duration": item["contentDetails"].get("duration"),
                }

            for item in search_resp.get("items", []):
                vid_id = item["id"].get("videoId")
                if not vid_id:
                    continue
                snippet = item["snippet"]
                stats = stats_map.get(vid_id, {})
                videos_with_stats.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "view_count": stats.get("view_count"),
                    "like_count": stats.get("like_count"),
                    "comment_count": stats.get("comment_count"),
                    "duration": stats.get("duration"),
                })

        result = {
            "keyword": args.keyword,
            "region": args.region,
            "total_results": search_resp.get("pageInfo", {}).get(
                "totalResults", 0
            ),
            "videos": videos_with_stats,
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        handle_api_error(e)


def cmd_config_show(config: dict, _args: argparse.Namespace) -> None:
    token_path = resolve_token_path()
    creds_path = resolve_credentials_path()

    display = {
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
        "config": config if config else None,
        "credentials_path": str(creds_path),
        "credentials_exists": creds_path.exists(),
        "token_path": str(token_path),
        "token_exists": token_path.exists(),
        "env": {
            "YOUTUBE_API_KEY": "設定済み" if os.environ.get("YOUTUBE_API_KEY") else None,
            "YOUTUBE_CREDENTIALS_PATH": os.environ.get("YOUTUBE_CREDENTIALS_PATH"),
            "YOUTUBE_TOKEN_PATH": os.environ.get("YOUTUBE_TOKEN_PATH"),
        },
    }
    if display["config"] and "api_key" in display["config"]:
        masked = dict(display["config"])
        masked["api_key"] = "設定済み（****）"
        display["config"] = masked
    print(json.dumps(display, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube",
        description="YouTube channel analytics and trending search CLI",
    )
    sub = parser.add_subparsers(dest="command")

    auth_parser = sub.add_parser("auth", help="認証管理")
    auth_sub = auth_parser.add_subparsers(dest="auth_command")
    auth_sub.add_parser("status", help="認証状態を確認")
    login_parser = auth_sub.add_parser("login", help="OAuth2認証を実行")
    login_parser.add_argument(
        "--url-only", action="store_true", help="認証URLのみ出力"
    )
    login_parser.add_argument(
        "--code", default=None, help="コールバックURL"
    )

    analyze_parser = sub.add_parser("analyze", help="チャンネル分析")
    analyze_parser.add_argument(
        "--days", type=int, default=28, help="分析対象の日数 (デフォルト: 28)"
    )

    trending_parser = sub.add_parser("trending", help="トレンド検索")
    trending_parser.add_argument(
        "--keyword", required=True, help="検索キーワード"
    )
    trending_parser.add_argument(
        "--max-results", type=int, default=20, help="取得件数 (デフォルト: 20)"
    )
    trending_parser.add_argument(
        "--region", default="JP", help="リージョンコード (デフォルト: JP)"
    )

    config_parser = sub.add_parser("config", help="設定管理")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="現在の設定・認証状態を表示")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    config = load_config()

    if args.command == "auth":
        if args.auth_command == "status":
            cmd_auth_status(config, args)
        elif args.auth_command == "login":
            cmd_auth_login(config, args)
        else:
            print("usage: youtube auth {status|login}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "config":
        if args.config_command == "show":
            cmd_config_show(config, args)
        else:
            print("usage: youtube config {show}", file=sys.stderr)
            sys.exit(1)
        return

    dispatch = {
        "analyze": cmd_analyze,
        "trending": cmd_trending,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(config, args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
