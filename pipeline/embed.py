"""Section 3 — Embed.

Turns text into vectors with OpenAI, using OPENAI_API_KEY and EMBED_MODEL from .env.
``embed_texts`` works today; ``embed_chunks`` will be written with the chunker.
"""

from __future__ import annotations

from openai import OpenAI

from pipeline import config

DEFAULT_MODEL = "text-embedding-3-small"


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Return one vector per input text, in the same order."""
    client = OpenAI(api_key=config.get("OPENAI_API_KEY", required=True))
    model = model or config.get("EMBED_MODEL", DEFAULT_MODEL)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]


def embed_chunks(chunks: list[dict]) -> list[dict]:
    raise NotImplementedError("embed: chunk embedding not written yet")
