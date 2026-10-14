# omo-orchestrator upstream refresh 2026-10-14

## 更新元と範囲

`/Users/tk/workspace/github.com/code-yeongyu/oh-my-openagent` の clean な `dev` で `git pull --ff-only` を実行し、`0c6b9997a` から `cd31c31b6d00f84b1e4f5a2b4a2db4b116fbfc90`（5.1.33）へ更新した。81 commits、153 files の差分を確認した。claude-plugins 側も開始時は clean な `main` だった。

変更された skill は mass-ulw、ulw-loop、ulw-research、ulw-execute。移植可能な指示と、Senpi/OpenCode/Codex の runtime・パッケージ変更を分けて判断した。

## 取り込み判断

| 上流の変更 | Claude Code 側の判断 |
|---|---|
| phase と harvest/expand/verify/reduce stage の区別、既知の chain を開始前に定義 | omo-mass-ulw 本文と planning に反映。Agent の ready set 単位で dispatch する既存方式を維持 |
| dependsOn は順序のみ、handoff file でデータを渡す | 絶対パスを producer/consumer の両 prompt に記載。ファイルの存在・入力 identity・検証証拠を確認。既存の reply-based handoff も維持 |
| mass harvest の batch、cluster reducer、容量を超える run の分割 | bounded report と batch chain を採用。Claude Code の slot 数は dispatch batch の上限として扱い、Senpi の具体的な node/run 数や設定名は移植しない |
| research node 自身の handoff だけは書き込みを許可 | mass-ulw の producer は自身の report のみ所有、中央 journal は coordinator 所有と明記。read-only omo-ultraresearch の契約は広げない |
| 発見した非阻害作業は現在の checkpoint 後、acceptance blocker は checkpoint 内 | omo-ulw-execute に反映。plan/todo 登録と Ralph の既存 count/cap/history を維持 |
| ulw-execute の task-local attempt/signature/time limit、blocked checkbox、harness repair exception | 今回は移植しない。既存 Ralph の共通 iteration cap・blocker history・唯一の controller と衝突し、blocked を completion に含めるには他の plan/review 契約も変更が必要 |
| run settle/paused wake、retry/amend runtime、Senpi task への直接 delegation | Claude Code は Agent 結果で進行するため移植しない。自動 wake/resume を実装済みと説明しない |
| RPC heartbeat、daemon shutdown、queued resume、native retired-command、package version/lock 更新 | 対応する runtime を同梱していないため対象外 |

## 検証

- `claude plugin validate ./omo-orchestrator`: PASS。
- `claude plugin validate .`: PASS。既存の `metadata.homepage` が unknown field という warning は残る。
- `node --test omo-orchestrator/hooks/pasted.test.mjs omo-orchestrator/hooks/review-gate.test.mjs omo-orchestrator/scripts/impact.test.mjs`: 27 tests PASS、0 FAIL。
- `git diff --check`: PASS。
- plugin/marketplace version を `1.32.0` に同期。description は双方148文字、変更なし。変更した skill の相対リンク解決を確認。
- script/hook の変更とプラグイン新設はないため、AGENTS.md の security-check agent 必須条件は該当しない。
- Biome LSP は未導入で、既存の導入辞退に従いインストールしていない。JSON は manifest validation で確認した。

empirical-prompt-tuning の実行記録は [evaluation.md](evaluation.md)。独立した executor がシナリオに従って graph/dispatch/ledger を出力する評価であり、実際の Claude Code Workflow や1200件の harvest を走らせたという記録ではない。
