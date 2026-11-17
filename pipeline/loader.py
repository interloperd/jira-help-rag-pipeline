"""Section 1 — Loader.

Reads the Atlassian Jira Cloud help docs export
(``atlassian_jira_cloud_help_docs_export_2025-03-07.json``) and returns clean,
typed ``Document`` objects ready for the chunker.

Quirks of the export handled here:
- ``headings`` is a JSON-encoded string, not a list.
- ``last_updated`` mixes ISO dates, ``DD/MM/YYYY`` dates and ``null``, and
  sometimes disagrees with the date in the body's frontmatter.
- every ``body_markdown`` starts with a YAML frontmatter block.
- some headings carry anchors such as ``{#browse-projects}``.
- ``url`` is not unique (two docs can point to the same page), so
  ``doc_id`` is the only reliable key.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_EXPORT_PATH = Path("data/atlassian_jira_cloud_help_docs_export_2025-03-07.json")

REQUIRED_DOC_KEYS = ("doc_id", "title", "body_markdown")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_ANCHOR_RE = re.compile(r"\s*\{#[^}]*\}\s*$")
# Date formats seen in the export. DD/MM is confirmed by JCH-0032,
# whose field says 14/01/2025 while its frontmatter says 2025-01-14.
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


@dataclass(frozen=True)
class ExportMetadata:
    export_id: str
    export_date: date | None
    export_format_version: str
    source_system: str
    record_count: int


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    body: str
    url: str | None
    source_file: str | None
    product_area: str | None
    headings: list[str]
    last_updated: date | None
    word_count: int | None
    frontmatter: dict[str, str] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        """Flat metadata to carry through to the vector store."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "url": self.url,
            "source_file": self.source_file,
            "product_area": self.product_area,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class ExportFormatError(ValueError):
    """The file does not look like the expected export."""


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    log.warning("Unrecognised date format: %r", value)
    return None


def split_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter, body). Only flat ``key: value`` lines are expected."""
    match = _FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown.strip()
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, markdown[match.end():].strip()


def parse_headings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            log.warning("headings is not valid JSON: %r", value[:80])
            return []
    if not isinstance(value, list):
        return []
    return [_ANCHOR_RE.sub("", str(h)).strip() for h in value]


def _resolve_last_updated(doc_id: str, raw: Any, frontmatter: dict[str, str]) -> date | None:
    field_date = parse_date(raw)
    fm_date = parse_date(frontmatter.get("last_updated"))
    if field_date and fm_date and field_date != fm_date:
        log.warning(
            "%s: last_updated field (%s) disagrees with frontmatter (%s); keeping the field",
            doc_id, field_date, fm_date,
        )
    return field_date or fm_date


def _to_document(raw: dict[str, Any]) -> Document:
    missing = [k for k in REQUIRED_DOC_KEYS if not raw.get(k)]
    if missing:
        raise ExportFormatError(f"{raw.get('doc_id', '?')}: missing {missing}")

    doc_id = str(raw["doc_id"])
    frontmatter, body = split_frontmatter(raw["body_markdown"])
    word_count = raw.get("word_count")

    return Document(
        doc_id=doc_id,
        title=str(raw["title"]).strip(),
        body=body,
        url=raw.get("url") or frontmatter.get("source_url"),
        source_file=raw.get("source_file"),
        product_area=raw.get("product_area"),
        headings=parse_headings(raw.get("headings")),
        last_updated=_resolve_last_updated(doc_id, raw.get("last_updated"), frontmatter),
        word_count=int(word_count) if word_count is not None else None,
        frontmatter=frontmatter,
    )


def load_export(path: str | Path = DEFAULT_EXPORT_PATH) -> tuple[ExportMetadata, list[Document]]:
    """Load and validate the export. Raises ExportFormatError on structural problems."""
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise ExportFormatError(f"{path}: expected an object with a 'docs' list")

    docs = [_to_document(d) for d in data["docs"]]

    seen: set[str] = set()
    dupes = {d.doc_id for d in docs if d.doc_id in seen or seen.add(d.doc_id)}
    if dupes:
        raise ExportFormatError(f"duplicate doc_id values: {sorted(dupes)}")

    record_count = int(data.get("record_count", len(docs)))
    if record_count != len(docs):
        log.warning("record_count says %d but %d docs were found", record_count, len(docs))

    meta = ExportMetadata(
        export_id=str(data.get("export_id", "")),
        export_date=parse_date(data.get("export_date")),
        export_format_version=str(data.get("export_format_version", "")),
        source_system=str(data.get("source_system", "")),
        record_count=record_count,
    )
    log.info("Loaded %d documents from %s", len(docs), path)
    return meta, docs


SUMMARY_FIELDS = ("source_file", "title", "url", "last_updated", "headings")


def main(argv: list[str] | None = None) -> int:
    """Print one line per document with the five summary fields.

    Usage: ``python -m pipeline.loader [path/to/export.json]``
    Exits with code 1 if any document is missing one of the five fields.
    """
    import sys

    argv = sys.argv[1:] if argv is None else argv
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    _, docs = load_export(argv[0] if argv else DEFAULT_EXPORT_PATH)

    incomplete = 0
    for d in docs:
        # metadata() has no headings, and headings is a list: join it into one readable value.
        values = {**d.metadata(), "headings": "; ".join(d.headings)}
        row = [str(values[f]) if values[f] else "MISSING" for f in SUMMARY_FIELDS]
        incomplete += "MISSING" in row
        print(" | ".join(row))

    print(f"\n{len(docs)} documents, {len(docs) - incomplete} with all {len(SUMMARY_FIELDS)} fields")
    return 1 if incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
