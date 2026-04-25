#!/usr/bin/env python3
"""GA4 data retrieval CLI. Supports accounts, property info, reports, and realtime data."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "ga4" / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"config.json のパースに失敗しました: {e}", file=sys.stderr)
            sys.exit(1)


def resolve_property_id(args_property: str | None, config: dict) -> str | None:
    if args_property is not None:
        raw = args_property
    else:
        raw = os.environ.get("GA4_PROPERTY_ID") or config.get("default")
    if raw is None:
        return None
    properties_map = config.get("properties", {})
    if str(raw).isdigit():
        return str(raw)
    if raw in properties_map:
        return str(properties_map[raw])
    return raw


def ensure_property_id(args_property: str | None, config: dict) -> str:
    pid = resolve_property_id(args_property, config)
    if pid is None:
        print("property IDが指定されていません。--property, GA4_PROPERTY_ID環境変数, "
              "またはconfig.jsonのdefaultで指定してください。", file=sys.stderr)
        sys.exit(1)
    return pid


def format_property_name(property_id: str) -> str:
    if property_id.startswith("properties/"):
        return property_id
    return f"properties/{property_id}"


def parse_names(csv: str, label: str) -> list[str]:
    """カンマ区切りの名前リストをパースし、空を除去して検証する"""
    names = [n.strip() for n in csv.split(",") if n.strip()]
    if not names:
        print(f"少なくとも1つの{label}を指定してください。", file=sys.stderr)
        sys.exit(1)
    return names


def get_credentials(config: dict):
    from google.auth.exceptions import DefaultCredentialsError
    from google.oauth2 import service_account

    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]

    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path:
        try:
            return service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
        except (FileNotFoundError, ValueError) as e:
            print(f"認証ファイルの読み込みに失敗しました ({sa_path}): {e}", file=sys.stderr)
            sys.exit(1)

    config_creds = config.get("credentials_file")
    if config_creds:
        expanded = os.path.expanduser(config_creds)
        try:
            return service_account.Credentials.from_service_account_file(expanded, scopes=scopes)
        except (FileNotFoundError, ValueError) as e:
            print(f"認証ファイルの読み込みに失敗しました ({expanded}): {e}", file=sys.stderr)
            sys.exit(1)

    try:
        import google.auth
        creds, _ = google.auth.default(scopes=scopes)
        return creds
    except DefaultCredentialsError:
        print("認証情報が見つかりません。以下のいずれかで設定してください:\n"
              "  1. GOOGLE_APPLICATION_CREDENTIALS 環境変数\n"
              "  2. ~/.config/ga4/config.json の credentials_file\n"
              "  3. gcloud auth application-default login "
              "--scopes=https://www.googleapis.com/auth/analytics.readonly",
              file=sys.stderr)
        sys.exit(1)


def get_admin_client(config: dict):
    from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient

    creds = get_credentials(config)
    return AnalyticsAdminServiceClient(credentials=creds)


def get_data_client(config: dict):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient

    creds = get_credentials(config)
    return BetaAnalyticsDataClient(credentials=creds)


_MAX_LIST_RESULTS = 100


def cmd_accounts(config: dict, _args: argparse.Namespace) -> None:
    client = get_admin_client(config)
    results = []
    for summary in client.list_account_summaries(timeout=30.0):
        account_entry = {
            "account": summary.account,
            "display_name": summary.display_name,
            "property_summaries": [
                {
                    "property": ps.property,
                    "display_name": ps.display_name,
                }
                for ps in summary.property_summaries
            ],
        }
        results.append(account_entry)
        if len(results) >= _MAX_LIST_RESULTS:
            break
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_property(config: dict, args: argparse.Namespace) -> None:
    pid = ensure_property_id(args.name_or_id, config)
    client = get_admin_client(config)
    prop = client.get_property(name=format_property_name(pid), timeout=30.0)
    result = {
        "name": prop.name,
        "display_name": prop.display_name,
        "property_type": str(prop.property_type),
        "industry_category": str(prop.industry_category),
        "time_zone": prop.time_zone,
        "currency_code": prop.currency_code,
        "create_time": prop.create_time.isoformat() if prop.create_time else None,
        "update_time": prop.update_time.isoformat() if prop.update_time else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_ads_links(config: dict, args: argparse.Namespace) -> None:
    pid = ensure_property_id(args.name_or_id, config)
    client = get_admin_client(config)
    parent = format_property_name(pid)
    results = []
    for link in client.list_google_ads_links(parent=parent, page_size=_MAX_LIST_RESULTS, timeout=30.0):
        results.append({
            "name": link.name,
            "customer_id": link.customer_id,
            "can_manage_clients": link.can_manage_clients,
            "creator_email_address": link.creator_email_address,
        })
        if len(results) >= _MAX_LIST_RESULTS:
            break
    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_report_request(property_id: str, args: argparse.Namespace):
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    metric_names = parse_names(args.metrics, "メトリクス")
    metrics = [Metric(name=m) for m in metric_names]

    start_date = getattr(args, "start_date", None) or "30daysAgo"
    end_date = getattr(args, "end_date", None) or "today"

    kwargs = {
        "property": format_property_name(property_id),
        "metrics": metrics,
        "date_ranges": [DateRange(start_date=start_date, end_date=end_date)],
        "limit": args.limit,
    }
    if args.dimensions:
        dim_names = parse_names(args.dimensions, "ディメンション")
        kwargs["dimensions"] = [Dimension(name=d) for d in dim_names]
    return RunReportRequest(**kwargs)


def rows_to_dicts(rows: list, dimension_headers: list, metric_headers: list) -> list[dict]:
    results = []
    for row in rows:
        entry = {}
        for dh, dv in zip(dimension_headers, row.dimension_values):
            entry[dh.name] = dv.value
        for mh, mv in zip(metric_headers, row.metric_values):
            entry[mh.name] = mv.value
        results.append(entry)
    return results


def cmd_report(config: dict, args: argparse.Namespace) -> None:
    pid = ensure_property_id(args.property, config)
    client = get_data_client(config)
    request = build_report_request(pid, args)

    response = client.run_report(request, timeout=30.0)

    results = rows_to_dicts(
        response.rows, response.dimension_headers, response.metric_headers
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_realtime(config: dict, args: argparse.Namespace) -> None:
    from google.analytics.data_v1beta.types import (
        Dimension,
        Metric,
        RunRealtimeReportRequest,
    )

    pid = ensure_property_id(args.property, config)
    client = get_data_client(config)

    metric_names = parse_names(args.metrics, "メトリクス")
    metrics = [Metric(name=m) for m in metric_names]
    request_params: dict = {
        "property": format_property_name(pid),
        "metrics": metrics,
        "limit": args.limit,
    }
    if args.dimensions:
        dim_names = parse_names(args.dimensions, "ディメンション")
        request_params["dimensions"] = [Dimension(name=d) for d in dim_names]

    response = client.run_realtime_report(
        RunRealtimeReportRequest(**request_params), timeout=30.0
    )
    results = rows_to_dicts(
        response.rows, response.dimension_headers, response.metric_headers
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_custom_dims(config: dict, args: argparse.Namespace) -> None:
    pid = ensure_property_id(args.property, config)
    client = get_admin_client(config)
    parent = format_property_name(pid)

    custom_dimensions = []
    for cd in client.list_custom_dimensions(parent=parent, page_size=_MAX_LIST_RESULTS, timeout=30.0):
        custom_dimensions.append({
            "name": cd.name,
            "parameter_name": cd.parameter_name,
            "display_name": cd.display_name,
            "description": cd.description,
            "scope": str(cd.scope),
        })
        if len(custom_dimensions) >= _MAX_LIST_RESULTS:
            break

    custom_metrics = []
    for cm in client.list_custom_metrics(parent=parent, page_size=_MAX_LIST_RESULTS, timeout=30.0):
        custom_metrics.append({
            "name": cm.name,
            "parameter_name": cm.parameter_name,
            "display_name": cm.display_name,
            "description": cm.description,
            "scope": str(cm.scope),
            "measurement_unit": str(cm.measurement_unit),
        })
        if len(custom_metrics) >= _MAX_LIST_RESULTS:
            break

    result = {
        "custom_dimensions": custom_dimensions,
        "custom_metrics": custom_metrics,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_config_show(config: dict, _args: argparse.Namespace) -> None:
    display = {
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
        "config": config if config else None,
        "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "GA4_PROPERTY_ID": os.environ.get("GA4_PROPERTY_ID"),
        },
    }
    print(json.dumps(display, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4",
        description="GA4 data retrieval CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("accounts", help="アカウント/プロパティ一覧を取得")

    p_prop = sub.add_parser("property", help="プロパティ詳細を取得")
    p_prop.add_argument("name_or_id", help="プロパティ名またはID")

    p_ads = sub.add_parser("ads-links", help="Google Adsリンク一覧を取得")
    p_ads.add_argument("name_or_id", help="プロパティ名またはID")

    p_report = sub.add_parser("report", help="レポートを取得")
    p_report.add_argument("--property", default=None, help="プロパティ名またはID")
    p_report.add_argument("--metrics", required=True, help="メトリクス (カンマ区切り)")
    p_report.add_argument("--dimensions", default=None, help="ディメンション (カンマ区切り)")
    p_report.add_argument("--start-date", default=None, dest="start_date", help="開始日 (例: 2024-01-01 or 30daysAgo)")
    p_report.add_argument("--end-date", default=None, dest="end_date", help="終了日 (例: 2024-01-31 or today)")
    p_report.add_argument("--limit", type=int, default=100, help="取得件数上限")

    p_rt = sub.add_parser("realtime", help="リアルタイムレポートを取得")
    p_rt.add_argument("--property", default=None, help="プロパティ名またはID")
    p_rt.add_argument("--metrics", required=True, help="メトリクス (カンマ区切り)")
    p_rt.add_argument("--dimensions", default=None, help="ディメンション (カンマ区切り)")
    p_rt.add_argument("--limit", type=int, default=100, help="取得件数上限")

    p_cd = sub.add_parser("custom-dims", help="カスタムディメンション/メトリクスを取得")
    p_cd.add_argument("--property", default=None, help="プロパティ名またはID")

    config_sub = sub.add_parser("config", help="設定管理")
    config_cmds = config_sub.add_subparsers(dest="config_command")
    config_cmds.add_parser("show", help="現在の設定・認証状態を表示")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    config = load_config()

    dispatch = {
        "accounts": cmd_accounts,
        "property": cmd_property,
        "ads-links": cmd_ads_links,
        "report": cmd_report,
        "realtime": cmd_realtime,
        "custom-dims": cmd_custom_dims,
    }

    if args.command == "config":
        if args.config_command == "show":
            cmd_config_show(config, args)
        else:
            print("usage: ga4 config {show}", file=sys.stderr)
            sys.exit(1)
        return

    handler = dispatch.get(args.command)
    if handler:
        try:
            from google.api_core import exceptions as gexc

            try:
                handler(config, args)
            except gexc.Unauthenticated as e:
                print(f"認証エラー: {e}", file=sys.stderr)
                sys.exit(2)
            except gexc.ResourceExhausted as e:
                print(f"クォータ超過: {e}", file=sys.stderr)
                sys.exit(3)
            except gexc.GoogleAPICallError as e:
                print(f"APIエラー: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception:
                import traceback
                traceback.print_exc()
                sys.exit(1)
        except ImportError:
            try:
                handler(config, args)
            except Exception:
                import traceback
                traceback.print_exc()
                sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
