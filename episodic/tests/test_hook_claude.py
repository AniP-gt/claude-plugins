"""session/hook/claude.py の特性テスト（現挙動固定）。

session/hook.py（ファイル）と session/hook/（ディレクトリ）が同名で共存し、
`import hook` では衝突するため、ハイフン無しでもファイルパス直指定で
spec_from_file_location ロードする（test_org_pipeline.py の idiom を踏襲）。

claude.py は stdlib のみ依存・パッケージ内 import 無しのため単体ロード可能。
module 直下で `HOME = Path.home()` を束縛するため、パス解決テストでは
`claude.HOME` を monkeypatch して隔離する（conftest の HOME 隔離方針に整合）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_CLAUDE_PATH = Path(__file__).resolve().parent.parent / "session" / "hook" / "claude.py"
_spec = importlib.util.spec_from_file_location("hook_claude_mod", _CLAUDE_PATH)
claude = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(claude)


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


# --- encode_cwd ---

def test_encode_cwd_replaces_slashes() -> None:
    assert claude.encode_cwd("/Users/x/proj") == "-Users-x-proj"


def test_encode_cwd_empty() -> None:
    assert claude.encode_cwd("") == ""


# --- find_jsonl ---

def test_find_jsonl_prefers_existing_transcript(tmp_path: Path) -> None:
    t = tmp_path / "transcript.jsonl"
    t.write_text("{}\n")
    assert claude.find_jsonl("sid", "/cwd", str(t)) == t


def test_find_jsonl_ignores_missing_transcript_then_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(claude, "HOME", tmp_path)
    cwd = "/Users/x/proj"
    proj_dir = tmp_path / ".claude" / "projects" / claude.encode_cwd(cwd)
    proj_dir.mkdir(parents=True)
    candidate = proj_dir / "sid-123.jsonl"
    candidate.write_text("{}\n")
    # transcript_path は実在しないので無視し candidate にフォールバックする
    result = claude.find_jsonl("sid-123", cwd, str(tmp_path / "nope.jsonl"))
    assert result == candidate


def test_find_jsonl_returns_none_when_nothing_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(claude, "HOME", tmp_path)
    assert claude.find_jsonl("sid", "/cwd", None) is None


def test_find_jsonl_returns_none_with_empty_session_and_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(claude, "HOME", tmp_path)
    assert claude.find_jsonl("", "", None) is None


# --- scan_metadata ---

def test_scan_metadata_collects_core_fields(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-06-10T01:00:00Z",
                "cwd": "/Users/x/proj",
                "gitBranch": "main",
                "message": {"role": "user", "content": "hello"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-06-10T01:00:05Z",
                "message": {"role": "assistant", "content": "hi", "model": "claude-3"},
            },
        ],
    )
    meta = claude.scan_metadata(jsonl)
    assert meta["first_ts"] == "2026-06-10T01:00:00Z"
    assert meta["last_ts"] == "2026-06-10T01:00:05Z"
    assert meta["cwd"] == "/Users/x/proj"
    assert meta["git_branch"] == "main"
    assert meta["message_count"] == 2
    assert meta["user_prompt_count"] == 1
    assert meta["model"] == "claude-3"
    # session_id は常に None を返す現挙動（要確認: ハードコード）
    assert meta["session_id"] is None


def test_scan_metadata_skips_meta_and_command_records(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "user", "isMeta": True,
             "message": {"role": "user", "content": "meta"}},
            {"type": "user",
             "message": {"role": "user", "content": "<command-name>foo</command-name>"}},
            {"type": "user",
             "message": {"role": "user", "content": "❯ /clear"}},
            {"type": "assistant",
             "message": {"role": "assistant", "content": "real answer"}},
        ],
    )
    meta = claude.scan_metadata(jsonl)
    # meta / command タグ / ペーストスラッシュは除外され、実応答 1 件のみ
    assert meta["message_count"] == 1
    assert meta["user_prompt_count"] == 0


def test_scan_metadata_model_picks_most_frequent(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "assistant", "message": {"role": "assistant", "content": "a", "model": "m1"}},
            {"type": "assistant", "message": {"role": "assistant", "content": "b", "model": "m2"}},
            {"type": "assistant", "message": {"role": "assistant", "content": "c", "model": "m2"}},
        ],
    )
    assert claude.scan_metadata(jsonl)["model"] == "m2"


def test_scan_metadata_defaults_for_empty_jsonl(tmp_path: Path) -> None:
    jsonl = _write_jsonl(tmp_path / "s.jsonl", [])
    meta = claude.scan_metadata(jsonl)
    assert meta["model"] == "unknown"
    assert meta["git_branch"] == "unknown"
    assert meta["cwd"] == ""
    assert meta["message_count"] == 0
    assert meta["first_ts"] is None


def test_scan_metadata_tolerates_malformed_lines(tmp_path: Path) -> None:
    p = tmp_path / "s.jsonl"
    p.write_text(
        "not json\n"
        + json.dumps({"type": "user", "message": {"role": "user", "content": "ok"}})
        + "\n",
        encoding="utf-8",
    )
    meta = claude.scan_metadata(p)
    assert meta["message_count"] == 1


# --- write_markdown ---

def test_write_markdown_invokes_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []

    def fake_run(args, **kw):
        calls.append((args, kw))

    monkeypatch.setattr(claude.subprocess, "run", fake_run)
    jsonl = tmp_path / "in.jsonl"
    output = tmp_path / "out.md"
    converter = tmp_path / "jsonl-to-markdown.py"
    claude.write_markdown(jsonl, output, converter)
    assert len(calls) == 1
    args, kw = calls[0]
    assert args == [sys.executable, str(converter), str(jsonl), str(output)]
    assert kw["check"] is True
    assert kw["timeout"] == 60
