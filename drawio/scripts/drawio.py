#!/usr/bin/env python3
"""
draw.io MCP Server Wrapper

npx @drawio/mcp を使用してダイアグラムを生成・表示するラッパースクリプト

Usage:
    drawio xml <content>
    drawio mermaid <content>
    drawio csv <content>
    drawio xml-file <file_path>
    drawio mermaid-file <file_path>
    drawio csv-file <file_path>

Examples:
    # Mermaid構文からフローチャートを生成
    drawio mermaid "graph TD; A-->B; B-->C;"

    # draw.io XMLをエディタで開く
    drawio xml "<mxfile>...</mxfile>"
"""

import argparse
import json
import os
import subprocess
import sys


def call_mcp_tool(tool_name, arguments=None):
    """
    draw.io MCPサーバーのツールを呼び出す

    npx @drawio/mcp を起動し、JSON-RPCでツールを呼び出す
    """
    if arguments is None:
        arguments = {}

    # MCP初期化リクエスト
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "drawio-cli", "version": "1.0.0"}
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
        result = subprocess.run(
            ["npx", "-y", "@drawio/mcp"],
            input=messages,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
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


def open_xml(content, lightbox=False, dark="auto"):
    """draw.io XMLをエディタで開く"""
    print(f"Opening draw.io XML ({len(content)} chars)\n")
    args = {"content": content}
    if lightbox:
        args["lightbox"] = True
    if dark != "auto":
        args["dark"] = dark
    return call_mcp_tool("open_drawio_xml", args)


def open_mermaid(content, lightbox=False, dark="auto"):
    """Mermaid構文をdraw.ioダイアグラムに変換して開く"""
    print(f"Converting Mermaid to draw.io diagram\n")
    print(f"Input:\n{content}\n")
    args = {"content": content}
    if lightbox:
        args["lightbox"] = True
    if dark != "auto":
        args["dark"] = dark
    return call_mcp_tool("open_drawio_mermaid", args)


def open_csv(content, lightbox=False, dark="auto"):
    """CSVデータをdraw.ioダイアグラムに変換して開く"""
    print(f"Converting CSV to draw.io diagram\n")
    print(f"Input:\n{content}\n")
    args = {"content": content}
    if lightbox:
        args["lightbox"] = True
    if dark != "auto":
        args["dark"] = dark
    return call_mcp_tool("open_drawio_csv", args)


def mermaid_to_drawio_xml(mermaid_content):
    """Mermaid構文をdraw.io XMLに変換（MermaidをmxGraphXMLとして埋め込む）"""
    from xml.sax.saxutils import escape
    escaped = escape(mermaid_content)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" type="device">
  <diagram name="Page-1" id="mermaid-diagram">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <object label="" mermaid="{escaped}" id="2">
          <mxCell style="shape=mxgraph.mermaid.chart;whiteSpace=wrap;" vertex="1" parent="1">
            <mxGeometry width="800" height="600" as="geometry"/>
          </mxCell>
        </object>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''


def export_drawio(content, output_path, source_format="mermaid"):
    """コンテンツを.drawioファイルとして出力"""
    print(f"Exporting to .drawio: {output_path}\n")

    if source_format == "mermaid":
        xml = mermaid_to_drawio_xml(content)
    elif source_format == "xml":
        xml = content
    else:
        return {"error": True, "message": f"Unsupported source format: {source_format}"}

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)

    size = os.path.getsize(output_path)
    return {"output": output_path, "format": "drawio", "size_bytes": size}


def read_file_content(file_path):
    """ファイルからコンテンツを読み込む"""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="draw.io MCP Server Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # 共通オプションを追加するヘルパー
    def add_common_options(p):
        p.add_argument("--lightbox", action="store_true", help="Open in lightbox mode (read-only)")
        p.add_argument("--dark", type=str, default="auto", choices=["auto", "true", "false"],
                        help="Dark mode (default: auto)")

    # xml コマンド
    xml_parser = subparsers.add_parser("xml", help="Open draw.io XML in editor")
    xml_parser.add_argument("content", type=str, help="draw.io XML content")
    add_common_options(xml_parser)

    # mermaid コマンド
    mermaid_parser = subparsers.add_parser("mermaid", help="Convert Mermaid to draw.io diagram")
    mermaid_parser.add_argument("content", type=str, help="Mermaid.js syntax")
    add_common_options(mermaid_parser)

    # csv コマンド
    csv_parser = subparsers.add_parser("csv", help="Convert CSV to draw.io diagram")
    csv_parser.add_argument("content", type=str, help="CSV data")
    add_common_options(csv_parser)

    # xml-file コマンド
    xml_file_parser = subparsers.add_parser("xml-file", help="Open draw.io XML from file")
    xml_file_parser.add_argument("file_path", type=str, help="Path to XML file")
    add_common_options(xml_file_parser)

    # mermaid-file コマンド
    mermaid_file_parser = subparsers.add_parser("mermaid-file", help="Convert Mermaid file to draw.io diagram")
    mermaid_file_parser.add_argument("file_path", type=str, help="Path to Mermaid file")
    add_common_options(mermaid_file_parser)

    # csv-file コマンド
    csv_file_parser = subparsers.add_parser("csv-file", help="Convert CSV file to draw.io diagram")
    csv_file_parser.add_argument("file_path", type=str, help="Path to CSV file")
    add_common_options(csv_file_parser)

    # export コマンド
    export_parser = subparsers.add_parser("export", help="Export Mermaid as .drawio file")
    export_parser.add_argument("content", type=str, help="Mermaid.js syntax")
    export_parser.add_argument("-o", "--output", type=str, required=True, help="Output file path (.drawio)")

    # export-file コマンド
    export_file_parser = subparsers.add_parser("export-file", help="Export Mermaid file as .drawio file")
    export_file_parser.add_argument("file_path", type=str, help="Path to Mermaid file")
    export_file_parser.add_argument("-o", "--output", type=str, required=True, help="Output file path (.drawio)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        lightbox = getattr(args, 'lightbox', False)
        dark = getattr(args, 'dark', 'auto')

        if args.command == "export":
            result = export_drawio(args.content, args.output, source_format="mermaid")
        elif args.command == "export-file":
            content = read_file_content(args.file_path)
            result = export_drawio(content, args.output, source_format="mermaid")
        elif args.command == "xml":
            result = open_xml(args.content, lightbox=lightbox, dark=dark)
        elif args.command == "mermaid":
            result = open_mermaid(args.content, lightbox=lightbox, dark=dark)
        elif args.command == "csv":
            result = open_csv(args.content, lightbox=lightbox, dark=dark)
        elif args.command == "xml-file":
            content = read_file_content(args.file_path)
            result = open_xml(content, lightbox=lightbox, dark=dark)
        elif args.command == "mermaid-file":
            content = read_file_content(args.file_path)
            result = open_mermaid(content, lightbox=lightbox, dark=dark)
        elif args.command == "csv-file":
            content = read_file_content(args.file_path)
            result = open_csv(content, lightbox=lightbox, dark=dark)
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
