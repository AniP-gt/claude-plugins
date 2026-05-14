# 記憶レイヤーの位置付け

`episodic-recording` skill が担当する範囲を、エージェントの記憶レイヤー全体の中で位置付けるリファレンス。記憶を性質ごとに別レイヤーへ分離する設計の全体像を示す。本 skill の責務境界（何を保存し、何を保存しないか）を判断するときに参照する。

## レイヤー一覧

| レイヤー | 担当 | 用途 |
|---|---|---|
| 意味記憶 / 手続き記憶 | auto memory（`memory/MEMORY.md` 配下） | ユーザー好み・コーディング規約・繰り返し参照する事実 |
| 意思決定記録 | `adr` skill | 技術選定・アーキテクチャ判断の永続化 |
| **エピソード記憶（kind: session）** | 本 skill（自動）+ `memories/raw/session/` | 過去セッションでの作業内容・判断・残課題 |
| **エピソード記憶（kind: web）** | 本 skill（手動）+ `memories/raw/web/` | 外部 URL のスナップショット |
| **エピソード記憶（kind: minutes）** | 本 skill（手動）+ `memories/raw/minutes/` | 議事録・指示・合意ログ |
| **エピソード記憶（kind: diary）** | 本 skill（手動）+ `memories/raw/diary/` | プライベートな日記・その時の気持ち。session が意図的に除外する感情を残す唯一のレイヤー |
| エピソード記憶（Wiki） | wiki-runner（recording 経由で自動連携、再生成可） | プロジェクト通史・参照索引・議事索引・日記月次集約（diary は `memories/wiki/diary/`） |
| 教訓・改善 | `retrospective` skill | フェーズ完了後に skills/rules を更新 |

## 運用原則

- 本 skill は「いつ・何をしたか／参照したか／決めたか」を保存する。普遍的なルール化が必要なら `retrospective` で意味/手続き記憶へ昇華する
- 記録は `kind` と `status` を必ず持つ。古い記録は `superseded` へ降格し、ないより悪い状態にしない
- session の再生成・上書きが起きたら、旧版との関係を `supersedes` フィールドで明示する
- **diary は通常 kind**: diary は session / web / minutes と同列の通常 kind で、raw / 月次 Wiki / cocoindex インデックスのすべてが共有 NAS（`memories_dir`）配下に置かれる。session レポートが「感情的表現」を意図的に除外する設計なのに対し、diary はその逆で気持ちをそのまま残す唯一のレイヤー
