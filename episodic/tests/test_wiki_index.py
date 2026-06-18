"""lib/wiki_index.py のテスト。

projects / references / minutes / diary / people の統合再生成と
enforce_source_count の動作を検証する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_index  # noqa: E402


def _make_md(p: Path, body: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


class TestEnforceSourceCount:
    def test_existing_field_overwritten(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("---\ntitle: T\nsource_count: 99\n---\nbody\n")
        wiki_index.enforce_source_count(f, 5)
        text = f.read_text()
        assert "source_count: 5" in text
        assert "source_count: 99" not in text

    def test_missing_field_appended(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("---\ntitle: T\n---\nbody\n")
        wiki_index.enforce_source_count(f, 3)
        assert "source_count: 3" in f.read_text()

    def test_no_frontmatter_no_change(self, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("body only\n")
        wiki_index.enforce_source_count(f, 9)
        assert f.read_text() == "body only\n"


class TestRegenerateIndex:
    def test_full_integration(self, tmp_path: Path) -> None:
        memories = tmp_path / "memories"
        wiki = memories / "wiki"
        # projects
        _make_md(wiki / "projects" / "alpha.md")
        _make_md(wiki / "projects" / "beta.md")
        # references
        _make_md(wiki / "references.md", "---\ntitle: ref\nsource_count: 0\n---\nx")
        _make_md(memories / "raw" / "web" / "2026-05-15" / "a.md")
        _make_md(memories / "raw" / "web" / "2026-05-15" / "b.md")
        # minutes
        _make_md(memories / "raw" / "minutes" / "2026-05-15" / "m1.md")
        _make_md(memories / "raw" / "minutes" / "2026-05-15" / "m2.md")
        _make_md(wiki / "minutes" / "202605.md", "---\ntitle: m\nsource_count: 0\n---\nx")
        # diary
        _make_md(memories / "raw" / "diary" / "2026-05-15" / "d1.md")
        _make_md(wiki / "diary" / "202605.md", "---\ntitle: d\nsource_count: 0\n---\nx")
        # people with mention_count
        _make_md(
            wiki / "people" / "yamada.md",
            "---\ntitle: 山田\nmention_count: 5\n---\nbody",
        )
        _make_md(
            wiki / "people" / "suzuki.md",
            "---\ntitle: 鈴木\nmention_count: 10\n---\nbody",
        )

        index_path = wiki_index.regenerate_index(wiki, memories)
        assert index_path == wiki / "index.md"
        text = index_path.read_text()

        # Sessions
        assert "計 2 プロジェクト" in text
        assert "- [alpha]" in text
        assert "- [beta]" in text
        # References (web count = 2)
        assert "Raw 計 2 件" in text
        assert "[References Library]" in text
        # Minutes (raw count = 2)
        assert "Raw 計 2 件、codex 統合済み" in text or "計 2 件" in text
        # Diary (raw count = 1)
        # People — mention_count 降順で suzuki が yamada より先
        suzuki_pos = text.find("[suzuki]")
        yamada_pos = text.find("[yamada]")
        assert suzuki_pos != -1 and yamada_pos != -1
        assert suzuki_pos < yamada_pos
        assert "言及 10 件" in text
        assert "言及 5 件" in text

        # enforce_source_count が動いている
        ref_text = (wiki / "references.md").read_text()
        assert "source_count: 2" in ref_text
        minutes_text = (wiki / "minutes" / "202605.md").read_text()
        assert "source_count: 2" in minutes_text
        diary_text = (wiki / "diary" / "202605.md").read_text()
        assert "source_count: 1" in diary_text

    def test_empty_dirs(self, tmp_path: Path) -> None:
        memories = tmp_path / "memories"
        wiki = memories / "wiki"
        wiki.mkdir(parents=True)
        index_path = wiki_index.regenerate_index(wiki, memories)
        text = index_path.read_text()
        assert "Wiki Index" in text
        # 全部 0 件 / 未統合メッセージ
        assert "計 0 プロジェクト" in text
        assert "まだ統合されていません" in text
