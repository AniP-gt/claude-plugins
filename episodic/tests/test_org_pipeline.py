"""org（組織）Wiki パイプライン追加分のテスト。

カバー範囲:
  - CodexRunner.web_search → `-c tools.web_search=true`
  - _default_codex_runner_factory が web_search を CodexRunner へ伝播
  - wiki_runner._resolve_wiki_target の org 経路 + パス脱出ガード
  - _process_batch_job の org web ゲーティング（web_checked_at 有無で web_search 切替）
  - wiki_dispatch が orgs 配列を enqueue --kind org（--category 付き）へ dispatch
  - wiki_prompt の既存レジストリ注入 / build_combined_prompt_org
  - wiki_index の Orgs セクション
  - enqueue.py の org kind（隔離 HOME で実 queue を汚さない）

実 queue（~/.local/share/episodic/state）・実データ（/Volumes/memory）は一切触らない。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_dispatch  # noqa: E402
from lib import wiki_index  # noqa: E402
from lib import wiki_prompt  # noqa: E402
from lib.codex_runner import CodexResult, CodexRunner  # noqa: E402

import importlib.util  # noqa: E402

# wiki_runner.py は wiki/ 配下（パッケージ外）にあるためファイルパスでロードする。
_WIKI_RUNNER_PATH = REPO_ROOT / "wiki" / "wiki_runner.py"
_spec = importlib.util.spec_from_file_location("wiki_runner_mod", _WIKI_RUNNER_PATH)
wiki_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wiki_runner)

ENQUEUE_SCRIPT = REPO_ROOT / "wiki" / "enqueue.py"


# ---------------------------------------------------------------------------
# CodexRunner.web_search
# ---------------------------------------------------------------------------
def test_codex_runner_web_search_flag_enabled() -> None:
    r = CodexRunner(model="gpt-5.4-mini", effort="low", codex_bin="/bin/echo", web_search=True)
    cmd = r.build_cmd(Path("/tmp/cap.log"))
    assert "tools.web_search=true" in cmd
    # `-c tools.web_search=true` の対で入っていること
    i = cmd.index("tools.web_search=true")
    assert cmd[i - 1] == "-c"


def test_codex_runner_web_search_flag_default_off() -> None:
    r = CodexRunner(model="gpt-5.4-mini", effort="low", codex_bin="/bin/echo")
    cmd = r.build_cmd(Path("/tmp/cap.log"))
    assert "tools.web_search=true" not in cmd


def test_default_factory_propagates_web_search() -> None:
    make = wiki_runner._default_codex_runner_factory(123)
    runner_on = make(model="m", sandbox_mode="workspace-write", cwd_dir=Path("/tmp"), web_search=True)
    runner_off = make(model="m", sandbox_mode="workspace-write", cwd_dir=Path("/tmp"))
    assert runner_on.web_search is True
    assert runner_off.web_search is False


# ---------------------------------------------------------------------------
# _resolve_wiki_target — org
# ---------------------------------------------------------------------------
def test_resolve_wiki_target_org(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    logs: list[str] = []
    entry = {"kind": "org", "slug": "ファルモ", "raw_path": str(tmp_path / "r.md")}
    kind, target, instruction, label, project = wiki_runner._resolve_wiki_target(
        entry, wiki_dir, logs.append
    )
    assert kind == "org"
    assert target == wiki_dir / "orgs" / "ファルモ.md"
    assert instruction == wiki_runner.INSTRUCTION_ORG
    assert project == "ファルモ"


def test_resolve_wiki_target_org_missing_slug(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    logs: list[str] = []
    entry = {"kind": "org", "slug": "", "raw_path": str(tmp_path / "r.md")}
    kind, target, _instruction, _label, _project = wiki_runner._resolve_wiki_target(
        entry, wiki_dir, logs.append
    )
    assert kind == "org"
    assert target is None


def test_resolve_wiki_target_org_escape_guard(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    logs: list[str] = []
    entry = {"kind": "org", "slug": "../../etc/passwd", "raw_path": str(tmp_path / "r.md")}
    # sanitize は enqueue 側だが、防衛層として slug に / が含まれると None。
    _kind, target, _i, _l, _p = wiki_runner._resolve_wiki_target(entry, wiki_dir, logs.append)
    assert target is None


# ---------------------------------------------------------------------------
# _process_batch_job — org web ゲーティング
# ---------------------------------------------------------------------------
def _run_org_job(tmp_path: Path, wiki_target: Path):
    """org の _process_batch_job を fake factory で実行し、渡された web_search を返す。"""
    captured: dict = {}

    def fake_factory(model, sandbox_mode, cwd_dir, web_search=False):
        captured["web_search"] = web_search
        captured["sandbox_mode"] = sandbox_mode

        class _FakeRunner:
            def run(self, prompt_path, log_file, capture_file=None):
                return CodexResult(returncode=0)

        return _FakeRunner()

    entries = [
        {
            "kind": "org",
            "slug": "ファルモ",
            "name": "ファルモ",
            "aliases": [],
            "category": "company",
            "context": "ctx",
            "source_kind": "minutes",
            "raw_path": str(tmp_path / "raw" / "minutes" / "2026-05-20" / "x.md"),
        }
    ]
    results = wiki_runner._process_batch_job(
        job_id="job-1",
        kind="org",
        wiki_target=wiki_target,
        instruction=wiki_runner.INSTRUCTION_ORG,
        label="orgs/ファルモ",
        project="ファルモ",
        model="gpt-5.4-mini",
        entries=entries,
        target_lock_root=tmp_path / "locks",
        log=lambda m: None,
        skip_codex=False,
        codex_runner_factory=fake_factory,
        log_file=tmp_path / "run.log",
        target_lock_timeout=5,
    )
    return results, captured


def test_org_web_search_enabled_when_unchecked(tmp_path: Path) -> None:
    wiki_target = tmp_path / "wiki" / "orgs" / "ファルモ.md"
    # ファイル未作成 → 未裏取り → web_search 有効
    results, captured = _run_org_job(tmp_path, wiki_target)
    assert all(r["status"] == "success" for r in results)
    assert captured["web_search"] is True
    assert captured["sandbox_mode"] == "workspace-write"


def test_org_web_search_disabled_when_checked(tmp_path: Path) -> None:
    wiki_target = tmp_path / "wiki" / "orgs" / "ファルモ.md"
    wiki_target.parent.mkdir(parents=True)
    wiki_target.write_text(
        "---\ntitle: ファルモ\nslug: ファルモ\nweb_checked_at: 2026-05-30\n---\n\n# ファルモ\n",
        encoding="utf-8",
    )
    results, captured = _run_org_job(tmp_path, wiki_target)
    assert all(r["status"] == "success" for r in results)
    assert captured["web_search"] is False


# ---------------------------------------------------------------------------
# wiki_dispatch — orgs 配列
# ---------------------------------------------------------------------------
def test_dispatch_handles_orgs(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    raw_path = tmp_path / "raw.md"
    raw_path.write_text("body")
    payload = {
        "people": [
            {"name": "河本", "slug": "河本", "org": "ファルモ", "source_raw": str(raw_path),
             "source_kind": "minutes", "aliases": ["河本さん"], "context": "c"},
        ],
        "orgs": [
            {"name": "ファルモ", "slug": "ファルモ", "category": "company",
             "source_raw": str(raw_path), "source_kind": "minutes",
             "aliases": ["株式会社ファルモ"], "context": "c"},
        ],
    }
    cap.write_text(f"<<<PEOPLE_JSON_BEGIN>>>\n{json.dumps(payload, ensure_ascii=False)}\n<<<PEOPLE_JSON_END>>>")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check, timeout):  # noqa: ARG001
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch.object(wiki_dispatch.subprocess, "run", side_effect=fake_run):
        parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
            cap, raw_path=raw_path, source_kind="minutes", enqueue_script=tmp_path / "enqueue.py",
        )
    assert parsed_ok is True
    assert errors == 0
    assert appended == 2  # person 1 + org 1
    org_cmds = [c for c in calls if "org" in c and "--kind" in c and c[c.index("--kind") + 1] == "org"]
    assert len(org_cmds) == 1
    oc = org_cmds[0]
    assert "--category" in oc and oc[oc.index("--category") + 1] == "company"
    assert oc[oc.index("--slug") + 1] == "ファルモ"


def test_dispatch_backward_compat_no_orgs_key(tmp_path: Path) -> None:
    cap = tmp_path / "cap.log"
    raw_path = tmp_path / "raw.md"
    raw_path.write_text("body")
    payload = {"people": [
        {"name": "河本", "slug": "河本", "source_raw": str(raw_path), "source_kind": "minutes"}
    ]}
    cap.write_text(f"<<<PEOPLE_JSON_BEGIN>>>\n{json.dumps(payload, ensure_ascii=False)}\n<<<PEOPLE_JSON_END>>>")

    def fake_run(cmd, capture_output, text, check, timeout):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch.object(wiki_dispatch.subprocess, "run", side_effect=fake_run):
        parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
            cap, raw_path=raw_path, source_kind="minutes", enqueue_script=tmp_path / "enqueue.py",
        )
    assert parsed_ok is True
    assert appended == 1


# ---------------------------------------------------------------------------
# wiki_prompt — レジストリ注入 / build_combined_prompt_org
# ---------------------------------------------------------------------------
def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    (wiki / "people").mkdir(parents=True)
    (wiki / "orgs").mkdir(parents=True)
    (wiki / "people" / "宮英嗣.md").write_text(
        "---\ntitle: 宮英嗣\nslug: 宮英嗣\naliases: [宮, miya]\nis_self: true\ncompany: メディエンサー\n---\n\n# 宮英嗣\n",
        encoding="utf-8",
    )
    (wiki / "people" / "河本.md").write_text(
        "---\ntitle: 河本さん\nslug: 河本\naliases: [河本さん, ファルモ河本]\ncompany: ファルモ\n---\n\n# 河本さん\n",
        encoding="utf-8",
    )
    (wiki / "orgs" / "ファルモ.md").write_text(
        "---\ntitle: ファルモ\nslug: ファルモ\naliases: [株式会社ファルモ]\nkind: org\ncategory: company\n---\n\n# ファルモ\n",
        encoding="utf-8",
    )
    return wiki


def test_build_registry_lists_people_and_orgs(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    reg = wiki_prompt.build_people_org_registry(wiki)
    assert wiki_prompt.REGISTRY_HEADING in reg
    assert "slug=宮英嗣" in reg
    assert "is_self=true" in reg
    assert "slug=河本" in reg
    assert "slug=ファルモ" in reg
    assert "category=company" in reg


def test_people_extract_prompt_injects_registry(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    instruction = tmp_path / "instr.md"
    instruction.write_text("INSTR {raw_count}", encoding="utf-8")
    wiki_target = wiki / "people" / ".extract-placeholder"
    prompt = wiki_prompt.build_combined_prompt_batch(
        instruction, wiki_target, [], "people_extract"
    )
    assert wiki_prompt.REGISTRY_HEADING in prompt
    assert "slug=宮英嗣" in prompt


def test_minutes_prompt_does_not_inject_registry(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    instruction = tmp_path / "instr.md"
    instruction.write_text("INSTR {raw_count}", encoding="utf-8")
    wiki_target = wiki / "minutes" / "202605.md"
    prompt = wiki_prompt.build_combined_prompt_batch(
        instruction, wiki_target, [], "minutes"
    )
    assert wiki_prompt.REGISTRY_HEADING not in prompt


def test_build_combined_prompt_org_web_note(tmp_path: Path) -> None:
    instruction = tmp_path / "instr.md"
    instruction.write_text("INSTR {slug} {raw_count}", encoding="utf-8")
    wiki_target = tmp_path / "wiki" / "orgs" / "ファルモ.md"
    mentions = [{"name": "ファルモ", "slug": "ファルモ", "context": "c", "source_kind": "minutes"}]
    on = wiki_prompt.build_combined_prompt_org(instruction, wiki_target, mentions, "ファルモ", True)
    off = wiki_prompt.build_combined_prompt_org(instruction, wiki_target, mentions, "ファルモ", False)
    assert "web検索ツールが利用可能" in on
    assert "web検索は行わず" in off
    assert "ファルモ" in on  # mention JSON 同梱


# ---------------------------------------------------------------------------
# wiki_index — Orgs セクション
# ---------------------------------------------------------------------------
def test_index_renders_orgs_section(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    (wiki / "orgs").mkdir(parents=True)
    (wiki / "orgs" / "ファルモ.md").write_text(
        "---\ntitle: ファルモ\nslug: ファルモ\nmention_count: 11\n---\n\n# ファルモ\n",
        encoding="utf-8",
    )
    (wiki / "orgs" / "メディパル.md").write_text(
        "---\ntitle: メディパル\nslug: メディパル\nmention_count: 1\n---\n\n# メディパル\n",
        encoding="utf-8",
    )
    wiki_index.regenerate_index(wiki, tmp_path)
    text = (wiki / "index.md").read_text(encoding="utf-8")
    assert "## Orgs（組織）" in text
    assert "[ファルモ](./orgs/ファルモ.md)" in text
    # mention_count 降順（ファルモ 11 が メディパル 1 より上）
    assert text.index("ファルモ.md") < text.index("メディパル.md")


# ---------------------------------------------------------------------------
# enqueue.py — org kind（隔離 HOME）
# ---------------------------------------------------------------------------
def _run_enqueue(home: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return subprocess.run(
        [sys.executable, str(ENQUEUE_SCRIPT), *args],
        capture_output=True, text=True, env=env,
    )


def _read_queue(home: Path) -> list[dict]:
    q = home / ".local" / "share" / "episodic" / "state" / "ingest-queue.jsonl"
    if not q.exists():
        return []
    return [json.loads(ln) for ln in q.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_enqueue_org_writes_entry(isolated_home, fake_raw, tmp_path: Path) -> None:
    r = _run_enqueue(
        tmp_path, str(fake_raw), "--kind", "org", "--name", "ファルモ",
        "--slug", "ファルモ", "--source-kind", "minutes", "--category", "company",
        "--aliases", "株式会社ファルモ", "--context", "テスト",
    )
    assert r.returncode == 0, r.stderr
    entries = _read_queue(tmp_path)
    org_entries = [e for e in entries if e.get("kind") == "org"]
    assert len(org_entries) == 1
    e = org_entries[0]
    assert e["slug"] == "ファルモ"
    assert e["category"] == "company"
    assert e["source_kind"] == "minutes"
    assert e["aliases"] == ["株式会社ファルモ"]


def test_enqueue_org_requires_slug(isolated_home, fake_raw, tmp_path: Path) -> None:
    r = _run_enqueue(
        tmp_path, str(fake_raw), "--kind", "org", "--name", "ファルモ",
        "--source-kind", "minutes",  # --slug 欠落
    )
    assert r.returncode == 3


# ---------------------------------------------------------------------------
# セキュリティ回帰: Codex 由来 source_raw のパストラバーサル
# ---------------------------------------------------------------------------
def test_dispatch_rejects_source_raw_outside_memories_root(tmp_path: Path) -> None:
    mem = tmp_path / "mem"
    raw_path = mem / "raw" / "minutes" / "2026-05-20" / "x.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("body")
    legit = mem / "raw" / "minutes" / "2026-05-20" / "y.md"
    payload = {
        "people": [
            {"name": "悪意", "slug": "evil", "source_raw": "/etc/passwd", "source_kind": "minutes"},
            {"name": "正規", "slug": "ok", "source_raw": str(legit), "source_kind": "minutes"},
        ]
    }
    cap = tmp_path / "cap.log"
    cap.write_text(
        f"<<<PEOPLE_JSON_BEGIN>>>\n{json.dumps(payload, ensure_ascii=False)}\n<<<PEOPLE_JSON_END>>>"
    )
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check, timeout):  # noqa: ARG001
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch.object(wiki_dispatch.subprocess, "run", side_effect=fake_run):
        parsed_ok, appended, errors = wiki_dispatch.dispatch_person_enqueues_from_capture(
            cap, raw_path=raw_path, source_kind="minutes", enqueue_script=tmp_path / "enqueue.py",
        )
    # memories root 外の source_raw（/etc/passwd）は enqueue されない
    assert appended == 1
    slugs = [c[c.index("--slug") + 1] for c in calls]
    assert slugs == ["ok"]
