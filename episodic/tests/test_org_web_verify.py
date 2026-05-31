"""wiki/org_web_verify.py のテスト（codex をモックし実 web 検索は行わない）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

_MOD_PATH = REPO_ROOT / "wiki" / "org_web_verify.py"
_spec = importlib.util.spec_from_file_location("org_web_verify_mod", _MOD_PATH)
owv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(owv)


_ORG_TEMPLATE = """---
title: ファルモ
slug: ファルモ
aliases: [ファルモクラウド]
kind: org
category: company
members: [河本]
website:
web_status: unchecked
web_checked_at: {checked}
status: active
mention_count: 1
updated_at: 2026-05-31T09:17:37+09:00
---

# ファルモ

## 概要

医薬品データベースを扱う会社として議事録に頻出する。

## 関係者

- [河本さん](../people/河本.md) — 関係者
"""


def _write_org(tmp_path: Path, checked: str = "null") -> Path:
    p = tmp_path / "ファルモ.md"
    p.write_text(_ORG_TEMPLATE.format(checked=checked), encoding="utf-8")
    return p


def test_verified_patches_frontmatter_and_overview(tmp_path: Path) -> None:
    p = _write_org(tmp_path)

    def fake_search(title, aliases, category):
        assert title == "ファルモ"
        return {"found": True, "official_name": "株式会社ファルモ",
                "website": "https://pharumo.example/", "summary": "医薬品DB事業の会社"}

    status = owv.verify_org_file(p, fake_search, "2026-05-31")
    assert status == "verified"
    text = p.read_text(encoding="utf-8")
    front = owv.fm.parse(p)
    assert front["website"] == "https://pharumo.example/"
    assert front["web_status"] == "verified"
    assert front["web_checked_at"] == "2026-05-31"
    assert "公式情報（web 裏取り 2026-05-31）: 医薬品DB事業の会社" in text
    # 概要見出し直後に挿入されている
    assert text.index("## 概要") < text.index("公式情報（web 裏取り")


def test_not_found_records_status(tmp_path: Path) -> None:
    p = _write_org(tmp_path)
    status = owv.verify_org_file(
        p, lambda t, a, c: {"found": False, "official_name": t, "website": "", "summary": ""},
        "2026-05-31",
    )
    assert status == "not_found"
    front = owv.fm.parse(p)
    assert front["web_status"] == "not_found"
    assert front["web_checked_at"] == "2026-05-31"
    assert (front.get("website") or "") == ""


def test_skip_when_already_checked(tmp_path: Path) -> None:
    p = _write_org(tmp_path, checked="2026-05-01")
    called = {"n": 0}

    def fake_search(t, a, c):
        called["n"] += 1
        return {"found": True, "official_name": t, "website": "x", "summary": "y"}

    status = owv.verify_org_file(p, fake_search, "2026-05-31")
    assert status == "skip"
    assert called["n"] == 0  # 検索関数は呼ばれない（冪等）


def test_force_rechecks(tmp_path: Path) -> None:
    p = _write_org(tmp_path, checked="2026-05-01")
    status = owv.verify_org_file(
        p, lambda t, a, c: {"found": True, "official_name": t,
                            "website": "https://x.example/", "summary": "s"},
        "2026-05-31", force=True,
    )
    assert status == "verified"
    assert owv.fm.parse(p)["web_checked_at"] == "2026-05-31"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    p = _write_org(tmp_path)
    before = p.read_text(encoding="utf-8")
    status = owv.verify_org_file(
        p, lambda t, a, c: {"found": True, "official_name": t,
                            "website": "https://x.example/", "summary": "s"},
        "2026-05-31", dry_run=True,
    )
    assert status == "verified"
    assert p.read_text(encoding="utf-8") == before  # 無変更


def test_error_when_search_returns_none(tmp_path: Path) -> None:
    p = _write_org(tmp_path)
    status = owv.verify_org_file(p, lambda t, a, c: None, "2026-05-31")
    assert status == "error"
    # 失敗時は web_checked_at を刻まない（次回再試行できる）
    assert (owv.fm.parse(p).get("web_checked_at") or "null") in owv._UNCHECKED


def test_update_overview_replaces_existing_line(tmp_path: Path) -> None:
    p = _write_org(tmp_path)
    owv.verify_org_file(
        p, lambda t, a, c: {"found": True, "official_name": t,
                            "website": "https://x.example/", "summary": "初回"},
        "2026-05-31",
    )
    # 2 回目（force）で公式情報行が重複せず置換される
    owv.verify_org_file(
        p, lambda t, a, c: {"found": True, "official_name": t,
                            "website": "https://x.example/", "summary": "二回目"},
        "2026-06-01", force=True,
    )
    text = p.read_text(encoding="utf-8")
    assert text.count("公式情報（web 裏取り") == 1
    assert "二回目" in text and "初回" not in text


def test_sanitizes_newlines_in_web_values(tmp_path: Path) -> None:
    """web 由来 website/summary の改行による frontmatter/markdown インジェクションを防ぐ。"""
    p = _write_org(tmp_path)
    owv.verify_org_file(
        p,
        lambda t, a, c: {
            "found": True,
            "official_name": t,
            "website": "https://x.example/\nmalicious_key: injected",
            "summary": "正規概要\n\n## 偽見出し\n本文",
        },
        "2026-05-31",
    )
    front = owv.fm.parse(p)
    # website の改行が除去され、frontmatter に新キーが注入されていない
    assert "malicious_key" not in front
    assert "\n" not in front["website"]
    # 本文 summary の改行が除去され、偽の見出し行が生成されていない
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").split("\n")]
    assert "## 偽見出し" not in lines
    assert any("公式情報" in ln and "正規概要" in ln for ln in lines)
