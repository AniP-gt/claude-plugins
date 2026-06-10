"""session/jsonl-to-markdown.py の特性テスト（現挙動固定）。

ハイフン入りファイル名のため spec_from_file_location でロードする
（test_org_pipeline.py の idiom を踏襲）。stdlib のみ依存で単体ロード可能。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_J2M_PATH = Path(__file__).resolve().parent.parent / "session" / "jsonl-to-markdown.py"
_spec = importlib.util.spec_from_file_location("jsonl_to_markdown_mod", _J2M_PATH)
j2m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(j2m)


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


# --- is_pasted_slash_command ---

@pytest.mark.parametrize("text", [
    "❯ /clear",
    "> /compact something",
    "/foo bar\n  ⎿ box output",
])
def test_is_pasted_slash_command_true(text: str) -> None:
    assert j2m.is_pasted_slash_command(text) is True


@pytest.mark.parametrize("text", [
    "通常のメッセージ",
    "/slash だがボックスも prompt 接頭辞も無い",
    "二行目に / があるだけ\n/here",
])
def test_is_pasted_slash_command_false(text: str) -> None:
    assert j2m.is_pasted_slash_command(text) is False


# --- should_skip ---

def test_should_skip_non_message_type() -> None:
    assert j2m.should_skip({"type": "summary"}) is True


def test_should_skip_is_meta() -> None:
    assert j2m.should_skip(
        {"type": "user", "isMeta": True, "message": {"content": "x"}}) is True


def test_should_skip_local_command_tag_string() -> None:
    rec = {"type": "user", "message": {"content": "<command-name>foo</command-name>"}}
    assert j2m.should_skip(rec) is True


def test_should_skip_pasted_slash_string() -> None:
    rec = {"type": "user", "message": {"content": "❯ /clear"}}
    assert j2m.should_skip(rec) is True


def test_should_skip_list_all_command_blocks() -> None:
    rec = {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "<command-stdout>out</command-stdout>"},
    ]}}
    assert j2m.should_skip(rec) is True


def test_should_skip_false_for_real_message() -> None:
    rec = {"type": "user", "message": {"content": "本物の発話"}}
    assert j2m.should_skip(rec) is False


def test_should_skip_false_when_list_has_non_command_text() -> None:
    rec = {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "real answer"},
        {"type": "text", "text": "<command-name>x</command-name>"},
    ]}}
    # 1 つでも非コマンドテキストがあれば保持する現挙動
    assert j2m.should_skip(rec) is False


# --- compress_tool_result ---

def test_compress_tool_result_error_keeps_head() -> None:
    body = "E" * (j2m.TOOL_RESULT_ERROR_HEAD_BYTES + 500)
    out = j2m.compress_tool_result(body, "Bash", is_error=True)
    assert out.startswith("E" * 100)
    assert "truncated (error tail)" in out


def test_compress_tool_result_error_short_unchanged() -> None:
    body = "short error"
    assert j2m.compress_tool_result(body, "Bash", is_error=True) == body


def test_compress_tool_result_drop_body_tool() -> None:
    body = "x" * 500
    out = j2m.compress_tool_result(body, "Read", is_error=False,
                                   tool_input={"file_path": "/a/b.py"})
    assert "Read result body omitted" in out
    assert "/a/b.py" in out
    assert "x" * 500 not in out


def test_compress_tool_result_drop_body_short_kept() -> None:
    # DROP_BODY 対象でも 200 文字以下なら本文を残す
    body = "x" * 50
    assert j2m.compress_tool_result(body, "Read", is_error=False) == body


def test_compress_tool_result_keep_under_limit() -> None:
    body = "y" * (j2m.TOOL_RESULT_KEEP_LIMIT - 1)
    assert j2m.compress_tool_result(body, "Bash", is_error=False) == body


def test_compress_tool_result_head_tail_over_limit() -> None:
    body = "z" * (j2m.TOOL_RESULT_KEEP_LIMIT + 1000)
    out = j2m.compress_tool_result(body, "Bash", is_error=False)
    assert "chars truncated" in out
    assert out.startswith("z" * j2m.TOOL_RESULT_HEAD_BYTES)
    assert out.endswith("z" * j2m.TOOL_RESULT_TAIL_BYTES)


# --- _tool_use_inline / compress_tool_input ---

def test_tool_use_inline_file_path() -> None:
    assert j2m._tool_use_inline("Read", {"file_path": "/x.py"}) == "Read: [/x.py]"


def test_tool_use_inline_command_newlines_collapsed() -> None:
    out = j2m._tool_use_inline("Bash", {"command": "a\nb"})
    assert out == "Bash: [a ⏎ b]"


def test_tool_use_inline_agent_subagent() -> None:
    out = j2m._tool_use_inline("Agent", {"description": "do x", "subagent_type": "impl"})
    assert "do x" in out and "subagent=impl" in out


def test_tool_use_inline_empty_input() -> None:
    assert j2m._tool_use_inline("X", {}) == "X: []"


def test_tool_use_inline_returns_none_for_unkeyed() -> None:
    # 識別キーの無い複雑な input は None（呼び出し側で JSON フォールバック）
    assert j2m._tool_use_inline("Weird", {"foo": "bar", "baz": 1}) is None


def test_compress_tool_input_truncates_long_value() -> None:
    long = "p" * (j2m.TOOL_INPUT_LONG_THRESHOLD + 100)
    out = j2m.compress_tool_input({"prompt": long, "file_path": "/x"})
    assert "chars truncated" in out["prompt"]
    assert out["file_path"] == "/x"  # 識別キーは無変更
    assert len(out["prompt"]) < len(long)


def test_compress_tool_input_non_dict_passthrough() -> None:
    assert j2m.compress_tool_input("scalar") == "scalar"


# --- fence ---

def test_fence_escapes_backticks() -> None:
    out = j2m.fence("text with ``` inside")
    # 内部の最大連続バッククォート(3)より長いフェンスを使う
    assert out.startswith("````")


# --- end-to-end main() ---

def test_main_end_to_end_structure(tmp_path: Path) -> None:
    records = [
        {"type": "user", "sessionId": "sess-1", "timestamp": "2026-06-10T00:00:00Z",
         "message": {"role": "user", "content": "実装してください"}},
        # スキップされるべき meta レコード
        {"type": "user", "isMeta": True,
         "message": {"role": "user", "content": "META-SHOULD-NOT-APPEAR"}},
        # スキップされるべきペーストスラッシュ
        {"type": "user", "message": {"role": "user", "content": "❯ /clear PASTED-SLASH"}},
        # assistant: tool_use (Read) + text
        {"type": "assistant", "timestamp": "2026-06-10T00:00:10Z",
         "message": {"role": "assistant", "content": [
             {"type": "text", "text": "ファイルを読みます"},
             {"type": "tool_use", "id": "t1", "name": "Read",
              "input": {"file_path": "/repo/main.py"}},
         ]}},
        # tool_result(成功)は省略される
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "file body here"},
        ]}},
        # サブエージェント起動
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t2", "name": "Task",
             "input": {"description": "調査タスク", "subagent_type": "explorer"}},
        ]}},
        # 最終 assistant 発話
        {"type": "assistant", "timestamp": "2026-06-10T00:01:00Z",
         "message": {"role": "assistant", "content": "完了しました"}},
    ]
    jsonl = _write_jsonl(tmp_path / "conv.jsonl", records)
    output = tmp_path / "conv.md"
    rc = j2m.main(["prog", str(jsonl), str(output)])
    assert rc == 0
    text = output.read_text(encoding="utf-8")

    # 見出し・メタ
    assert text.startswith("# 会話履歴")
    assert "- session: `sess-1`" in text
    assert f"- source: `{jsonl}`" in text

    # 実発話は保持
    assert "実装してください" in text
    assert "完了しました" in text
    assert "ファイルを読みます" in text

    # スキップ対象は不在
    assert "META-SHOULD-NOT-APPEAR" not in text
    assert "PASTED-SLASH" not in text

    # tool_use は 1 行インライン化
    assert "Read: [/repo/main.py]" in text
    # サブエージェント起動が記録される
    assert "調査タスク" in text and "subagent=explorer" in text
    # 成功 tool_result の本文は省略される
    assert "file body here" not in text

    # 順序: 最初の user 発話 → assistant の Read → 最終 assistant
    assert text.index("実装してください") < text.index("Read: [/repo/main.py]") < text.index("完了しました")


def test_main_error_tool_result_kept(tmp_path: Path) -> None:
    records = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "e1", "name": "Bash",
             "input": {"command": "make ci"}},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "e1", "is_error": True,
             "content": "FATAL: build broke"},
        ]}},
    ]
    jsonl = _write_jsonl(tmp_path / "err.jsonl", records)
    output = tmp_path / "err.md"
    assert j2m.main(["prog", str(jsonl), str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    # エラー時は診断のため本文を残す
    assert "FATAL: build broke" in text
    assert "Bash ERROR" in text or "`Bash` ERROR" in text


def test_main_stdin_buffered_two_pass(monkeypatch, capsys) -> None:
    # 入力省略時は stdin を一度バッファして 2 パス走査する（再走査不能な stdin の担保）。
    import io

    records = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t9", "name": "Read",
             "input": {"file_path": "/z.py"}},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t9", "content": "body"},
        ]}},
        {"type": "assistant", "message": {"role": "assistant", "content": "完了"}},
    ]
    stdin_text = "\n".join(json.dumps(r) for r in records) + "\n"
    monkeypatch.setattr(j2m.sys, "stdin", io.StringIO(stdin_text))
    rc = j2m.main(["prog"])  # 入力・出力省略 → stdin→stdout
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("# 会話履歴")
    # 1パス目で構築したマップを 2パス目で参照できている
    assert "Read: [/z.py]" in out
    assert "完了" in out


def test_main_help_returns_zero(capsys) -> None:
    assert j2m.main(["prog", "--help"]) == 0


def test_main_empty_input_only_header(tmp_path: Path) -> None:
    jsonl = _write_jsonl(tmp_path / "empty.jsonl", [])
    output = tmp_path / "empty.md"
    assert j2m.main(["prog", str(jsonl), str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    # 本文セクションは無いが、見出しと source メタ行のみ出力される現挙動
    assert text.startswith("# 会話履歴")
    assert f"- source: `{jsonl}`" in text
    assert "## " not in text
