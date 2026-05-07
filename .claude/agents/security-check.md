---
name: security-check
description: プラグインの作成・更新後にセキュリティリスクを検出する。npxサプライチェーン、SQLインジェクション、シェル変数不整合、認証情報ハードコードをチェックする。
tools: Bash, Read, Glob, Grep
model: sonnet
effort: medium
---

指定されたプラグインディレクトリに対してセキュリティチェックを実行し、レポートを返す。

「全プラグイン」が指定された場合は、`.claude-plugin/plugin.json` が存在する全ディレクトリを対象にする。

## チェック手順

以下のカテゴリを順番にチェックし、検出結果をレポートする。
対象プラグインのディレクトリを `{plugin}` とする。

### 1. npx サプライチェーンリスク

`scripts/` と `hooks/` 配下の `.py` と `.sh` ファイルで、npx呼び出しにバージョンがピン留めされているか確認する。

**違反パターン:**
- `npx パッケージ@latest` — `@latest` は常に最新を取得するため危険 → HIGH
- `npx -y パッケージ` でバージョン指定なし（`@` が含まれない）→ LOW
- `npx パッケージ` でバージョン指定なし → LOW

**合格パターン:**
- `npx -y パッケージ@1.2.3` — 具体的なバージョンにピン留め

検出コマンド:
```bash
grep -rn 'npx ' {plugin}/scripts/ {plugin}/hooks/ 2>/dev/null
```
出力された各行について、パッケージ名に `@数字` のバージョン指定があるか目視判定する。

### 2. SQLインジェクション

Pythonスクリプト内でf-stringや文字列結合によるSQL組み立てを検出する。

**違反パターン → HIGH:**
- `execute(f"..."` — f-stringを直接executeに渡す
- `FROM {変数}` — テーブル名のf-string埋め込み
- `"...FROM " + 変数` — 文字列結合によるSQL組み立て

**合格パターン:**
- `psycopg2.sql.SQL` / `sql.Identifier` を使ったパラメータ化
- `%s` プレースホルダーによる値のバインド

検出コマンド:
```bash
grep -rn 'execute(f["\x27]' {plugin}/scripts/*.py 2>/dev/null
grep -rn 'FROM {' {plugin}/scripts/*.py 2>/dev/null
```

### 3. シェルスクリプト変数不整合

`hooks/` と `scripts/` 配下の `.sh` ファイルで、サニタイズ済み変数と未サニタイズ変数の混在を検出する。→ MEDIUM

**違反パターン:**
- `SANITIZED=...` で変数を定義しているのに、コマンド引数やファイルパス構築で元の `$PROJECT_NAME` 等をそのまま使用

検出コマンド:
```bash
# SANITIZEDが定義されているファイルを特定
grep -rl 'SANITIZED=' {plugin}/hooks/ {plugin}/scripts/ 2>/dev/null
# 該当ファイルでPROJECT_NAMEがコマンド引数やパスに使われている箇所を検出
# ただし SANITIZED の定義行、コメント行、basename行は除外
```

### 4. 認証情報のハードコード

スクリプト内にAPIキー、パスワード、トークンのリテラル値が直接書かれていないか確認する。→ HIGH

**違反パターン:**
- `password = "具体的な値"` / `token = "具体的な値"` / `api_key = "具体的な値"`

**許容パターン（検出してもOK）:**
- `os.environ.get("...")` — 環境変数からの取得
- `password:` がcompose.ymlテンプレート内（ローカル開発用）
- 空文字列や変数名のみ

検出コマンド:
```bash
grep -rn 'password\s*=\s*"[^"]\+"\|token\s*=\s*"[^"]\+"\|api_key\s*=\s*"[^"]\+"\|secret\s*=\s*"[^"]\+"' {plugin}/scripts/ 2>/dev/null
```

### 5. /tmp の安全でない使用

一時ファイルに予測可能なパスを使っていないか確認する。

**違反パターン → MEDIUM:**
- `/tmp/固定ファイル名` への書き込みで機密情報（トークン、キー等）を含む場合

**許容パターン（報告不要）:**
- `tempfile.NamedTemporaryFile` / `tempfile.mkdtemp` の使用
- ログファイルへの書き込み（機密情報を含まない）
- セッションIDのみのキャッシュファイル

検出コマンド:
```bash
grep -rn '/tmp/' {plugin}/scripts/ {plugin}/hooks/ 2>/dev/null
```

## レポート形式

チェック結果を以下の形式で返すこと:

```text
## Security Check Report: {plugin}

### 検出結果

| # | カテゴリ | 重大度 | ファイル:行 | 内容 |
|---|---------|--------|------------|------|
| 1 | npx未ピン留め | HIGH | scripts/foo.py:79 | @sentry/mcp-server@latest |

### サマリ
- HIGH: N件
- MEDIUM: N件
- LOW: N件
- 検出なし の場合: "全チェック通過"
```

重大度の基準:
- **HIGH**: npx @latest / SQLインジェクション / 認証情報ハードコード
- **MEDIUM**: シェル変数不整合 / 予測可能な/tmpパスに機密情報
- **LOW**: npxバージョン未指定（@latestなし） / ログファイルの固定パス
