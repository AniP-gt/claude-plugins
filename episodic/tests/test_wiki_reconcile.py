"""lib/wiki_reconcile.py のテスト。

人物/組織 Wiki の重複検出・統合（決定論的・LLM/web 不使用）を検証する。
合成の重複ファイルを tmp_path に作り、検出ヒューリスティック・canonical 選択・
統合結果（aliases union / 時系列 dedup＆降順 / mention_count 整合 / first_last_seen 再計算）・
dry-run と --apply の挙動・非重複ファイルの非干渉を確認する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import wiki_reconcile  # noqa: E402


FIXED_NOW = "2026-05-31T12:00:00+09:00"


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _person_md(
    *,
    title: str,
    slug: str,
    aliases: str = "[]",
    first_seen: str = "2026-05-20",
    last_seen: str = "2026-05-20",
    mention_count: int = 1,
    overview: str = "観察中。",
    timeline: list[str] | None = None,
    relations: list[str] | None = None,
) -> str:
    """人物ページの合成テキストを組み立てる（codex-instruction-person の構造準拠）。"""
    timeline = timeline if timeline is not None else []
    relations = relations if relations is not None else []
    tl = "\n".join(timeline)
    rel = "\n".join(relations)
    return (
        "---\n"
        f"title: {title}\n"
        f"slug: {slug}\n"
        f"aliases: {aliases}\n"
        "status: active\n"
        f"first_seen: {first_seen}\n"
        f"last_seen: {last_seen}\n"
        f"mention_count: {mention_count}\n"
        "updated_at: 2026-05-20T00:00:00+09:00\n"
        "---\n\n"
        f"# {title}\n\n"
        "## 概要\n\n"
        f"{overview}\n\n"
        "## 言及の時系列（新しい順）\n\n"
        f"{tl}\n\n"
        "## 関係性・役割\n\n"
        f"{rel}\n"
    )


def _tl(date: str, ctx: str, kind: str, basename: str) -> str:
    return (
        f"- **{date}** — {ctx} "
        f"([{kind}](../../raw/{kind}/{date}/{basename}.md))"
    )


@pytest.fixture
def people_dir(tmp_path: Path) -> Path:
    d = tmp_path / "wiki" / "people"
    d.mkdir(parents=True)
    return d


# --------------------------------------------------------------------------
# 検出: 組織プレフィックス変種
# --------------------------------------------------------------------------
class TestDetectPrefixVariant:
    def test_prefix_variant_clusters(self, people_dir: Path) -> None:
        _write(
            people_dir / "ファルモ河本.md",
            _person_md(
                title="ファルモ河本",
                slug="ファルモ河本",
                aliases="[河本さん]",
                timeline=[_tl("2026-05-20", "1on1 に参加した", "minutes", "105626_1on1")],
                relations=["- 1on1 の相手として登場"],
            ),
        )
        _write(
            people_dir / "河本.md",
            _person_md(
                title="河本さん",
                slug="河本",
                aliases="[河本さん]",
                timeline=[_tl("2026-05-20", "Rollbar の方針確認先", "minutes", "114651_1on1b")],
                relations=["- ファルモの関係者"],
            ),
        )
        clusters = wiki_reconcile.detect_clusters(people_dir)
        assert len(clusters) == 1
        slugs = {m.slug for m in clusters[0]}
        assert slugs == {"ファルモ河本", "河本"}


# --------------------------------------------------------------------------
# 検出: alias / title 集合の交差（敬称除去・NFC 正規化）
# --------------------------------------------------------------------------
class TestDetectAliasIntersection:
    def test_alias_intersection_clusters(self, people_dir: Path) -> None:
        # slug は接尾辞関係になく、プレフィックスも共有しない。
        # ただし alias「田中」と title「田中さん」が敬称除去後に交差する。
        _write(
            people_dir / "tanaka1.md",
            _person_md(
                title="田中太郎",
                slug="tanaka1",
                aliases="[田中]",
                timeline=[_tl("2026-05-21", "会議に参加", "minutes", "aaa")],
            ),
        )
        _write(
            people_dir / "tanaka2.md",
            _person_md(
                title="田中さん",
                slug="tanaka2",
                aliases="[]",
                timeline=[_tl("2026-05-22", "別の会議", "minutes", "bbb")],
            ),
        )
        clusters = wiki_reconcile.detect_clusters(people_dir)
        assert len(clusters) == 1
        assert {m.slug for m in clusters[0]} == {"tanaka1", "tanaka2"}


# --------------------------------------------------------------------------
# 検出: 共有 source_raw + 正規化名の部分一致
# --------------------------------------------------------------------------
class TestDetectSharedSource:
    def test_shared_source_raw_clusters(self, people_dir: Path) -> None:
        shared = _tl("2026-05-23", "同じ議事録に登場", "minutes", "shared_minutes")
        # 同一 source_raw を共有し、正規化名が部分一致（「佐藤」が「佐藤次郎」の部分文字列）。
        # slug は接尾辞関係になく、プレフィックス変種でもないので shared-source 経路でのみ検出される。
        _write(
            people_dir / "satou.md",
            _person_md(
                title="佐藤",
                slug="satou",
                aliases="[]",
                timeline=[shared],
            ),
        )
        _write(
            people_dir / "satou-jirou.md",
            _person_md(
                title="佐藤次郎",
                slug="satou-jirou",
                aliases="[]",
                timeline=[shared],
            ),
        )
        clusters = wiki_reconcile.detect_clusters(people_dir)
        assert len(clusters) == 1
        assert {m.slug for m in clusters[0]} == {"satou", "satou-jirou"}


# --------------------------------------------------------------------------
# 非重複: 別人はクラスタ化されない
# --------------------------------------------------------------------------
class TestNonDuplicate:
    def test_distinct_people_not_clustered(self, people_dir: Path) -> None:
        _write(
            people_dir / "yamada.md",
            _person_md(
                title="山田",
                slug="yamada",
                timeline=[_tl("2026-05-20", "A の会議", "minutes", "raw_a")],
            ),
        )
        _write(
            people_dir / "suzuki.md",
            _person_md(
                title="鈴木",
                slug="suzuki",
                timeline=[_tl("2026-05-21", "B の会議", "minutes", "raw_b")],
            ),
        )
        clusters = wiki_reconcile.detect_clusters(people_dir)
        # 重複候補なし → クラスタ（メンバー2 以上の集合）は 0
        assert clusters == []


# --------------------------------------------------------------------------
# canonical 選択
# --------------------------------------------------------------------------
class TestCanonicalSelection:
    def test_shortest_name_picks_shorter_slug(self, people_dir: Path) -> None:
        _write(people_dir / "ファルモ河本.md", _person_md(title="ファルモ河本", slug="ファルモ河本", aliases="[河本さん]", mention_count=1, timeline=[_tl("2026-05-20", "x", "minutes", "a")]))
        _write(people_dir / "河本.md", _person_md(title="河本さん", slug="河本", aliases="[河本さん]", mention_count=5, timeline=[_tl("2026-05-20", "y", "minutes", "b")]))
        clusters = wiki_reconcile.detect_clusters(people_dir)
        canonical = wiki_reconcile.choose_canonical(clusters[0], strategy="shortest-name")
        assert canonical.slug == "河本"

    def test_most_mentions_picks_higher_count(self, people_dir: Path) -> None:
        _write(people_dir / "ファルモ河本.md", _person_md(title="ファルモ河本", slug="ファルモ河本", aliases="[河本さん]", mention_count=9, timeline=[_tl("2026-05-20", "x", "minutes", "a")]))
        _write(people_dir / "河本.md", _person_md(title="河本さん", slug="河本", aliases="[河本さん]", mention_count=2, timeline=[_tl("2026-05-20", "y", "minutes", "b")]))
        clusters = wiki_reconcile.detect_clusters(people_dir)
        canonical = wiki_reconcile.choose_canonical(clusters[0], strategy="most-mentions")
        assert canonical.slug == "ファルモ河本"


# --------------------------------------------------------------------------
# 統合: aliases union / 時系列 dedup＆降順 / mention_count / first_last_seen
# --------------------------------------------------------------------------
class TestMerge:
    def _setup_pair(self, people_dir: Path) -> None:
        # 共通の言及（同一 date + 同一 raw）を両ページに持たせ、dedup を確認する。
        common = _tl("2026-05-18", "在庫処理について話した", "minutes", "older")
        _write(
            people_dir / "ファルモ河本.md",
            _person_md(
                title="ファルモ河本",
                slug="ファルモ河本",
                aliases="[河本さん]",
                first_seen="2026-05-18",
                last_seen="2026-05-18",
                mention_count=1,
                overview="在庫処理について言及。",
                timeline=[common],
                relations=["- 1on1 の相手"],
            ),
        )
        _write(
            people_dir / "河本.md",
            _person_md(
                title="河本さん",
                slug="河本",
                aliases="[河本さん]",
                first_seen="2026-05-18",
                last_seen="2026-05-22",
                mention_count=2,
                overview="ファルモの関係者。",
                timeline=[
                    _tl("2026-05-22", "Rollbar の方針確認", "minutes", "newest"),
                    common,
                ],
                relations=["- ファルモの関係者", "- 1on1 の相手"],
            ),
        )

    def test_merge_fields(self, people_dir: Path) -> None:
        self._setup_pair(people_dir)
        clusters = wiki_reconcile.detect_clusters(people_dir)
        canonical = wiki_reconcile.choose_canonical(clusters[0], strategy="shortest-name")
        assert canonical.slug == "河本"
        merged = wiki_reconcile.merge_cluster(clusters[0], canonical, now=FIXED_NOW)

        # aliases union: 非 canonical の title/slug も alias 化（プレフィックス変種）。
        # canonical 自身の title/slug（河本さん / 河本）は alias から除外される。
        assert "ファルモ河本" in merged.aliases
        assert canonical.title not in merged.aliases
        assert canonical.slug not in merged.aliases
        # 時系列 dedup（common は date+raw が同一なので 1 件に）＆ 降順
        dates = [item.date for item in merged.timeline]
        assert dates == sorted(dates, reverse=True)
        keys = [(item.date, item.raw) for item in merged.timeline]
        assert len(keys) == len(set(keys)), "(date, raw) が重複している"
        # newest(05-22) と common(05-18) で 2 件
        assert len(merged.timeline) == 2
        # mention_count = 時系列項目数
        assert merged.mention_count == len(merged.timeline)
        assert merged.mention_count == 2
        # first/last_seen 再計算（全日付の min/max）
        assert merged.first_seen == "2026-05-18"
        assert merged.last_seen == "2026-05-22"
        # 概要・関係性は行単位で重複排除して結合（情報を失わない）
        assert "在庫処理について言及。" in merged.overview
        assert "ファルモの関係者。" in merged.overview
        rel_text = "\n".join(merged.relations)
        assert rel_text.count("1on1 の相手") == 1  # dedup
        assert "ファルモの関係者" in rel_text


# --------------------------------------------------------------------------
# dry-run / --apply のファイル副作用
# --------------------------------------------------------------------------
class TestApplyAndDryRun:
    def _setup_pair(self, people_dir: Path) -> None:
        _write(
            people_dir / "ファルモ河本.md",
            _person_md(
                title="ファルモ河本",
                slug="ファルモ河本",
                aliases="[河本さん]",
                mention_count=1,
                timeline=[_tl("2026-05-18", "古い言及", "minutes", "older")],
            ),
        )
        _write(
            people_dir / "河本.md",
            _person_md(
                title="河本さん",
                slug="河本",
                aliases="[河本さん]",
                mention_count=1,
                timeline=[_tl("2026-05-22", "新しい言及", "minutes", "newest")],
            ),
        )

    def test_dry_run_does_not_modify(self, tmp_path: Path, people_dir: Path) -> None:
        self._setup_pair(people_dir)
        before = {p.name: p.read_text(encoding="utf-8") for p in people_dir.glob("*.md")}
        rc = wiki_reconcile.main(
            ["--memories-dir", str(tmp_path), "--kind", "people", "--now", FIXED_NOW]
        )
        assert rc == 0
        after = {p.name: p.read_text(encoding="utf-8") for p in people_dir.glob("*.md")}
        assert before == after, "dry-run でファイルが変更された"
        assert set(p.name for p in people_dir.glob("*.md")) == {"ファルモ河本.md", "河本.md"}

    def test_apply_writes_canonical_and_deletes_others(
        self, tmp_path: Path, people_dir: Path
    ) -> None:
        self._setup_pair(people_dir)
        rc = wiki_reconcile.main(
            [
                "--memories-dir",
                str(tmp_path),
                "--kind",
                "people",
                "--apply",
                "--now",
                FIXED_NOW,
                "--canonical-strategy",
                "shortest-name",
            ]
        )
        assert rc == 0
        remaining = sorted(p.name for p in people_dir.glob("*.md"))
        # canonical（河本）のみ残り、非 canonical（ファルモ河本）は削除
        assert remaining == ["河本.md"]
        canonical_text = (people_dir / "河本.md").read_text(encoding="utf-8")
        # 時系列に両方の言及がマージされている
        assert "newest" in canonical_text
        assert "older" in canonical_text
        # mention_count = 2 に更新
        assert "mention_count: 2" in canonical_text
        # alias に変種が入る
        assert "ファルモ河本" in canonical_text
        # updated_at は注入した now
        assert FIXED_NOW in canonical_text

    def test_apply_does_not_touch_non_duplicates(
        self, tmp_path: Path, people_dir: Path
    ) -> None:
        self._setup_pair(people_dir)
        # 無関係な別人ページ
        unrelated = _person_md(
            title="渡辺",
            slug="watanabe",
            timeline=[_tl("2026-05-25", "独立した会議", "minutes", "watanabe_raw")],
        )
        _write(people_dir / "watanabe.md", unrelated)
        rc = wiki_reconcile.main(
            ["--memories-dir", str(tmp_path), "--kind", "people", "--apply", "--now", FIXED_NOW]
        )
        assert rc == 0
        assert (people_dir / "watanabe.md").exists()
        assert (people_dir / "watanabe.md").read_text(encoding="utf-8") == unrelated
