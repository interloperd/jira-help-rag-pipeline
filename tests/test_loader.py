import json
from datetime import date

import pytest

from pipeline.loader import ExportFormatError, load_export, parse_date


def _export(tmp_path, docs, **extra):
    data = {"export_id": "test", "export_date": "2025-03-07", "record_count": len(docs), "docs": docs, **extra}
    path = tmp_path / "export.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _doc(doc_id="JCH-1", **overrides):
    doc = {
        "doc_id": doc_id,
        "title": "Title",
        "url": "https://example.com",
        "last_updated": "2025-02-18",
        "headings": '["Before you begin", "Grant it {#grant}"]',
        "body_markdown": "---\ntitle: Title\nlast_updated: 2025-02-18\n---\n# Title\n\nBody.",
        "word_count": 3,
    }
    doc.update(overrides)
    return doc


def test_parses_headings_frontmatter_and_body(tmp_path):
    _, docs = load_export(_export(tmp_path, [_doc()]))
    d = docs[0]
    assert d.headings == ["Before you begin", "Grant it"]
    assert d.body.startswith("# Title")
    assert d.frontmatter["last_updated"] == "2025-02-18"


@pytest.mark.parametrize("raw,expected", [
    ("2025-02-18", date(2025, 2, 18)),
    ("14/01/2025", date(2025, 1, 14)),
    (None, None),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


def test_null_date_falls_back_to_frontmatter(tmp_path):
    _, docs = load_export(_export(tmp_path, [_doc(last_updated=None)]))
    assert docs[0].last_updated == date(2025, 2, 18)


def test_duplicate_doc_id_rejected(tmp_path):
    with pytest.raises(ExportFormatError):
        load_export(_export(tmp_path, [_doc("A"), _doc("A")]))


def test_real_export_if_present():
    from pipeline.loader import DEFAULT_EXPORT_PATH
    if not DEFAULT_EXPORT_PATH.exists():
        pytest.skip("export not in data/")
    meta, docs = load_export(DEFAULT_EXPORT_PATH)
    assert len(docs) == meta.record_count
    assert all(isinstance(d.headings, list) for d in docs)
