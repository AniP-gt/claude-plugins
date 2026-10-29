# OMO upstream refresh 2026-10-29

## 上流調査と配置

上流 `/Users/tk/workspace/github.com/code-yeongyu/oh-my-openagent` の `dev` で `git pull --ff-only` を実行。`ad3cb2e28d` から `8c12be2b31b33aa49f8bce9822ac951fc242b073` に更新し、作業ツリーはクリーン。pull後のログ表示用変数にzshの読み取り専用変数名を使って失敗したが、pull自体は完了しており、HEADとログで確認した。

差分295ファイルをディレクトリ単位で分類。共有skillsの7ファイルはfrontend本文・design参照・配布manifest関連。frontendの履歴と差分、grounding全文、design-system-architecture差分を確認した。全ランタイムの監査・移植は行っていない。

| 上流の改善 | 判断と配置先 |
|---|---|
| grounding: source→owned surface→fix→planned proof、未読を既読扱いにしない | 既存 `omo-frontend/SKILL.md` Phase 1 と直接参照 `implementer-brief.md` に配置 |
| state-stable controls: 状態間のbox維持と実測 | 既存 `references/layout-and-motion.md` のmechanics、briefの実装契約、本文のQA引継ぎに役割を分けて配置 |
| 新規screenのcaptureはfirst draft後 | 既存のbefore capture規則を維持し、新規では不存在記録とfirst draft検証を明記 |
| 新しい色・surface・shadcnの一律規則、全ガイドライン読了、大量PR実行 | 既存のproject system・表現幅・権限境界と実行規模を維持するため移植しない |
| WCAG項目別の新しい合格表・例外、upstream check-draft-guard | 規格監査と同梱実装がないまま検証済みと誤認させない。既存quality floorとvisual QAを維持 |
| desktop/keychain/trust/telemetry、OpenCode/Codex/Senpi固有実装、テスト基盤 | Claude Codeのportable prompt変更の対象外 |

開始時に追加の訂正・retrospective lessonなし。上流の手順は既存skillへ配置し、新規hook・skill・agentは作らない。評価で見つかった「空projectに既存部品5〜10個の読了を要求する矛盾」は同じ事前調査手順内で修正した。nested project instructionsの発見、存在しないmanifestと提案する構成の区別を明記。既存のno-auto-install、外部テキストはdata、reference fidelity、最終QA APPROVEの境界は維持する。

## Iteration 0

変更前に [checklist.md](checklist.md) の3ケース・各4要件を固定。descriptionが示すUI/design-system、source/reuseの範囲と本文は整合。read-onlyの新規executorが具体的なbrief/handoffを作成した。

Aは二つのemail、日本語エラー、slot予約と4状態の矩形比較を提案。Bは不存在を明記し、DESIGN.md/index.html/styles.cssを提案と明示。Cは指定画像を契約とし、browser不在でINCONCLUSIVE、実画面QAをcallerへ返した。返された出力を固定4要件へ採点するとA/B/Cとも4/4・100%、成功○。ただしexecutor自身はsource→owner→proofと状態寸法維持を「裁量による補完」と報告し、現行指示だけの充足はpartial/×と評価した。この二つの採点を混同しない。

新規曖昧性: nested instructionの探索、制約ごとのproof、loading時の寸法安定、greenfieldの不存在処理。修正対象の要件は2と3、要件1/4の証拠境界を維持する。小変更での既存component layer不在時の質問規則は今回の対象外。retry 0。自己申告はfunctions.exec 1回、内部exec_command 1回。

## Iteration 1以降

変更は「実装前に制約と証明を具体化し、状態変化をその証明へ含める」という1テーマ。本文122→122行（予算500未満）、brief84→90行、layout-and-motion89→91行。直接参照はいずれも100行未満。description変更なし。

Iteration 1（新規executor、変更後）: A/B/Cは各4/4・100%、成功○、retry 0。出所とproof、greenfield不存在、slotと矩形比較が明示指示に変わったと報告した。Aは別々のemailと日本語エラーを維持し、footer上端とcontrol矩形を比較する計画。Bは不存在をシナリオ条件と実確認で区別し、HTML/CSS案を未確定と明記、showcase→first draftへ引継ぎ。Cは画像とbefore captureを混同せず、browser不在でINCONCLUSIVEとした。保存予定の画像/JSONを取得済みと主張しなかった。自己申告: functions.exec 2回、読取command 3回、親への通知2回。

新規の指摘: 矩形の等値比較に許容差が未定義（executorは同一環境での完全一致を計画）、厳密画像とaccessibilityが衝突する際の運用順序、入力内容が未確定なBの暫定brief境界。前者は現在の「same width and height」をそのまま厳密比較する計画で要件を満たす。後二者は既存のユーザー指定優先・未解決trade-offのescalationと、シナリオ入力不足に関わる。今回のproof/slot契約の失敗はなく、無関係な方針変更を加えない。

Iteration 2（本文変更なし、さらに新規executor）: A/B/Cは各4/4・100%、成功○、retry 0。Aは二つのemail・日本語errorを維持、label/spinner予約とfooter比較を計画。Bは実在未確認の提案ファイルと既知の不存在を分け、設定内容を捏造しない。Cは厳密画像とfocus衝突を独断で解消せず、browserなしではINCONCLUSIVE。自己申告tool call 1回。追加参照は未読と明記し、完全なfrontend実行を主張しなかった。

初見hold-outも4/4・100%、成功○。送信前previewと長い宛先一覧を維持。nested rule→modal→送信前previewの操作検証を対応づけた。controlはlocale/widthごとに同寸法を比較し、一覧本文は自然な伸長とscrollを許容。全証拠をplanned/openとし、未実施QAを完了にしなかった。直近平均からの精度低下0ポイント。

Iteration 2の新規指摘は既存motion規則の「transform/opacity/filterのみ」と「colorのshort easing」の不一致。今回の差分で導入していない既存の別テーマとして記録し、対象を広げない。矩形許容差は前回と同じ。指摘ゼロが2回連続という正式収束条件は未達。固定要件全通過・hold-out通過・限定変更の費用対効果に基づくresource cutoffで出荷し、完全な収束は主張しない。

| Iteration / ケース | 成功 | 精度 | steps（参考自己申告） | duration | retries |
|---|---|---|---|---|---|
| 0 / A・B・C（各） | ○ | 各100% | 全ケース合計exec 1回、command 1回 | 未計測 | 0 |
| 1 / A・B・C（各） | ○ | 各100% | 全ケース合計exec 2回、読取command 3回 | 未計測 | 0 |
| 2 / A・B・C（各） | ○ | 各100% | hold-out込みtool 1回 | 未計測 | 0 |
| 2 / hold-out | ○ | 100% | 上記に含む | 未計測 | 0 |

次の修正提案は既存motion規則の整合性確認であり、今回の出荷条件には含めない。

測定制約: このdispatch surfaceはTaskの `usage.tool_uses` / `duration_ms` を返さない。自己申告tool数は参考値とし、正確な所要時間や数値的収束を捏造しない。チェックリスト提示型のsimulationであり、盲検精度や実UIの成功率ではない。

## 検証

- 変更前後とも `node --test omo-orchestrator/hooks/*.test.mjs omo-orchestrator/scripts/*.test.mjs`: 81 pass、0 fail。
- `claude plugin validate ./omo-orchestrator --json`: success=true、manifest errors/warningsなし。
- `claude plugin validate ./.claude-plugin/marketplace.json --json`: success=true。既存 `metadata.homepage` はunknown fieldのwarning。今回変更しない。
- directory申請向けのLICENSE/icon不足は既存advice。今回はdirectory申請をしない。
- `git diff --check` 通過。plugin/marketplace 2.2.0、description各148文字。
- scripts/hooksの変更なし。新しいruntime testは追加せず、promptの実行評価で変更契約を確認する。

独立security-checkが `.claude/agents/security-check.md` の5カテゴリを実行。scripts/hooksは14ファイル（13 mjs、1 json）、py/shなし。拡張子を限定せずnpx、SQL埋込み、サニタイズ変数混在、認証情報リテラル、固定tmpを検索してすべて一致0。HIGH 0 / MEDIUM 0 / LOW 0。差分にallowed-tools変更、権限拡大、外部データ境界・no-auto-install緩和なし。visual QAの既存指示と整合。詳細証跡はgit外 `.omo/evidence/2026-10-29-omo-frontend-security-check/report.md` に保持。

## 公開権限と開始状態

ユーザーはこのセッションのcommit・pushとClaude plugin更新を明示許可。skill既定の「pushしない」より今回の指示を優先。claude-plugins開始時はmain/bf05246、クリーンでorigin/mainと一致。導入済みはuser 2.1.0、local 2.0.0（folderVersion 2.1.0）。AniP-gt marketplaceは当該worktreeを参照するdirectory source。

## 公開・導入結果

- `c9ed3df31e191587deb5682c65496986989f4800`: `feat(omo-orchestrator): UI制約の検証計画と操作状態の寸法維持を明確にする (2.2.0)` をコミット。
- `git push origin main` 成功、`bf05246..c9ed3df main -> main`。`git ls-remote origin refs/heads/main` でも一致を確認。
- `claude plugin marketplace update AniP-gt` 成功。
- `claude plugin update omo-orchestrator@AniP-gt --scope user --json`: outcome=ok、up_to_date、2.2.0。directory sourceを読むため、更新コマンド時点では既に最新版として返った。
- 同コマンド `--scope local`: outcome=ok、updated、2.0.0→2.2.0。
- `claude plugin list --json`: user/local両scopeでversion/folderVersionとも2.2.0。更新後のtracked作業ツリーはクリーン。
- CLIの案内どおり、Claude Code再起動で実行中セッションへ適用する。ユーザーの実行中セッションは終了していない。

この公開結果追記はdocsのみの別commitとして通常pushする。plugin配下の追加変更はないためバージョン再更新は不要。
