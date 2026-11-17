import json
import re

from pipeline.inventory import run


def _doc(doc_id, **kw):
    d = {
        "doc_id": doc_id, "title": "T", "url": f"https://x/{doc_id}", "source_file": "a/b.md",
        "last_updated": "2025-02-18", "headings": '["One", "Two"]', "word_count": 9,
        "body_markdown": f"---\ntitle: T\nsource_url: https://x/{doc_id}\nlast_updated: 2025-02-18\n---\n# T\n\n## One\n\nalpha beta\n\n## Two\n\ngamma",
    }
    d.update(kw)
    return d


def _run(tmp_path, docs):
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"export_id": "t", "record_count": len(docs), "docs": docs}), encoding="utf-8")
    return run(p)


def test_clean_page_has_no_flags_and_zero_counts(tmp_path):
    report, flagged = _run(tmp_path, [_doc("A")])
    assert flagged == 0
    assert re.search(r"DUPLICATE URL\s+0\s", report)
    assert report.rstrip().endswith("1 pages | 0 flagged | 1 clean")


def test_each_problem_is_flagged(tmp_path):
    docs = [
        _doc("A", last_updated="07/02/2025"),
        _doc("B", last_updated=None),
        _doc("C", last_updated="2025-03-01"),
        _doc("D", url="https://x/A", source_file="a/Bad_Name.md"),
    ]
    report, flagged = _run(tmp_path, docs)
    assert "ODD DATE (07/02/2025)" in report
    assert "MISSING DATE (frontmatter has 2025-02-18)" in report
    assert "DATE CONFLICT (field 2025-03-01 vs frontmatter 2025-02-18)" in report
    assert "DUPLICATE URL (shared with D)" in report
    assert "ODD FILENAME" in report
    assert flagged == 4
