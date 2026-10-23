# OMO upstream refresh 1.57.0

開始日: 2026-10-22。上流 `oh-my-openagent` を `git pull --ff-only` で
`c00a05835a6bb11944976263b4e945972adce538` から
`16bf9418fb0f78eb96d3f7323f0c2091df163397` へ更新した。
claude-plugins は開始時に clean、origin/main と同期済み。

## 反映先と採否

- 装飾の判定範囲拡張 → 既存 skill → `omo-frontend/SKILL.md` と `references/aesthetics.md`。
  角形ボックスの片側バー、丸角カードの2px以上のアクセント枠、アクセント下線を対象化。
  focus-visible、フォーム検証、表罫線、指定参照の例外を維持する。
  HTML/CSS/SVG のレポート・図・スライド・印刷にも適用する。
- 短縮調査でも本文を届ける手順 → 既存 skill → `omo-ultraresearch/SKILL.md`。
  インライン表示は書込み不要の機能がある場合に限定し、なければチャット本文を返す。
- 視覚的再現の比較 → 同じ調査 skill の出力契約。
  同じ時刻・視点の実参照と出力を比較し、動きには再生可能な映像を使う。
  取得・修正が書込みを要する場合は具体的に引き継ぎ、未比較を未検証とする。

上流の根拠: `c5469a93bc`、`9611b21398`（frontend）、
`fbca231540`、`567e7a0e02`、`a5b34b5fc2`、`8a06523475`、
`d27f82311a`（ulw-research と参照映像）。

上流のメモリ agreements、暗号処理、Senpi desktop、CI、インストーラーは
Claude Code の本プラグインの責務外として除外した。上流の装飾 linter や
report-tools のランタイムも導入していない。ソース監査を自動 lint 成功と呼ばない。
新規 hook・skill・agent は作成していない。

## Empirical evaluation

description と本文の対象を先に照合し、frontend の export 対象を両方に明記した。
実装や描画そのものではなく、変更した指示に従う応答を独立 executor に実行させた。
チェックリストは実行前に固定した。review skill の評価ではないため公開 checklist を使用。

固定要件: [critical] 角形バーと丸角アクセント枠の置換、[critical] focus/form/table の
例外維持、export と手動監査の扱い、[critical] 読取り専用の維持、
[critical] 比較不足を未検証とする具体的引継ぎ、短縮時にも報告本文を返すこと。

### Iteration 1

- 変更: 上記 portable contract を反映。
- シナリオA: 印刷HTML、角形の警告バー、選択カード ring-2、正当な focus/form/table。
- 出力: バーと選択リングを面色・警告ラベル・選択記号へ置換。
  focus-visible、入力検証、表罫線は保持。印刷時も文字・記号で状態を示す。
- シナリオB: 参照URLと出力静止画のみ、inline tool と書込み権限なしの短縮調査。
- 出力: fidelity/motion を UNKNOWN とする報告本文、対応時刻・視点の比較画像と
  再生可能クリップを取得する引継ぎ。自己比較での承認を拒否。
- 成功 ○、6/6、100%、再試行0。executor自己申告の内部tool数5。
- 不明点: 実ファイルなしの仕様では token 対応を保留、clip長は裁量。
  前後2秒という提案は executor の一案であり、新しい必須規則にはしていない。
- tool_uses / duration_ms の公式メタデータは取得不可。

### Iteration 2

- 差分: なし。同じ指示を新しい executor が独立実行。
- A/B の要件を5項目に束ねて採点し5/5、100%、critical 全件 ○。
  第1回と同じ6要件はすべて出力で確認できた。集計粒度の差であり閾値変更ではない。
- 再試行0。ツール出力切詰めによる再読1回。公式 tool/duration metadata は取得不可。
- 不明点: 単独成果物を visualize へ回す場合と一般アプリ調査の区別を executor が
  補足確認事項として挙げた。現行 Phase 0 は前者が Phase 1 を置換すると明記済み。
  実プロジェクト未提供のためパス・token は作らず保留した。
- B の実URL・時刻不足は想定した入力不足であり、未検証と引継ぎで扱えた。

### Hold-out

- 入力: 指定画像で必須の紫エッジと、無関係な新図の紫下線。
  書込みなしのinline表示機能、間隔差分のある既存比較ペア。
- 出力: 指定エッジを参照例外として保持、無関係な下線を置換。
  本文・比較批評を含むinline版を提案し、間隔修正と同じ表示条件での再取得を引継ぎ。
  実際には表示していないことを明示。
- 成功 ○、3/3、100%、再試行0。欠けたpath・時刻・寸法は捏造しなかった。

これはプロンプト応答評価であり、実アプリ・動画・inline表示の描画検証ではない。
executor role が要求する ULW plan や永続QA matrix はこの独立評価の前提ではなく、
その不足による role 内部の FAIL は上記応答チェックリストの判定と区別した。
タイミングメタデータがないため厳密な収束条件を達成したとは主張しない。
追加実装を伴わない今回の範囲では費用対効果による打切りとする。

## 検証

- `node --test --test-reporter=tap` で impact と全hookの5テストファイルを実行:
  74 passed、0 failed、0 skipped。
- `claude plugin validate omo-orchestrator`: Validation passed。
  既存の directory 公開用 LICENSE 不足と icon 不足の警告は残る。
- `git diff --check`: 通過。
- manifest / marketplace のバージョン一致: 1.57.0。description は各148文字。
- frontend skill 118行、aesthetics 65行、ultraresearch skill 131行。
  description は197文字 / 188文字で予算内。
- 独立 security-check: 規定5カテゴリとprompt差分を確認し HIGH 0 / MEDIUM 0 / LOW 0。
  スクリプト変更なし。危険な指示の追加なし。

push はこのセッションのユーザー明示許可に従って実行する。
