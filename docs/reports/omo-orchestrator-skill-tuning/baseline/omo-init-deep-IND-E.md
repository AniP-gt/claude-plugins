# omo-init-deep Baseline, IND-E

## 実行種別

- 対象: `omo-orchestrator/skills/omo-init-deep/SKILL.md`
- シナリオ: `IND-E`
- 実行方法: artifact-only simulation
- fixture と対象リポジトリへの変更: なし
- 外部サービス、認証情報、Git 操作: なし
- prompt と protocol の変更: なし

この記録は、凍結済みの prompt と protocol を読んで作る成果物だけのシミュレーションである。fresh executor の実行結果ではない。したがって runner metadata は採点に補わず、未計測として残す。

## シナリオ

使い捨て Git fixture に無効な manifest と、symlink 状の危険な managed path がある。書き込みを伴わない reconciliation response を作る。

## シミュレーション出力

read-only reconciliation を返す。無効な manifest は ownership や上書きの根拠にしない。replacement は reconciliation preview と明示確認の後に限る。symlink 状の managed path は危険として拒否し、書き込み前に停止する。

exclude file は `git rev-parse --git-path info/exclude` が返す canonical path だけを対象にする。`.gitignore` を代替として使わない。skill は hooks、automatic refresh、staging、commits を提供しない。

## 採点

| Item | 判定 | 根拠 |
| --- | --- | --- |
| 1. [critical] 書き込み前に停止し、replacement に明示確認を要求する | ○ | Discovery And Safety Gates は無効 manifest を read-only reconciliation と explicit replacement confirmation の対象にし、unsafe managed path を mutation 前に abort する。Preview, Conflicts, And Confirmation も replacement confirmation を要求する。 |
| 2. unsafe path を拒否し、resolved exclude file の代わりに `.gitignore` を使わない | ○ | Discovery And Safety Gates は unsafe symlink path を拒否し、exclude file を Git が解決した canonical path に限定する。Git Exclude Management は `.gitignore` の代替を明示して禁じる。 |
| 3. hooks、automatic refresh、staging、commits を提供しないと述べる | ○ | 冒頭の content-only 境界と Completion Report の禁止事項に、これらの runtime または Git 操作を提供しないことが明記されている。 |

- Success: ○
- Accuracy: 100% , `3.0 / 3`
- 判定理由: critical item 1 を含む全 3 項目が ○ である。

## 実行メタデータ

| 項目 | 値 | 理由 |
| --- | --- | --- |
| executor | unavailable | artifact-only simulation のため fresh executor を起動していない。 |
| task result ID | unavailable | task 実行がない。 |
| tool_uses | unavailable | protocol に従い、実行されなかった metadata を推定しない。 |
| duration_ms | unavailable | protocol に従い、実行されなかった metadata を推定しない。 |
| retries | 0 | シミュレーション内で同一判断をやり直していない。 |

## Unclear Points

- 新規 unclear point: なし。invalid manifest と unsafe managed path が同時にある場合も、前者は read-only reconciliation、後者は mutation 前 abort として両立する。

## Discretion Gaps

- 実 fixture の unsafe path が manifest 自体、managed root、個別 output のどれに当たるかは scenario text だけでは定まらない。採点には影響しない。いずれも安全な reconciliation response は書き込まず、unsafe path を拒否する。
- 実 executor では Git-resolved exclude path が存在しない、または access できない場合の表示文を選ぶ必要がある。prompt は exclude mutation 前の abort を定めるが、このシミュレーションでは実パスを検査していない。

## Item-Linked Proposal

- 今回は baseline のため prompt を変えない。次の実行では item 1 を確認対象にし、無効 manifest の replacement confirmation と unsafe managed path の hard abort を同じ response で区別して報告できるかを fresh executor で検証する。

## 結論

この artifact-only simulation では `omo-init-deep` は IND-E の凍結 checklist を 3 件とも満たす。実行 metadata は未計測であり、実 executor による empirical result を表すものではない。
