# episodic plugin tests

Python 単体テスト（pytest）。`wiki/enqueue.py` の主要関数と CLI 動作を網羅する。

## 実行

```bash
cd episodic
uv sync --extra test
uv run pytest
```

## カバレッジ範囲

- `sanitize_slug` / `detect_kind` / `_entry_identity` / `_append_entry` の単体テスト
- `enqueue.py` を subprocess で呼び出す E2E:
  - minutes/diary 時に `people_extract` が自動連動 enqueue される
  - session は連動しない
  - 同 raw の再 enqueue は両エントリ dedupe される
  - person の必須引数欠落で rc=3
  - person slug がサニタイズで空になると rc=3
  - person 正常系（slug サニタイズ・aliases・context が保持される）
  - パイプ / パストラバーサル混入 slug がサニタイズで無害化される
  - 同 raw 異 slug は別エントリとして共存できる

## HOME 隔離

`conftest.py` の `isolated_home` fixture が必ず HOME を `tmp_path` に固定する。テストは
ユーザーの実 `~/.local/share/episodic/state/ingest-queue.jsonl` には絶対に触れない。

過去（2026-05-15）に手動シェルテストで HOME 上書きが伝播せず実 queue を汚染した
インシデントが発生したため、回帰検知のテスト（`TestRealQueueIsNotTouched`）も含む。
