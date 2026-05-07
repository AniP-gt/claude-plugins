# cocoindex-setup

`~/.config/cocoindex/` の `secrets.env` / `config.toml` を所有・auto-provision する共通基盤プラグイン。`compass` / `episodic` など下流プラグインの secrets hub として機能する。

## インストール

```text
/plugin install pgvector-stack@hidetsugu-miya
/plugin install cocoindex-setup@hidetsugu-miya
```

## auto-provision

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_config.sh
```

不足する `secrets.env` / `config.toml` だけテンプレートから配置する（既存は上書きしない）。配置後 `~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。

## 共通 secrets hub としての役割

下流プラグインの secrets 解決順:

1. `~/.config/<plugin>/secrets.env`（プラグイン専用、最優先）
2. `~/.config/cocoindex/secrets.env`（このプラグインが所有、fallback）

詳細は `skills/cocoindex-setup/SKILL.md` を参照。
