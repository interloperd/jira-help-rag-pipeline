"""Data quality inventory of the raw export, before the loader repairs anything.

Usage: python -m pipeline --inventory [path/to/export.json] [--out inventory.txt]

Each rule in RULES says what counts as bad for one field. Every page is listed with
its raw last_updated, its title and the flags it raised; the summary shows a count for
every rule, including the ones that found nothing (0 = clean field).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEBAB_FILE = re.compile(r"^[a-z0-9/-]+\.md$")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
WORD_COUNT_TOLERANCE = 0.15


def _frontmatter(body: str) -> dict[str, str]:
    m = FRONTMATTER.match(body or "")
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _headings(raw: Any) -> list[str] | None:
    if raw in (None, ""):
        return []
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return None
    return [str(h) for h in value] if isinstance(value, list) else None


class Page:
    """Raw record plus the values the rules compare against."""

    def __init__(self, raw: dict[str, Any], ids_by_url: dict[str, list[str]], id_counts: Counter):
        self.raw = raw
        self.body = raw.get("body_markdown") or ""
        self.fm = _frontmatter(self.body)
        self.headings = _headings(raw.get("headings"))
        self.body_h2 = re.findall(r"^## (.+?)\s*$", self.body, re.MULTILINE)
        self.h1 = re.findall(r"^# (.+?)\s*$", self.body, re.MULTILINE)
        text = FRONTMATTER.sub("", self.body, count=1)
        self.words = len(text.split())
        self.ids_by_url = ids_by_url
        self.id_counts = id_counts


# (field, flag, what counts as bad, test). A test returns True when the page is bad.
RULES: list[tuple[str, str, str, Callable[[Page], bool]]] = [
    ("doc_id", "DUPLICATE ID", "doc_id used by more than one page",
     lambda p: p.id_counts[p.raw.get("doc_id")] > 1),
    ("title", "MISSING TITLE", "title empty or null",
     lambda p: not p.raw.get("title")),
    ("title", "TITLE MISMATCH", "title differs from the frontmatter title or the # heading in the body",
     lambda p: bool(p.raw.get("title")) and (p.fm.get("title", p.raw["title"]) != p.raw["title"] or (p.h1 and p.h1[0] != p.raw["title"]))),
    ("last_updated", "MISSING DATE", "last_updated empty or null",
     lambda p: not p.raw.get("last_updated")),
    ("last_updated", "ODD DATE", "last_updated present but not in ISO format YYYY-MM-DD",
     lambda p: bool(p.raw.get("last_updated")) and not ISO_DATE.match(str(p.raw["last_updated"]))),
    ("last_updated", "DATE CONFLICT", "ISO last_updated differs from the last_updated in the body's frontmatter",
     lambda p: bool(p.raw.get("last_updated")) and bool(ISO_DATE.match(str(p.raw["last_updated"])))
     and bool(p.fm.get("last_updated")) and p.fm["last_updated"] != p.raw["last_updated"]),
    ("headings", "MISSING HEADING", "headings empty, null or unreadable",
     lambda p: not p.headings),
    ("headings", "DUPLICATE HEADING", "the same section heading appears twice on one page",
     lambda p: bool(p.headings) and len(set(p.headings)) != len(p.headings)),
    ("headings", "HEADING ANCHOR", "a heading carries anchor markup such as {#browse-projects}",
     lambda p: any("{#" in h for h in (p.headings or []))),
    ("headings", "HEADING MISMATCH", "headings field differs from the ## headings found in the body",
     lambda p: bool(p.headings) and p.headings != p.body_h2),
    ("url", "MISSING URL", "url empty or null",
     lambda p: not p.raw.get("url")),
    ("url", "DUPLICATE URL", "url shared with another page",
     lambda p: bool(p.raw.get("url")) and len(p.ids_by_url.get(p.raw["url"], [])) > 1),
    ("url", "URL MISMATCH", "url differs from source_url in the frontmatter",
     lambda p: bool(p.raw.get("url")) and p.fm.get("source_url", p.raw["url"]) != p.raw["url"]),
    ("body", "EMPTY BODY", "body_markdown empty",
     lambda p: not p.body.strip()),
    ("body", "NO FRONTMATTER", "body_markdown does not start with a --- frontmatter block",
     lambda p: bool(p.body.strip()) and not p.fm),
    ("source_file", "ODD FILENAME", "source_file not lowercase-kebab-case .md",
     lambda p: not KEBAB_FILE.match(str(p.raw.get("source_file") or ""))),
    ("word_count", "WORD COUNT OFF", f"word_count more than {int(WORD_COUNT_TOLERANCE * 100)}% away from the words in the body",
     lambda p: isinstance(p.raw.get("word_count"), int) and abs(p.words - p.raw["word_count"]) > WORD_COUNT_TOLERANCE * p.raw["word_count"]),
]


def detail(flag: str, p: Page) -> str:
    """Short evidence shown next to a flag."""
    r = p.raw
    return {
        "ODD DATE": f'{r.get("last_updated")}',
        "DATE CONFLICT": f'field {r.get("last_updated")} vs frontmatter {p.fm.get("last_updated")}',
        "MISSING DATE": f'frontmatter has {p.fm.get("last_updated") or "nothing"}',
        "DUPLICATE HEADING": ", ".join(sorted({h for h in p.headings or [] if (p.headings or []).count(h) > 1})),
        "HEADING ANCHOR": ", ".join(h for h in p.headings or [] if "{#" in h),
        "DUPLICATE URL": "shared with " + ", ".join(o for o in p.ids_by_url.get(r.get("url"), []) if o != r.get("doc_id")),
        "ODD FILENAME": str(r.get("source_file")),
        "WORD COUNT OFF": f'{r.get("word_count")} vs {p.words}',
    }.get(flag, "")


def run(path: str | Path) -> tuple[str, int]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    docs = data["docs"]
    ids_by_url: dict[str, list[str]] = {}
    for d in docs:
        ids_by_url.setdefault(d.get("url"), []).append(d.get("doc_id"))
    id_counts = Counter(d.get("doc_id") for d in docs)

    totals = Counter()
    rows, flagged_pages = [], 0
    for i, raw in enumerate(docs, 1):
        page = Page(raw, ids_by_url, id_counts)
        flags = [(flag, detail(flag, page)) for _, flag, _, test in RULES if test(page)]
        totals.update(f for f, _ in flags)
        flagged_pages += bool(flags)
        reason = "; ".join(f"{f} ({d})" if d else f for f, d in flags)
        date = str(raw.get("last_updated")) if raw.get("last_updated") else "(none)"
        rows.append(f"{i:02d}  {raw.get('doc_id', '?'):<9} {date:<12} {str(raw.get('title') or '(no title)'):<56} {reason}".rstrip())

    lines = [
        f"Inventory of {Path(path).name}  (raw export, before the loader repairs anything)",
        f"export_id {data.get('export_id')}  record_count {data.get('record_count')}  docs found {len(docs)}",
        "",
        f"{'#':<3} {'doc_id':<9} {'last_updated':<12} {'heading':<56} flags",
        *rows,
        "",
        "Summary by field (0 = clean)",
    ]
    field_width = max(len(f) for f, *_ in RULES)
    for field, flag, rule, _ in RULES:
        lines.append(f"  {field:<{field_width}}  {flag:<18} {totals[flag]:>2}   {rule}")
    parts = [f"{len(docs)} pages", f"{flagged_pages} flagged", f"{len(docs) - flagged_pages} clean"]
    parts += [f"{totals[flag]} {flag.lower()}" for _, flag, _, _ in RULES if totals[flag]]
    lines += ["", " | ".join(parts)]
    return "\n".join(lines) + "\n", flagged_pages
