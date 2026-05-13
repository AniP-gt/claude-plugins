# Claude API から episodic-search を呼び出す

`episodic-search` skill は副作用なし・stdin/stdout 完結なので、Claude API の Tool Use として登録するだけで外部アプリから利用できる。

## 前提

- skill が配置されたホストにリモートシェル経由でアクセスできる、または同一ホストで Claude アプリを動かしている
- `episodic` プラグインがインストール済み（`/plugin install episodic@hidetsugu-miya`）
- PostgreSQL（cocoindex バックエンド）が起動している
- 直近セッションの Stop hook（debounce 経由）が走り、memories インデックスが構築されている

## パス解決

Claude Code 内（hook / Bash ツール経由）でも外部アプリからでも、runtime の絶対パスを指定する:

```bash
~/.config/episodic/codex-hook-runtime/scripts/search/search.sh
```

`episodic/scripts/install-bin.sh` が plugin source を `~/.config/episodic/codex-hook-runtime/` にミラーコピーするため、Claude plugin cache のバージョン付きパスには依存しない。

## 最小実装パターン: Bash 実行可能なツールから直接叩く

Claude API の Tool Use で「shell コマンド実行」ツールを定義し、`search.sh` を呼ぶ。

```python
import anthropic
import os
import subprocess
import json

client = anthropic.Anthropic()

tools = [
    {
        "name": "search_memory",
        "description": (
            "過去の Claude Code セッション要約（kind: session）・URL アーカイブ（kind: web）・"
            "議事録（kind: minutes）・統合 Wiki ページをベクトル検索する。"
            "自然言語クエリで関連する作業記録を発見できる。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "自然言語クエリ"},
                "top": {"type": "integer", "default": 10},
                "scope": {
                    "type": "string",
                    "enum": ["session", "web", "minutes", "wiki", "all"],
                    "default": "all",
                },
                "include_superseded": {"type": "boolean", "default": False},
            },
            "required": ["query"],
        },
    }
]


SEARCH_SH = os.path.expanduser(
    "~/.config/episodic/codex-hook-runtime/scripts/search/search.sh"
)


def execute_tool(name: str, args: dict) -> str:
    if name != "search_memory":
        raise ValueError(f"unknown tool: {name}")
    cmd = [
        SEARCH_SH,
        args["query"],
        "--top", str(args.get("top", 10)),
        "--scope", args.get("scope", "all"),
        "--format", "json",
    ]
    if args.get("include_superseded"):
        cmd.append("--include-superseded")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return json.dumps({"error": result.stderr})
    return result.stdout


# 通常の Tool Use ループで使う
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4096,
    tools=tools,
    messages=[
        {"role": "user", "content": "過去のセッションで cocoindex の設定を変更したものを探して"},
    ],
)
# ... tool_use ブロックを検出したら execute_tool で実行し tool_result で返す ...
```

## リモートホスト経由

memories が別ホストにある場合、SSH 経由で叩く:

```python
import subprocess

def execute_tool_remote(args: dict) -> str:
    # リモートホスト側で展開させたいので "~/" のままシェルへ渡す（ssh 越しに展開される）
    cmd = [
        "ssh", "user@memories-host",
        "~/.config/episodic/codex-hook-runtime/scripts/search/search.sh",
        args["query"],
        "--format", "json",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
```

## レスポンス例（JSON）

```json
[
  {
    "score": 0.842,
    "path": "/Volumes/memory/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md",
    "snippet": "...（本文冒頭のスニペット）...",
    "frontmatter": {
      "kind": "session",
      "title": "<タイトル>",
      "status": "active",
      "tags": "<tag1>, <tag2>",
      "session_id": "<UUID>",
      "source_jsonl": "~/.claude/projects/<encoded-cwd>/<UUID>.jsonl"
    }
  }
]
```

## エラーハンドリング

- exit code 2: 引数不正
- exit code 3: cocoindex プラグインまたは memories ディレクトリが見つからない
- 非ゼロ + stderr: cocoindex 内部エラー（PostgreSQL 接続失敗など）

stderr を捕捉してアプリ側でリトライ判定する。

## キャッシュ戦略

`search.sh` 自体はキャッシュを持たない。Claude API アプリ側で同一クエリの結果を短時間（例: 60 秒）キャッシュすると、Tool Use ループ内での重複検索を抑制できる。
