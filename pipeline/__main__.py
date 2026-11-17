"""Run the pipeline: ``python -m pipeline [path/to/export.json]``.

Only the loader is implemented; the run stops cleanly at the first unwritten section.
"""

from __future__ import annotations

import logging
import sys

from pipeline import config
from pipeline.chunker import chunk_documents
from pipeline.embed import embed_chunks
from pipeline.loader import DEFAULT_EXPORT_PATH, load_export
from pipeline.upsert import upsert_vectors


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    path = argv[1] if len(argv) > 1 else config.get("EXPORT_PATH", str(DEFAULT_EXPORT_PATH))

    meta, docs = load_export(path)
    print(f"{meta.export_id}: {len(docs)} documents loaded")

    try:
        upsert_vectors(embed_chunks(chunk_documents(docs)))
    except NotImplementedError as exc:
        print(f"Stopped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
