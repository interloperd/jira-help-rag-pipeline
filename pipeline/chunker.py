"""Section 2 — Chunker. Not implemented yet.

Will split each ``Document`` from the loader into retrieval-sized chunks,
carrying ``Document.metadata()`` onto every chunk.
"""

from __future__ import annotations

from pipeline.loader import Document


def chunk_documents(docs: list[Document]) -> list[dict]:
    raise NotImplementedError("chunker: section not written yet")
