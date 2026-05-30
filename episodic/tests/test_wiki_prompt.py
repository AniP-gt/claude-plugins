"""lib/wiki_prompt.py のテスト。

カバレッジ:
  - テンプレ展開 ({project} / {wiki_target} / {slug})
  - 旧版 (supersedes) 同梱
  - wiki_target 未存在 → "まだ存在しません" メッセージ
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_prompt  # noqa: E402


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestBuildCombinedPromptBatch:
    def test_template_expansion(self, tmp_path: Path) -> None:
        instruction = _write(
            tmp_path / "i.md",
            "project={project}\nwiki_target={wiki_target}\nproject_wiki={project_wiki}\n",
        )
        raw = _write(tmp_path / "raw.md", "---\nproject: P1\n---\nbody\n")
        wiki_target = tmp_path / "wiki" / "projects" / "P1.md"

        text = wiki_prompt.build_combined_prompt_batch(
            instruction, wiki_target, [raw], "session", project="P1"
        )
        assert "project=P1" in text
        assert f"wiki_target={wiki_target}" in text
        assert f"project_wiki={wiki_target}" in text
        # raw 本体も同梱
        assert "<<<RAW_BEGIN>>>" in text
        assert "body" in text
        assert "<<<RAW_END>>>" in text

    def test_subagent_placeholders_expand(self, tmp_path: Path) -> None:
        instruction = _write(
            tmp_path / "i.md",
            "raw_count={raw_count}\nhint={subagent_hint}\n",
        )
        raw1 = _write(tmp_path / "r1.md", "---\nkind: minutes\n---\na\n")
        raw2 = _write(tmp_path / "r2.md", "---\nkind: diary\n---\nb\n")
        raw3 = _write(tmp_path / "r3.md", "---\nkind: minutes\n---\nc\n")
        text = wiki_prompt.build_combined_prompt_batch(
            instruction, tmp_path / "w.md", [raw1, raw2, raw3], "people_extract"
        )
        # raw_count が展開され、プレースホルダが残らない
        assert "raw_count=3" in text
        assert "{subagent_hint}" not in text
        assert "subagent" in text  # 3 件 → subagent 起動を促すヒント
        # 各 Raw の実 kind が source_kind: として混在表記される
        assert "source_kind: minutes" in text
        assert "source_kind: diary" in text

    def test_subagent_hint_small_raw_count(self, tmp_path: Path) -> None:
        instruction = _write(tmp_path / "i.md", "hint={subagent_hint}\n")
        raw = _write(tmp_path / "r.md", "---\nproject: P\n---\nx\n")
        text = wiki_prompt.build_combined_prompt_batch(
            instruction, tmp_path / "w.md", [raw], "session", project="P"
        )
        # 少数なので lead 単独を促す
        assert "lead 単独" in text

    def test_supersedes_attached(self, tmp_path: Path) -> None:
        old_raw = _write(tmp_path / "old.md", "old body")
        instruction = _write(tmp_path / "i.md", "instr\n")
        raw = _write(
            tmp_path / "new.md",
            f"---\nproject: P1\nsupersedes: {old_raw}\n---\nnew body\n",
        )
        text = wiki_prompt.build_combined_prompt_batch(
            instruction, tmp_path / "wiki.md", [raw], "session", project="P1"
        )
        assert "<<<REVISION_BEGIN>>>" in text
        assert "old body" in text
        assert "<<<REVISION_END>>>" in text
        # 新 raw も同梱
        assert "new body" in text

    def test_wiki_target_absent(self, tmp_path: Path) -> None:
        instruction = _write(tmp_path / "i.md", "instr\n")
        raw = _write(tmp_path / "raw.md", "body\n")
        text = wiki_prompt.build_combined_prompt_batch(
            instruction, tmp_path / "absent.md", [raw], "web", project=""
        )
        assert "まだ存在しません" in text


class TestBuildCombinedPromptPerson:
    def test_template_expansion_person(self, tmp_path: Path) -> None:
        instruction = _write(
            tmp_path / "i.md", "wiki_target={wiki_target}\nslug={slug}\n"
        )
        wiki_target = tmp_path / "wiki" / "people" / "yamada.md"
        mentions = [
            {"name": "山田", "slug": "yamada", "context": "ctx1", "source_kind": "minutes"},
            {"name": "山田", "slug": "yamada", "context": "ctx2", "source_kind": "diary"},
        ]
        text = wiki_prompt.build_combined_prompt_person(
            instruction, wiki_target, mentions, "yamada"
        )
        assert f"wiki_target={wiki_target}" in text
        assert "slug=yamada" in text
        assert "<<<MENTION_BEGIN>>>" in text
        assert "ctx1" in text
        assert "ctx2" in text

    def test_subagent_placeholders_expand_person(self, tmp_path: Path) -> None:
        instruction = _write(
            tmp_path / "i.md", "raw_count={raw_count}\nhint={subagent_hint}\n"
        )
        mentions = [
            {"name": "山田", "slug": "yamada", "context": f"c{i}", "source_kind": "minutes"}
            for i in range(5)
        ]
        text = wiki_prompt.build_combined_prompt_person(
            instruction, tmp_path / "w.md", mentions, "yamada"
        )
        assert "raw_count=5" in text
        assert "{subagent_hint}" not in text
        assert "言及" in text

    def test_wiki_target_absent_person(self, tmp_path: Path) -> None:
        instruction = _write(tmp_path / "i.md", "x\n")
        text = wiki_prompt.build_combined_prompt_person(
            instruction, tmp_path / "absent.md", [], "slug-x"
        )
        assert "まだ存在しません" in text
