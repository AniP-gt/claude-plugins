# omo upstream 5.1.32 照合

## 結果

`oh-my-openagent`の`dev`を`git pull --ff-only`で更新した。前回照合の`7b44ad22b02d2f3f55769406c553210ed42157df`（5.1.30）から、`0c6b9997a11af1485daa3888c2143bde8e5a572a`（5.1.32）まで117ファイルを確認した。

Claude Codeへ移植する新しい指示の差分はなく、omo-orchestratorは1.28.0を維持する。プラグイン配下の変更はないため、バージョン更新は行わない。既存の1.28.0コミット`bba80af`と今回の照合記録をpush対象とする。

## 確認した変更

- Senpi 2026.10.12への更新。終了した端末の保持メモリー削減、compaction後のcontext利用、provider単位のquota fallback、検索・RPC・cache prewarmの変更。Claude Codeの実行基盤を提供する本プラグインの機能ではなく、同じ挙動をプロンプトで保証することはできない。
- Desktop/headlessの既定model profileをDaily · Normalへ変更。Claude版のmodel選択をこのruntime固有profileへ置き換えない。
- OpenCode session managerのlegacy storage fallbackとエラー表示、読み取り不能sessionのskip。Claude版はOpenCode SDKやsession managerを同梱しない。
- macOS notarizationの伝播待ちとmusl smokeの終了判定・コンテナー後片付け。対応するrelease pipelineはClaude版に存在しない。
- CHANGELOGで補足されたmemory、ulwキーワード、環境変数テストの項目は、本文コードの新規移植対象として扱わない。今回の差分では対応するportable prompt/skill本文の変更はない。

`git diff --name-only 7b44ad22b..HEAD`で、以下の移植対象ディレクトリーの差分が0件であることを確認した。

- `packages/prompts-core/`
- `packages/shared-skills/`
- `packages/skills-loader-core/src/features/builtin-skills/`
- `packages/omo-senpi/skills/`
- `packages/omo-codex/plugin/components/rules/bundled-rules/`

## 検証

- `claude plugin validate ./omo-orchestrator`: 成功。
- `claude plugin validate .`: 成功。既存の`metadata.homepage` unknown-field警告1件。
- `node --test omo-orchestrator/hooks/pasted.test.mjs omo-orchestrator/hooks/review-gate.test.mjs omo-orchestrator/scripts/impact.test.mjs`: 27件成功、失敗0件。
- pluginとmarketplaceのversionは1.28.0で一致。descriptionは両方148文字。
- `git diff --check`: 成功。

独立したシナリオ評価は[evaluation.md](evaluation.md)に記録する。今回の評価は指示に従った模擬実行であり、実際の並列開発やHTTP serverの起動・停止を実測したものではない。
