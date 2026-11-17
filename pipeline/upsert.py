"""Section 4 — Upsert. Not implemented yet.

Will write embedded chunks to the vector store configured in .env
(VECTOR_DB_URL, VECTOR_DB_API_KEY, VECTOR_INDEX_NAME), keyed by doc_id + chunk index.
"""

from __future__ import annotations


def upsert_vectors(vectors: list[dict]) -> None:
    raise NotImplementedError("upsert: section not written yet")
