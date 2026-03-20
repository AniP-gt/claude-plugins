---
name: cocoindex-setup
description: CocoIndexの環境セットアップ手順。初回設定・DB起動・設定ファイルの管理方法。
user-invocable: false
---

# CocoIndex セットアップ

## 共通情報

- **スクリプト**: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- **ユーザー設定**: `~/.config/cocoindex/.env`
- **DB**: OrbStack VM内の `cocoindex` コンテナ（ポート15432、`restart: unless-stopped`で自動起動）

## 初回セットアップ

`~/.config/cocoindex/.env` は、セッション開始時およびヘルスチェック実行時にテンプレートから自動コピーされる。

手動セットアップが必要な場合:

```bash
mkdir -p ~/.config/cocoindex && cp ${CLAUDE_PLUGIN_ROOT}/templates/.env.example ~/.config/cocoindex/.env
```

`~/.config/cocoindex/.env` の `VOYAGE_API_KEY` を設定すること。

## DB起動（VM内でのみ実行）

```bash
cd ~/.config/cocoindex && docker compose up -d
```

`compose.yml` はVM側（`/root/.config/cocoindex/`）にのみ配置。Mac側には配置しない。

## テーブル名の規則

テーブル名には `hostname` プレフィックスが付く:
- VM: `codeindex_dev_<project>__code_chunks`
- Mac: `codeindex_macbookpro_local_<project>__code_chunks`

これにより同一DBをMac/VMで共有しても競合しない。

## インデックス再構築

同じ構築コマンドを再実行すればインデックスが更新される。
