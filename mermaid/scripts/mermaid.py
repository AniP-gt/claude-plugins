#!/usr/bin/env python3
"""
Mermaid.js CLI Wrapper

@mermaid-js/mermaid-cli (mmdc) を使用してMermaid構文からPNG/SVG画像を生成するラッパースクリプト

Usage:
    mermaid render <content> -o <path>
    mermaid render-file <file_path> -o <path>

Examples:
    # Mermaid構文からPNG画像を生成
    mermaid render "graph TD; A-->B; B-->C;" -o output.png

    # Mermaidファイルから画像を生成
    mermaid render-file diagram.mmd -o output.svg
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def render_mermaid(content, output_path, fmt="png"):
    """Mermaid構文をPNG/SVGに変換して出力"""
    print(f"Rendering Mermaid to {fmt.upper()}: {output_path}\n")
    print(f"Input:\n{content}\n")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli@11.12.0", "-i", tmp_path, "-o", output_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return {"error": True, "message": result.stderr.strip() or "mmdc failed"}

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            return {"output": output_path, "format": fmt, "size_bytes": size}
        else:
            return {"error": True, "message": f"Output file not created: {output_path}"}

    except subprocess.TimeoutExpired:
        return {"error": True, "message": "mmdc timeout (120s)"}
    except FileNotFoundError:
        return {"error": True, "message": "npx not found. Please install Node.js"}
    except Exception as e:
        return {"error": True, "message": str(e)}
    finally:
        os.unlink(tmp_path)


def read_file_content(file_path):
    """ファイルからコンテンツを読み込む"""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Mermaid.js CLI Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # render コマンド
    render_parser = subparsers.add_parser("render", help="Render Mermaid to PNG/SVG image")
    render_parser.add_argument("content", type=str, help="Mermaid.js syntax")
    render_parser.add_argument("-o", "--output", type=str, required=True, help="Output file path (.png or .svg)")

    # render-file コマンド
    render_file_parser = subparsers.add_parser("render-file", help="Render Mermaid file to PNG/SVG image")
    render_file_parser.add_argument("file_path", type=str, help="Path to Mermaid file")
    render_file_parser.add_argument("-o", "--output", type=str, required=True, help="Output file path (.png or .svg)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "render":
            fmt = "svg" if args.output.endswith(".svg") else "png"
            result = render_mermaid(args.content, args.output, fmt=fmt)
        elif args.command == "render-file":
            content = read_file_content(args.file_path)
            fmt = "svg" if args.output.endswith(".svg") else "png"
            result = render_mermaid(content, args.output, fmt=fmt)
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
