"""人物 / 組織 Wiki の重複ページを決定論的に検出・統合する保守 CLI。

LLM / web を一切使わない純 Python の保守ツール。`wiki/people/` または
`wiki/orgs/` 配下のページを走査し、以下のような重複を検出・統合する:

- 組織名プレフィックス変種（例「ファルモ河本」と「河本」）
- 敬称除去・NFC 正規化後の title / alias 集合の交差
- 同一 source_raw を共有しつつ正規化名が部分一致するページ

既定は dry-run（提案レポートのみ、書き込み / 削除なし）。`--apply` 指定時のみ
canonical ページを統合内容で上書きし、非 canonical ページを削除する。

CLI:
    python -m lib.wiki_reconcile [--memories-dir PATH] [--kind {people,orgs,both}]
        [--apply] [--canonical-strategy {shortest-name,most-mentions}]
        [--org-prefixes 語,語,...] [--now ISO8601]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# 既定の組織プレフィックス語。`--org-prefixes` で追加できる。
DEFAULT_ORG_PREFIXES: tuple[str, ...] = (
    "ファルモ",
    "メディパル",
    "アルフレッサ",
    "スズケン",
    "東邦",
)

# 敬称（接尾辞）。正規化名の比較時に除去する。
_HONORIFICS: tuple[str, ...] = ("さん", "ちゃん", "くん", "君", "様", "さま", "氏", "先生", "殿")

# 言及の時系列行: `- **YYYY-MM-DD** — <ctx> ([kind](../../raw/kind/DATE/basename.md))`
_TIMELINE_LINE = re.compile(
    r"^\s*-\s+\*\*(?P<date>\d{4}-\d{2}-\d{2})\*\*\s*[—-]\s*(?P<ctx>.*?)\s*"
    r"\(\[[^\]]*\]\((?P<raw>[^)]+)\)\)\s*$"
)

# frontmatter の aliases: `[a, b, c]` 形式（frontmatter.py が文字列で返す）。
_ALIASES_LINE = re.compile(r"^\[(?P<items>.*)\]$")


@dataclass
class TimelineItem:
    """「言及の時系列」の 1 行を表す。"""

    date: str
    ctx: str
    raw: str
    # 元行の kind ラベル（minutes / diary 等）。再構築時に保持する。
    line: str


@dataclass
class Page:
    """人物 / 組織 Wiki ページ 1 件のパース結果。"""

    path: Path
    slug: str
    title: str
    aliases: list[str]
    mention_count: int
    first_seen: str
    last_seen: str
    overview: str
    relations: list[str]
    timeline: list[TimelineItem] = field(default_factory=list)


@dataclass
class MergedPage:
    """統合後のページ内容。"""

    slug: str
    title: str
    aliases: list[str]
    mention_count: int
    first_seen: str
    last_seen: str
    overview: str
    relations: list[str]
    timeline: list[TimelineItem]
    updated_at: str


# --------------------------------------------------------------------------
# 正規化ヘルパ
# --------------------------------------------------------------------------
def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def strip_honorifics(name: str) -> str:
    """敬称（さん / 先生 / 様 / 氏 等）を末尾から除去し NFC 正規化する。"""
    s = _nfc(name)
    changed = True
    while changed:
        changed = False
        for h in _HONORIFICS:
            if s.endswith(h) and len(s) > len(h):
                s = s[: -len(h)]
                changed = True
    return s


def _parse_aliases(raw: str) -> list[str]:
    """frontmatter の aliases 文字列（`[a, b]`）を list に変換する。"""
    raw = raw.strip()
    m = _ALIASES_LINE.match(raw)
    if not m:
        return []
    items = m.group("items").strip()
    if not items:
        return []
    out: list[str] = []
    for part in items.split(","):
        v = part.strip().strip("'\"").strip()
        if v:
            out.append(v)
    return out


# --------------------------------------------------------------------------
# ページパース
# --------------------------------------------------------------------------
def _split_sections(body: str) -> dict[str, list[str]]:
    """本文を `## 見出し` ごとに分割し、見出し名→行リストの dict を返す。"""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.split("\n"):
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _section_match(sections: dict[str, list[str]], *keywords: str) -> list[str]:
    """見出し名に keyword のいずれかを含むセクションの行リストを返す。"""
    for name, lines in sections.items():
        if any(kw in name for kw in keywords):
            return lines
    return []


def parse_page(path: Path) -> Page:
    """1 つの .md をパースして Page を返す。

    frontmatter（title / slug / aliases / mention_count / first_seen / last_seen）と
    「## 言及の時系列」「## 概要」「## 関係性・役割」を抽出する。
    """
    # frontmatter.parse を再利用（aliases / mention_count 等を文字列で取得）。
    from lib import frontmatter

    fm = frontmatter.parse(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    # frontmatter ブロックを除いた本文を取り出す。
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            body = text[end + len("\n---") :]

    sections = _split_sections(body)

    timeline: list[TimelineItem] = []
    for line in _section_match(sections, "言及の時系列", "言及", "時系列"):
        m = _TIMELINE_LINE.match(line)
        if not m:
            continue
        timeline.append(
            TimelineItem(
                date=m.group("date"),
                ctx=m.group("ctx").strip(),
                raw=m.group("raw").strip(),
                line=line.rstrip(),
            )
        )

    overview = "\n".join(
        ln for ln in _section_match(sections, "概要") if ln.strip()
    ).strip()
    relations = [
        ln.rstrip()
        for ln in _section_match(sections, "関係性", "役割")
        if ln.strip()
    ]

    slug = fm.get("slug") or path.stem
    title = fm.get("title") or slug

    try:
        mention_count = int(fm.get("mention_count", "0") or "0")
    except ValueError:
        mention_count = 0

    return Page(
        path=path,
        slug=slug,
        title=title,
        aliases=_parse_aliases(fm.get("aliases", "[]")),
        mention_count=mention_count,
        first_seen=fm.get("first_seen", "").strip(),
        last_seen=fm.get("last_seen", "").strip(),
        overview=overview,
        relations=relations,
        timeline=timeline,
    )


def load_pages(wiki_kind_dir: Path) -> list[Page]:
    """ディレクトリ配下の .md（ドットファイル除外）を Page にパースして返す。"""
    if not wiki_kind_dir.exists():
        return []
    pages: list[Page] = []
    for p in sorted(wiki_kind_dir.glob("*.md")):
        if p.name.startswith("."):
            continue
        pages.append(parse_page(p))
    return pages


# --------------------------------------------------------------------------
# 重複検出（union-find クラスタリング）
# --------------------------------------------------------------------------
class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _norm_name_set(page: Page) -> set[str]:
    """敬称除去・NFC 正規化した title + aliases の名前集合。"""
    names = {page.title, *page.aliases}
    out: set[str] = set()
    for n in names:
        s = strip_honorifics(n)
        if s:
            out.add(s)
    return out


def _is_prefix_variant(a: Page, b: Page, prefixes: list[str]) -> bool:
    """一方の slug が他方の slug の接尾辞で、差分が既知の組織プレフィックスに一致するか。"""
    sa, sb = _nfc(a.slug), _nfc(b.slug)
    if sa == sb:
        return False
    longer, shorter = (sa, sb) if len(sa) > len(sb) else (sb, sa)
    if not longer.endswith(shorter):
        return False
    diff = longer[: len(longer) - len(shorter)]
    return diff in {_nfc(p) for p in prefixes}


def _shares_source_with_partial_name(a: Page, b: Page) -> bool:
    """同一 source_raw を共有し、かつ正規化名が部分一致するか。"""
    raws_a = {item.raw for item in a.timeline}
    raws_b = {item.raw for item in b.timeline}
    if not (raws_a & raws_b):
        return False
    names_a = _norm_name_set(a)
    names_b = _norm_name_set(b)
    for na in names_a:
        for nb in names_b:
            if na and nb and (na in nb or nb in na):
                return True
    return False


def _is_duplicate(a: Page, b: Page, prefixes: list[str]) -> bool:
    """2 ページが重複候補か（プレフィックス変種 / 名前交差 / 共有 source）。"""
    if _is_prefix_variant(a, b, prefixes):
        return True
    if _norm_name_set(a) & _norm_name_set(b):
        return True
    if _shares_source_with_partial_name(a, b):
        return True
    return False


def detect_clusters(
    wiki_kind_dir: Path,
    org_prefixes: list[str] | None = None,
) -> list[list[Page]]:
    """ディレクトリ内の重複ページを union-find でクラスタ化する。

    Returns:
        メンバー数 2 以上のクラスタのリスト。各クラスタは Page のリスト
        （slug 昇順で安定ソート）。重複が無ければ空リスト。
    """
    prefixes = list(DEFAULT_ORG_PREFIXES) + list(org_prefixes or [])
    pages = load_pages(wiki_kind_dir)
    n = len(pages)
    uf = _UnionFind(n)

    # O(N^2) 全ペア比較を避けるため、_is_duplicate の各成立条件の「必要条件」で
    # ページをバケツ分けし、同一バケツに同居したペアのみ _is_duplicate で確定する。
    # どの重複ペアも必ずいずれかのバケツを共有するので結果は全ペア比較と一致し、
    # バケツ由来の余分な候補は _is_duplicate が確定弾きするため判定基準は不変。
    #   - name: 正規化名集合の交差（条件: _norm_name_set 交差）
    #   - slug: slug 本体 + 既知プレフィックス除去後の核（条件: prefix 変種）
    #   - raw:  timeline の source raw 共有（条件: source 共有 + 部分名一致の前提）
    prefix_nfc = [_nfc(p) for p in prefixes]
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, page in enumerate(pages):
        for name in _norm_name_set(page):
            buckets[("name", name)].append(idx)
        slug_nfc = _nfc(page.slug)
        cores = {slug_nfc}
        for p in prefix_nfc:
            if p and slug_nfc.startswith(p) and len(slug_nfc) > len(p):
                cores.add(slug_nfc[len(p):])
        for core in cores:
            buckets[("slug", core)].append(idx)
        for item in page.timeline:
            buckets[("raw", item.raw)].append(idx)

    candidate_pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        uniq = sorted(set(members))
        for a in range(len(uniq)):
            for b in range(a + 1, len(uniq)):
                candidate_pairs.add((uniq[a], uniq[b]))

    for i, j in candidate_pairs:
        if _is_duplicate(pages[i], pages[j], prefixes):
            uf.union(i, j)

    groups: dict[int, list[Page]] = {}
    for idx, page in enumerate(pages):
        groups.setdefault(uf.find(idx), []).append(page)

    clusters: list[list[Page]] = []
    for members in groups.values():
        if len(members) >= 2:
            clusters.append(sorted(members, key=lambda p: p.slug))
    clusters.sort(key=lambda c: c[0].slug)
    return clusters


# --------------------------------------------------------------------------
# canonical 選択
# --------------------------------------------------------------------------
def choose_canonical(cluster: list[Page], strategy: str = "shortest-name") -> Page:
    """クラスタ内で canonical ページを選ぶ。

    - shortest-name: 最短の slug（＝組織プレフィックスを含まない素の人名）。
      同長なら slug 昇順で安定化。
    - most-mentions: mention_count 最大。同数なら slug 昇順で安定化。
    """
    if strategy == "most-mentions":
        return min(cluster, key=lambda p: (-p.mention_count, p.slug))
    # 既定: shortest-name
    return min(cluster, key=lambda p: (len(p.slug), p.slug))


# --------------------------------------------------------------------------
# 統合
# --------------------------------------------------------------------------
def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def merge_cluster(cluster: list[Page], canonical: Page, now: str) -> MergedPage:
    """クラスタを canonical に統合した MergedPage を構築する。

    - aliases = 全メンバーの aliases ∪ 非 canonical の title / slug。重複排除。
    - 時系列 = 全メンバーの行を (date, raw) で重複排除し日付降順マージ。
    - mention_count = マージ後の時系列項目数。
    - first_seen / last_seen = 全日付の最小 / 最大。
    - 概要 / 関係性 = 行単位で重複排除して結合（情報を失わない）。
    """
    others = [p for p in cluster if p.slug != canonical.slug]

    # aliases union（敬称・プレフィックス変種も alias 化）
    aliases: list[str] = list(canonical.aliases)
    for p in cluster:
        aliases.extend(p.aliases)
    for p in others:
        aliases.append(p.title)
        aliases.append(p.slug)
    # canonical 自身の title / slug は alias に含めない
    aliases = [a for a in aliases if a not in (canonical.title, canonical.slug)]
    aliases = _dedup_preserve_order([_nfc(a) for a in aliases if a.strip()])

    # 時系列 (date, raw) で重複排除し降順マージ
    by_key: dict[tuple[str, str], TimelineItem] = {}
    for p in cluster:
        for item in p.timeline:
            key = (item.date, item.raw)
            # 既存があれば「より新しい / 情報量が多い」方を優先せず、最初に出たものを維持
            if key not in by_key:
                by_key[key] = item
    timeline = sorted(by_key.values(), key=lambda it: (it.date, it.raw), reverse=True)

    # 日付集合から first / last_seen を再計算（frontmatter の日付も補完に使う）
    dates: list[str] = [it.date for it in timeline]
    for p in cluster:
        if p.first_seen:
            dates.append(p.first_seen)
        if p.last_seen:
            dates.append(p.last_seen)
    dates = [d for d in dates if d]
    first_seen = min(dates) if dates else canonical.first_seen
    last_seen = max(dates) if dates else canonical.last_seen

    # 概要: canonical を先頭に、全メンバーの概要行を行単位で dedup 結合
    overview_lines: list[str] = []
    for p in [canonical, *others]:
        for ln in p.overview.split("\n"):
            if ln.strip():
                overview_lines.append(ln.rstrip())
    overview = "\n".join(_dedup_preserve_order(overview_lines))

    # 関係性: 同様に行単位 dedup 結合
    relation_lines: list[str] = []
    for p in [canonical, *others]:
        relation_lines.extend(p.relations)
    relations = _dedup_preserve_order([ln.rstrip() for ln in relation_lines if ln.strip()])

    return MergedPage(
        slug=canonical.slug,
        title=canonical.title,
        aliases=aliases,
        mention_count=len(timeline),
        first_seen=first_seen,
        last_seen=last_seen,
        overview=overview,
        relations=relations,
        timeline=timeline,
        updated_at=now,
    )


def render_page(merged: MergedPage) -> str:
    """MergedPage を人物 Wiki の Markdown テキストに直列化する。"""
    aliases_str = "[" + ", ".join(merged.aliases) + "]"
    lines: list[str] = [
        "---",
        f"title: {merged.title}",
        f"slug: {merged.slug}",
        f"aliases: {aliases_str}",
        "status: active",
        f"first_seen: {merged.first_seen}",
        f"last_seen: {merged.last_seen}",
        f"mention_count: {merged.mention_count}",
        f"updated_at: {merged.updated_at}",
        "---",
        "",
        f"# {merged.title}",
        "",
        "## 概要",
        "",
        merged.overview if merged.overview else "観察中。",
        "",
        "## 言及の時系列（新しい順）",
        "",
    ]
    for item in merged.timeline:
        lines.append(item.line)
    lines.append("")
    lines.append("## 関係性・役割")
    lines.append("")
    lines.extend(merged.relations)
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# レポート / 適用
# --------------------------------------------------------------------------
def _kind_dirs(wiki_dir: Path, kind: str) -> list[tuple[str, Path]]:
    mapping = {
        "people": [("people", wiki_dir / "people")],
        "orgs": [("orgs", wiki_dir / "orgs")],
        "both": [("people", wiki_dir / "people"), ("orgs", wiki_dir / "orgs")],
    }
    return mapping[kind]


def reconcile(
    wiki_dir: Path,
    kind: str,
    *,
    apply: bool,
    strategy: str,
    org_prefixes: list[str] | None,
    now: str,
    out=sys.stdout,
) -> int:
    """検出・統合の本体。dry-run はレポートのみ、apply 時のみ実書き込み / 削除。"""
    total_clusters = 0
    for kind_label, kind_dir in _kind_dirs(wiki_dir, kind):
        clusters = detect_clusters(kind_dir, org_prefixes=org_prefixes)
        if not clusters:
            print(f"[{kind_label}] 重複候補なし ({kind_dir})", file=out)
            continue
        for cluster in clusters:
            total_clusters += 1
            canonical = choose_canonical(cluster, strategy=strategy)
            merged = merge_cluster(cluster, canonical, now=now)
            others = [p for p in cluster if p.slug != canonical.slug]

            print(f"[{kind_label}] クラスタ検出:", file=out)
            print(f"  canonical ← {canonical.slug}", file=out)
            print(
                f"  統合元: {[p.slug for p in others]}",
                file=out,
            )
            print(f"  マージ後 mention_count: {merged.mention_count}", file=out)
            print(
                f"  削除予定ファイル: {[str(p.path) for p in others]}",
                file=out,
            )

            if apply:
                canonical.path.write_text(render_page(merged), encoding="utf-8")
                for p in others:
                    try:
                        p.path.unlink()
                    except OSError as e:
                        print(f"  削除失敗 {p.path}: {e}", file=out)
                print(
                    f"  実施: {canonical.path} を上書き、{len(others)} ファイルを削除",
                    file=out,
                )
            else:
                print("  (dry-run: 書き込み / 削除は行いません)", file=out)

    if total_clusters == 0:
        print("統合対象の重複クラスタはありませんでした。", file=out)
    else:
        mode = "適用済み" if apply else "dry-run（--apply で実行）"
        print(f"検出クラスタ数: {total_clusters} / モード: {mode}", file=out)
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "人物 / 組織 Wiki の重複ページを決定論的に検出・統合する保守 CLI。"
            "既定は dry-run（提案レポートのみ）。--apply 指定時のみ実書き込み / 削除を行う。"
        )
    )
    parser.add_argument(
        "--memories-dir",
        default=os.environ.get("MEMORIES_DIR", "/Volumes/memory"),
        help="memories ルート（既定: env MEMORIES_DIR or /Volumes/memory）。配下の wiki/ を対象にする",
    )
    parser.add_argument(
        "--kind",
        choices=("people", "orgs", "both"),
        default="both",
        help="対象種別（people→wiki/people、orgs→wiki/orgs、both=両方。既定 both）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実書き込み / 削除を行う。未指定時は dry-run（提案レポートのみ、副作用なし）",
    )
    parser.add_argument(
        "--canonical-strategy",
        choices=("shortest-name", "most-mentions"),
        default="shortest-name",
        help="canonical 選択戦略（shortest-name=最短 slug、most-mentions=言及最多。既定 shortest-name）",
    )
    parser.add_argument(
        "--org-prefixes",
        default="",
        help="組織プレフィックス語の追加（カンマ区切り）。既定リストに加算する",
    )
    parser.add_argument(
        "--now",
        default=None,
        help="updated_at に書き込む ISO8601 文字列（テスト用に注入可能。既定は現在時刻）",
    )
    args = parser.parse_args(argv)

    extra_prefixes = [p.strip() for p in args.org_prefixes.split(",") if p.strip()]
    now = args.now or datetime.now().astimezone().isoformat(timespec="seconds")
    wiki_dir = Path(args.memories_dir) / "wiki"

    return reconcile(
        wiki_dir,
        args.kind,
        apply=args.apply,
        strategy=args.canonical_strategy,
        org_prefixes=extra_prefixes,
        now=now,
    )


if __name__ == "__main__":
    sys.exit(main())
