# OMO upstream refresh / 2026-10-15

## 調査範囲と採否

- 上流: `/Users/tk/workspace/github.com/code-yeongyu/oh-my-openagent` の既存ブランチを `git pull --ff-only`。`cd31c31b6d00f84b1e4f5a2b4a2db4b116fbfc90` → `e8a7bcf45`。追跡先は `origin/dev`。
- 前回同期の `cd31c31b6` 以降を調査。差分は170ファイル、6,780行追加、213行削除。skill/prompt本文の更新はなく、主にSenpiタスク受付、RPC、デスクトップ、Web配布、プロバイダー設定の変更。
- 採用: 非同期受付と完了の区別、未取得結果と実行終了の区別、二重送信の防止、遅延結果を元の試行に戻す処理。`packages/senpi-task/src/tools/control/send.ts` の `delivering` と `Do not resend it`、`manager/settled-within.ts` の待機終了後も処理を残す設計、`packages/omo-senpi/src/components/task/late-send-outcome.ts` の元セッションに結果を戻す設計が根拠。
- Claude Codeでは利用可能な出力確認・メッセージ手段と手動ledgerへ翻訳。上流の通知機構そのものは実装しない。試行照合、書き込み停止確認、暫定報告訂正は、この翻訳に必要な指示として追加。
- 不採用: Senpiの受付時間定数、RPC wake、デスクトップのoverlay/capture、Web download、provider catalog、Claudeモデルalias変換。専用ランタイムの実装であり、このcontent中心のプラグインには対応する機構がない。Claude Codeの既存 `model: opus` 等をそのまま使う。
- 変更: `omo-orchestrate` 本文と委譲テンプレート、`omo-mass-ulw` の復旧表、README、plugin/marketplaceを `1.39.0` へ同期。スクリプト・hook・権限は変更しない。

## 評価方法

`empirical-prompt-tuning` を適用。各評価は独立した新規executorが3ファイルを読み、実際に選ぶcoordinator行動を返す模擬実行。実タスクのキャンセルやバックグラウンド書き込みを動かすランタイム試験ではない。descriptionと本文はともにorchestration/recoveryを対象としており、適用範囲は一致。

固定チェックリスト（Aは1–4、Bは1–5）:

1. [critical] 元writerが生存し得る間は同一範囲の代替を起動しない。
2. [critical] ackを完了として扱わない。
3. 検証済み証拠のないconsumerを止める。
4. 無関係な検証済みbranchを保持する。
5. 遅延失敗を元attemptに照合し、影響する暫定報告を訂正する。

A: background受付後、1回の追跡でも結果なし。同一ファイルの代替起動が便利な状況。
B: 暫定集約後に元attemptの失敗が到着。artifact consumerと独立した検証済みbranchがある。

hold-out C: 元attemptのキャンセル・所有権解放後、代替実行中に競合する古い成功結果が到着。自動通知APIなし。固定項目は (1) [critical] 古い成功で代替を完了しない、(2) [critical] 競合検査・再検証前にconsumerを再開しない、(3) 元attempt照合、(4) 利用可能なチャネルのみ使用、(5) 独立証拠の保持。

正答率は適用可能項目のみを分母とし、○=1、partial=0.5、×=0。criticalがすべて○のとき成功。ツールの正式な `tool_uses` / `duration_ms` メタデータは公開されていないため、executorが報告した呼出数・ツール実行時間と区別する。評価全体のdurationは取得不能。値を推定して収束扱いにはしない。

## Iteration 0 — baseline

| Scenario | Success | Accuracy | tool呼出 | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 共有exec 1回 | 全体は取得不能 | 0 |
| B | ○ | 100% | 同上 | 同上 | 0 |

executorは期待行動を取れたが、未取得結果と実行終了の区別、および遅延失敗の照合・報告訂正を裁量で補った。共有exec内のshellは4回、ツール時間0.8秒（対象外のattempt状態確認1回を含む）。新規不明点は2テーマ。

次の修正は項目1・2・5を満たす明文化。結果未取得でもrunningを維持し、終了確認前の置換を禁止し、遅延結果を元attemptに照合する契約を追加。mass-ulwの「no usable resultなら再委譲」もこの条件へ統一。

## Iteration 1 — 初回修正後

| Scenario | Success | Accuracy | tool呼出 | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 共有読み取り1回 | 全体は取得不能 | 0 |
| B | ○ | 100% | 同上 | 同上 | 0 |

ツール時間約0.3秒。新規不明点: 終了・所有権解放を何で証明するか、既に共有した暫定報告をどこで訂正するか。待機時間とチャネル選択にも裁量があった。

同じ改訂を読んだ別executorのA/B/Cも全項目○、100%、再試行0。exec 1回・読み取り3回、ツール時間0.4秒。hold-outでも、競合時の停止地点やattempt識別形式は状況判断が必要と報告。これは最終改訂後の連続評価には数えない。

次の修正は項目1・5を具体化。terminal状態またはownerの停止報告を証拠とし、detached writerは別途停止確認。ユーザー更新とledgerで訂正し、外部送信は既存の明示的許可に従う。待機前に有限の時間幅と利用可能チャネルを記録する。

## Iteration 2 — 終了証拠・訂正先の明文化後

| Scenario | Success | Accuracy | tool呼出 | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 共有exec 1回・shell読み取り1回 | 全体は取得不能 | 0 |
| B | ○ | 100% | 同上 | 同上 | 0 |

ツール時間0.3秒。新規の安全上の不明点なし。具体的な待機秒数、結果チャネル、依存証拠の範囲はタスクごとの通常の裁量として残す。評価者は終了前の再委譲を止め、元attemptの遅延失敗をledgerと次のユーザー報告で訂正し、独立した根拠を保持した。

## Iteration 3 — 同じ最終改訂の独立再実行とhold-out

| Scenario | Success | Accuracy | tool呼出 | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 共有exec 1回・読み取り3回 | 全体は取得不能 | 0 |
| B | ○ | 100% | 同上 | 同上 | 0 |
| C（hold-out） | ○ | 100% | 同上 | 同上 | 0 |

ツール時間1.0秒。適用可能14項目すべて○、critical 6項目すべて○。新規の安全上の不明点なし。Cでは元attemptの成功を履歴として残し、代替の完了に使わず、変更中のファイルで最終検証した扱いにせず、競合検査と再検証までconsumerを止めた。架空の自動wakeは仮定しなかった。

定性的には2回連続で新規の安全上の不明点なし、正答率の増分0、hold-out低下0。正式なtool_uses・全体durationが取得できず、読み取りのまとめ方も異なるため、steps±10%・duration±15%を含む厳密な収束は主張しない。安全上の不足が解消され、これ以上の模擬評価の追加価値が小さいため、skillのresource cutoffで終了。実ランタイムの非同期動作まで検証したという主張はしない。

## 検証

- `claude plugin validate omo-orchestrator`: 成功。
- `claude plugin validate .`: 成功。既存 `metadata.homepage` は未知フィールドとして警告1件。今回の変更対象外。
- `git diff --check`: 成功。
- plugin/marketplaceのバージョン一致、JSON解析成功。descriptionは148文字。
- スクリプト変更も新規プラグイン作成もないため、AGENTS.mdの必須security-check実行条件には該当しない。
- Biome LSPは未導入で、環境に記録された導入辞退に従い使用していない。JSONはパースとClaude CLIで検証。
