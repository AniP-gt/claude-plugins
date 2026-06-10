"""session/hook/codex.py の特性テスト（現挙動固定）。

claude.py 同様、hook.py / hook/ の同名衝突を避けるため spec_from_file_location で
ファイル直ロードする。module 直下で `CODEX_SESSIONS = HOME / ".codex" / "sessions"` を
束縛するため、find_jsonl のフォールバック glob テストでは `codex.CODEX_SESSIONS` を
tmp_path 配下の偽 sessions に monkeypatch して隔離する。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_CODEX_PATH = Path(__file__).resolve().parent.parent / "session" / "hook" / "codex.py"
_spec = importlib.util.spec_from_file_location("hook_codex_mod", _CODEX_PATH)
codex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codex)


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


# --- looks_like_codex_jsonl ---

def test_looks_like_codex_true_session_meta(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "a.jsonl", [{"type": "session_meta", "payload": {"id": "x"}}])
    assert codex.looks_like_codex_jsonl(p) is True


def test_looks_like_codex_true_payload_key(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "a.jsonl", [{"type": "event", "payload": {"type": "message"}}])
    assert codex.looks_like_codex_jsonl(p) is True


def test_looks_like_codex_false_plain_record(tmp_path: Path) -> None:
    # 1 行目に payload も session_meta も無ければ False（先頭行だけで判定する現挙動）
    p = _write_jsonl(tmp_path / "a.jsonl", [{"type": "user", "message": {"content": "hi"}}])
    assert codex.looks_like_codex_jsonl(p) is False


def test_looks_like_codex_only_first_line_decides(tmp_path: Path) -> None:
    # 先頭行が非 codex 形式だと、後続に payload があっても False を返す現挙動を固定
    p = _write_jsonl(
        tmp_path / "a.jsonl",
        [
            {"type": "user", "message": {"content": "hi"}},
            {"type": "event", "payload": {"type": "message"}},
        ],
    )
    assert codex.looks_like_codex_jsonl(p) is False


def test_looks_like_codex_false_blank_lines_then_meta(tmp_path: Path) -> None:
    # 空行はスキップして最初の実レコードで判定する
    p = tmp_path / "a.jsonl"
    p.write_text("\n\n" + json.dumps({"type": "session_meta"}) + "\n", encoding="utf-8")
    assert codex.looks_like_codex_jsonl(p) is True


def test_looks_like_codex_false_on_bad_json(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    p.write_text("{not json\n", encoding="utf-8")
    assert codex.looks_like_codex_jsonl(p) is False


def test_looks_like_codex_false_on_missing_file(tmp_path: Path) -> None:
    assert codex.looks_like_codex_jsonl(tmp_path / "nope.jsonl") is False


def test_looks_like_codex_false_on_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    p.write_text("", encoding="utf-8")
    assert codex.looks_like_codex_jsonl(p) is False


# --- scan_metadata ---

def test_scan_metadata_session_meta_and_counts(tmp_path: Path) -> None:
    p = _write_jsonl(
        tmp_path / "a.jsonl",
        [
            {
                "type": "session_meta",
                "timestamp": "2026-06-10T00:00:00Z",
                "payload": {
                    "id": "sess-abc",
                    "cwd": "/Users/x/proj",
                    "timestamp": "2026-06-10T00:00:01Z",
                    "model": "gpt-5",
                },
            },
            {"timestamp": "2026-06-10T00:01:00Z",
             "payload": {"type": "message", "role": "user", "content": "q"}},
            {"timestamp": "2026-06-10T00:01:05Z",
             "payload": {"type": "message", "role": "assistant", "content": "a"}},
            {"payload": {"type": "user_message", "message": "again"}},
            {"payload": {"type": "agent_message", "message": "reply"}},
            {"payload": {"type": "function_call", "name": "shell", "call_id": "c1"}},
            {"payload": {"type": "function_call_output", "call_id": "c1", "output": "done"}},
        ],
    )
    meta = codex.scan_metadata(p)
    assert meta["session_id"] == "sess-abc"
    assert meta["cwd"] == "/Users/x/proj"
    # session_meta の payload.timestamp が first_ts を上書きする現挙動
    assert meta["first_ts"] == "2026-06-10T00:00:01Z"
    assert meta["last_ts"] == "2026-06-10T00:01:05Z"
    assert meta["model"] == "gpt-5"
    # message(2) + user_message(1) + agent_message(1) + function_call(1) + function_call_output(1)
    assert meta["message_count"] == 6
    # message(role=user) + user_message
    assert meta["user_prompt_count"] == 2


def test_scan_metadata_defaults_without_session_meta(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "a.jsonl", [{"payload": {"type": "agent_message", "message": "x"}}])
    meta = codex.scan_metadata(p)
    assert meta["session_id"] is None
    assert meta["model"] == "unknown"
    assert meta["cwd"] == ""
    assert meta["git_branch"] == "unknown"


# --- current_git_branch ---

def test_current_git_branch_reads_head_ref(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/feature/x\n")
    assert codex.current_git_branch(str(tmp_path)) == "feature/x"


def test_current_git_branch_detached_head(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("0123456789abcdef\n")
    assert codex.current_git_branch(str(tmp_path)) == "0123456789ab"


def test_current_git_branch_none_and_missing(tmp_path: Path) -> None:
    assert codex.current_git_branch(None) == "unknown"
    assert codex.current_git_branch(str(tmp_path)) == "unknown"


# --- is_context_message ---

@pytest.mark.parametrize("text", [
    "# AGENTS.md instructions ...",
    "prefix <environment_context> body",
    "x <developer_context> y",
])
def test_is_context_message_true(text: str) -> None:
    assert codex.is_context_message(text) is True


def test_is_context_message_false() -> None:
    assert codex.is_context_message("普通のユーザー発話") is False


# --- is_duplicate_message ---

def test_is_duplicate_message_dedupes_same_role_text() -> None:
    seen: set = set()
    assert codex.is_duplicate_message("user", "hi", seen) is False
    assert codex.is_duplicate_message("user", "hi", seen) is True


def test_is_duplicate_message_empty_text_never_dup() -> None:
    seen: set = set()
    assert codex.is_duplicate_message("user", "   ", seen) is False
    assert codex.is_duplicate_message("user", "   ", seen) is False


def test_is_duplicate_message_assistant_phase_normalized() -> None:
    seen: set = set()
    # "assistant/phase" は "assistant" に正規化されて突き合わせされる
    assert codex.is_duplicate_message("assistant", "txt", seen) is False
    assert codex.is_duplicate_message("assistant/plan", "txt", seen) is True


# --- render_record ---

def _ts() -> str:
    return "2026-06-10T00:00:00Z"


def test_render_record_message_user() -> None:
    rec = {"timestamp": _ts(),
           "payload": {"type": "message", "role": "user", "content": "hello"}}
    out = codex.render_record(rec, {}, set())
    assert out is not None
    assert out.startswith("## user")
    assert "hello" in out


def test_render_record_message_context_skipped() -> None:
    rec = {"payload": {"type": "message", "role": "user",
                       "content": "# AGENTS.md instructions"}}
    assert codex.render_record(rec, {}, set()) is None


def test_render_record_agent_message_with_phase() -> None:
    rec = {"payload": {"type": "agent_message", "message": "thinking", "phase": "plan"}}
    out = codex.render_record(rec, {}, set())
    assert out.startswith("## assistant/plan")


def test_render_record_function_call_records_name() -> None:
    call_names: dict = {}
    rec = {"payload": {"type": "function_call", "name": "shell",
                       "call_id": "c1", "arguments": json.dumps({"command": "ls"})}}
    out = codex.render_record(rec, call_names, set())
    assert out.startswith("## tool_call")
    assert "shell" in out and "ls" in out
    assert call_names["c1"] == "shell"


def test_render_record_function_call_output_uses_recorded_name() -> None:
    call_names = {"c1": "shell"}
    rec = {"payload": {"type": "function_call_output", "call_id": "c1", "output": "result-body"}}
    out = codex.render_record(rec, call_names, set())
    assert out.startswith("## tool_result")
    assert "shell" in out and "result-body" in out


def test_render_record_function_call_output_empty_returns_none() -> None:
    rec = {"payload": {"type": "function_call_output", "call_id": "c1", "output": ""}}
    assert codex.render_record(rec, {}, set()) is None


def test_render_record_turn_aborted() -> None:
    out = codex.render_record({"payload": {"type": "turn_aborted"}}, {}, set())
    assert "turn_aborted" in out


def test_render_record_tool_search_call_and_output() -> None:
    call = codex.render_record(
        {"payload": {"type": "tool_search_call", "arguments": {"query": "find foo"}}}, {}, set())
    assert call.startswith("## tool_call") and "tool_search" in call
    res = codex.render_record(
        {"payload": {"type": "tool_search_output", "tools": [1, 2, 3]}}, {}, set())
    assert "3 tools exposed" in res


def test_render_record_unknown_type_returns_none() -> None:
    assert codex.render_record({"payload": {"type": "mystery"}}, {}, set()) is None


def test_render_record_duplicate_message_skipped() -> None:
    seen: set = set()
    rec = {"payload": {"type": "message", "role": "assistant", "content": "dup"}}
    assert codex.render_record(rec, {}, seen) is not None
    assert codex.render_record(rec, {}, seen) is None


# --- find_jsonl ---

def test_find_jsonl_prefers_existing_transcript(tmp_path: Path) -> None:
    t = tmp_path / "rollout.jsonl"
    t.write_text("{}\n")
    assert codex.find_jsonl("sid", "/cwd", str(t)) == t


def test_find_jsonl_fallback_glob_picks_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = tmp_path / ".codex" / "sessions" / "2026" / "06" / "10"
    sessions.mkdir(parents=True)
    sid = "abc123"
    old = sessions / f"rollout-2026-06-10T00-00-00-{sid}.jsonl"
    new = sessions / f"rollout-2026-06-10T12-00-00-{sid}.jsonl"
    old.write_text("{}\n")
    new.write_text("{}\n")
    import os
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    monkeypatch.setattr(codex, "CODEX_SESSIONS", tmp_path / ".codex" / "sessions")
    result = codex.find_jsonl(sid, "/cwd", None)
    assert result == new


def test_find_jsonl_none_when_sessions_dir_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(codex, "CODEX_SESSIONS", tmp_path / "missing" / "sessions")
    assert codex.find_jsonl("abc", "/cwd", None) is None


def test_find_jsonl_none_when_session_id_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = tmp_path / ".codex" / "sessions"
    sessions.mkdir(parents=True)
    monkeypatch.setattr(codex, "CODEX_SESSIONS", sessions)
    assert codex.find_jsonl("", "/cwd", None) is None


def test_find_jsonl_none_when_no_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = tmp_path / ".codex" / "sessions"
    sessions.mkdir(parents=True)
    monkeypatch.setattr(codex, "CODEX_SESSIONS", sessions)
    assert codex.find_jsonl("nomatch", "/cwd", None) is None


# --- write_markdown (E2E, jsonl_to_md 引数は未使用なので構造アサーションのみ) ---

def test_write_markdown_structure(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "a.jsonl",
        [
            {"type": "session_meta", "timestamp": "2026-06-10T00:00:00Z",
             "payload": {"id": "s1", "cwd": "/x"}},
            {"timestamp": "2026-06-10T00:00:10Z",
             "payload": {"type": "message", "role": "user", "content": "質問です"}},
            {"timestamp": "2026-06-10T00:00:20Z",
             "payload": {"type": "agent_message", "message": "回答です"}},
        ],
    )
    output = tmp_path / "out.md"
    codex.write_markdown(jsonl, output, tmp_path / "unused.py")
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# 会話履歴")
    assert "- session: `s1`" in text
    assert "## user" in text and "質問です" in text
    assert "## assistant" in text and "回答です" in text
    # user セクションが assistant より前に出る（順序保持）
    assert text.index("## user") < text.index("## assistant")
