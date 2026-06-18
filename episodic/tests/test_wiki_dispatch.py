"""lib/wiki_dispatch.py のテスト。

経路:
  - マーカー不在 → parse 失敗
  - 不正 JSON → parse 失敗
  - 正常 → enqueue.py が人物ごとに呼ばれ、引数が期待通り
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_dispatch  # noqa: E402


def test_capture_missing_returns_failed(tmp_path: Path) -> None:
    parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
        tmp_path / "absent.log",
        raw_path=tmp_path / "raw.md",
        source_kind="minutes",
        enqueue_script=tmp_path / "enqueue.py",
    )
    assert parsed_ok is False
    assert appended == 0


def test_no_markers_failed(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    cap.write_text("some output without markers")
    parsed_ok, _, _ = wiki_dispatch.dispatch_person_enqueues_from_capture(
        cap,
        raw_path=tmp_path / "raw.md",
        source_kind="diary",
        enqueue_script=tmp_path / "enqueue.py",
    )
    assert parsed_ok is False


def test_invalid_json_failed(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    cap.write_text("prefix\n<<<PEOPLE_JSON_BEGIN>>> not json <<<PEOPLE_JSON_END>>>\n")
    parsed_ok, _, _ = wiki_dispatch.dispatch_person_enqueues_from_capture(
        cap,
        raw_path=tmp_path / "raw.md",
        source_kind="minutes",
        enqueue_script=tmp_path / "enqueue.py",
    )
    assert parsed_ok is False


def test_valid_dispatches_to_enqueue(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    raw_path = tmp_path / "raw.md"
    raw_path.write_text("body")
    payload = {
        "people": [
            {
                "name": "山田",
                "slug": "yamada",
                "source_raw": str(raw_path),
                "source_kind": "minutes",
                "aliases": ["taro", "yan"],
                "context": "ctx",
            },
            {
                "name": "鈴木",
                "slug": "suzuki",
                "source_raw": str(raw_path),
                "source_kind": "minutes",
                "aliases": [],
                "context": "",
            },
            # 不完全エントリはスキップ
            {"name": "", "slug": "x", "source_raw": str(raw_path), "source_kind": "minutes"},
        ]
    }
    cap.write_text(
        f"noise\n<<<PEOPLE_JSON_BEGIN>>>\n{json.dumps(payload)}\n<<<PEOPLE_JSON_END>>>\nfooter\n"
    )

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check, timeout):  # noqa: ARG001
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch.object(wiki_dispatch.subprocess, "run", side_effect=fake_run):
        parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
            cap,
            raw_path=raw_path,
            source_kind="minutes",
            enqueue_script=tmp_path / "enqueue.py",
        )
    assert parsed_ok is True
    assert appended == 2
    assert errors == 0
    # コマンド構成を検査
    assert len(calls) == 2
    cmd0 = calls[0]
    assert "--kind" in cmd0 and "person" in cmd0
    assert "--name" in cmd0
    idx = cmd0.index("--slug")
    assert cmd0[idx + 1] == "yamada"
    idx = cmd0.index("--source-kind")
    assert cmd0[idx + 1] == "minutes"
    idx = cmd0.index("--aliases")
    assert cmd0[idx + 1] == "taro,yan"


def test_enqueue_failure_counted_as_error(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    raw_path = tmp_path / "raw.md"
    raw_path.write_text("body")
    payload = {
        "people": [
            {"name": "山田", "slug": "yamada", "source_raw": str(raw_path), "source_kind": "minutes"},
        ]
    }
    cap.write_text(f"<<<PEOPLE_JSON_BEGIN>>>\n{json.dumps(payload)}\n<<<PEOPLE_JSON_END>>>")

    def fake_run(cmd, capture_output, text, check, timeout):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    with patch.object(wiki_dispatch.subprocess, "run", side_effect=fake_run):
        parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
            cap,
            raw_path=raw_path,
            source_kind="minutes",
            enqueue_script=tmp_path / "enqueue.py",
        )
    assert parsed_ok is False  # errors>0 なので parsed_ok=False
    assert appended == 0
    assert errors == 1
