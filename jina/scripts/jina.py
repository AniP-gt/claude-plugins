#!/usr/bin/env python3
"""
Jina AI Remote MCP Server Wrapper

mcp.jina.ai/v1 (Streamable HTTP) に JSON-RPC で直接ツール呼び出しを行うラッパースクリプト。
認証ヘッダ ``Authorization: Bearer ${JINA_API_KEY}`` は ``~/.config/jina/secrets.env``
から読み込む。

Usage:
    jina tools
    jina primer
    jina read <url>
    jina search <query> [--source web|arxiv|ssrn|images|blog|bibtex]
    jina screenshot <url>
    jina expand <query>
    jina extract-pdf <url>
    jina rerank <query> <doc> [<doc> ...]
    jina classify --labels <a,b,c> <text> [<text> ...]
    jina dedup <text> [<text> ...] [--top-k <n>]
    jina call <tool_name> [--args <json>]

Examples:
    # ツール一覧（schema 含む）を取得
    jina tools

    # URL からクリーンな markdown を抽出
    jina read "https://example.com/article"

    # Web 検索
    jina search "Claude Code MCP plugin"

    # arXiv 検索
    jina search "diffusion transformer" --source arxiv

    # 任意のツールを直接呼び出し（schema は `jina tools` で確認）
    jina call read_url --args '{"url":"https://example.com"}'
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

JINA_MCP_URL = "https://mcp.jina.ai/v1"
CONFIG_DIR = Path.home() / ".config" / "jina"
SECRETS_FILE = CONFIG_DIR / "secrets.env"
TEMPLATES_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent)) / "templates"


def ensure_secrets_file():
    """~/.config/jina/secrets.env が無ければテンプレートからコピー（既存は上書きしない）。"""
    if SECRETS_FILE.exists():
        return
    template = TEMPLATES_DIR / "secrets.example.env"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if template.exists():
        SECRETS_FILE.write_text(template.read_text(), encoding="utf-8")
    else:
        SECRETS_FILE.write_text("JINA_API_KEY=\n", encoding="utf-8")


def load_secrets():
    """secrets.env を読み込み、未設定の環境変数をセットする（既存環境変数は尊重）。"""
    ensure_secrets_file()
    if not SECRETS_FILE.exists():
        return
    with open(SECRETS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def parse_streamable_response(content_type: str, raw: str):
    """Streamable HTTP のレスポンス（JSON または SSE）を JSON に正規化する。"""
    if "text/event-stream" in content_type:
        for chunk in raw.split("\n\n"):
            for line in chunk.split("\n"):
                line = line.strip()
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    if not payload:
                        continue
                    try:
                        return json.loads(payload)
                    except json.JSONDecodeError:
                        continue
        return {"error": True, "message": "No data line in SSE response", "raw": raw}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": True, "message": f"Invalid JSON: {e}", "raw": raw}


def call_mcp(method: str, params=None, request_id: int = 1, timeout: int = 120):
    """Jina MCP サーバーに JSON-RPC を POST して結果を返す。"""
    load_secrets()
    api_key = os.environ.get("JINA_API_KEY", "").strip()

    body = {"jsonrpc": "2.0", "method": method, "id": request_id}
    if params is not None:
        body["params"] = params

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "jina-claude-plugin/0.1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(JINA_MCP_URL, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8", errors="replace")
            return parse_streamable_response(content_type, raw)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        return {"error": True, "message": f"HTTP {e.code} {e.reason}", "body": err_body}
    except urllib.error.URLError as e:
        return {"error": True, "message": f"URL error: {e.reason}"}
    except Exception as e:  # noqa: BLE001
        return {"error": True, "message": str(e)}


def call_tool(tool_name: str, arguments=None):
    """tools/call を呼ぶ。"""
    return call_mcp(
        "tools/call",
        {"name": tool_name, "arguments": arguments or {}},
        request_id=2,
    )


def list_tools():
    """tools/list を呼ぶ。"""
    return call_mcp("tools/list", {}, request_id=3)


# --- subcommand handlers ---------------------------------------------------

def cmd_tools(_args):
    return list_tools()


def cmd_call(args):
    arguments = {}
    if args.args:
        arguments = json.loads(args.args)
    return call_tool(args.tool, arguments)


def cmd_primer(_args):
    return call_tool("primer", {})


def cmd_read(args):
    return call_tool("read_url", {"url": args.url})


def cmd_search(args):
    tool_map = {
        "web": "search_web",
        "arxiv": "search_arxiv",
        "ssrn": "search_ssrn",
        "images": "search_images",
        "blog": "search_jina_blog",
        "bibtex": "search_bibtex",
    }
    tool = tool_map.get(args.source, "search_web")
    return call_tool(tool, {"query": args.query})


def cmd_screenshot(args):
    return call_tool("capture_screenshot_url", {"url": args.url})


def cmd_expand(args):
    return call_tool("expand_query", {"query": args.query})


def cmd_extract_pdf(args):
    return call_tool("extract_pdf", {"url": args.url})


def cmd_rerank(args):
    return call_tool(
        "sort_by_relevance",
        {"query": args.query, "documents": args.documents},
    )


def cmd_classify(args):
    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    return call_tool("classify_text", {"texts": args.texts, "labels": labels})


def cmd_dedup(args):
    return call_tool(
        "deduplicate_strings",
        {"strings": args.texts, "top_k": args.top_k},
    )


# --- argparse setup --------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Jina AI Remote MCP Server Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", help="Subcommands")

    sub.add_parser("tools", help="List available MCP tools (with schema)")
    sub.add_parser("primer", help="Get current contextual info (time/locale)")

    p_call = sub.add_parser("call", help="Call any MCP tool with raw JSON arguments")
    p_call.add_argument("tool", type=str, help="Tool name (see `jina tools`)")
    p_call.add_argument("--args", type=str, default=None, help="Arguments as JSON string")

    p_read = sub.add_parser("read", help="Extract clean markdown from a URL")
    p_read.add_argument("url", type=str, help="Target URL")

    p_search = sub.add_parser("search", help="Search the web / arxiv / ssrn / images / blog / bibtex")
    p_search.add_argument("query", type=str, help="Search query")
    p_search.add_argument(
        "--source", "-s",
        type=str, default="web",
        choices=["web", "arxiv", "ssrn", "images", "blog", "bibtex"],
        help="Search source (default: web)",
    )

    p_shot = sub.add_parser("screenshot", help="Capture screenshot of a URL")
    p_shot.add_argument("url", type=str, help="Target URL")

    p_expand = sub.add_parser("expand", help="Expand / rewrite a search query")
    p_expand.add_argument("query", type=str, help="Query to expand")

    p_pdf = sub.add_parser("extract-pdf", help="Extract figures/tables/equations from PDF URL")
    p_pdf.add_argument("url", type=str, help="PDF URL (arXiv etc.)")

    p_rerank = sub.add_parser("rerank", help="Rerank documents by relevance to a query")
    p_rerank.add_argument("query", type=str, help="Query")
    p_rerank.add_argument("documents", nargs="+", type=str, help="Documents to rerank")

    p_cls = sub.add_parser("classify", help="Classify texts into user-defined labels")
    p_cls.add_argument("--labels", required=True, type=str, help="Comma-separated labels")
    p_cls.add_argument("texts", nargs="+", type=str, help="Texts to classify")

    p_dedup = sub.add_parser("dedup", help="Get top-k semantically unique strings")
    p_dedup.add_argument("texts", nargs="+", type=str, help="Strings to deduplicate")
    p_dedup.add_argument("--top-k", type=int, default=10, help="Max unique strings (default: 10)")

    return parser


HANDLERS = {
    "tools": cmd_tools,
    "call": cmd_call,
    "primer": cmd_primer,
    "read": cmd_read,
    "search": cmd_search,
    "screenshot": cmd_screenshot,
    "expand": cmd_expand,
    "extract-pdf": cmd_extract_pdf,
    "rerank": cmd_rerank,
    "classify": cmd_classify,
    "dedup": cmd_dedup,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handler = HANDLERS.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

    try:
        result = handler(args)
    except Exception as e:  # noqa: BLE001
        err = {"error": True, "command": args.command, "message": str(e)}
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    print("=" * 50)
    print("Result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if isinstance(result, dict):
        if result.get("error"):
            sys.exit(1)
        inner = result.get("result")
        if isinstance(inner, dict) and inner.get("isError"):
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
