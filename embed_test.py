"""Embed one test sentence and print its dimension.

Usage: python embed_test.py ["your sentence"]
Needs OPENAI_API_KEY in .env. The dimension printed is the one the Pinecone index must use.
"""

import sys

from pipeline import config
from pipeline.embed import DEFAULT_MODEL, embed_texts

sentence = sys.argv[1] if len(sys.argv) > 1 else "How do I reset a board filter?"
model = config.get("EMBED_MODEL", DEFAULT_MODEL)

vector = embed_texts([sentence], model=model)[0]

print(f'Embedding: "{sentence}"')
print(f"model: {model}")
print("[" + ", ".join(f"{v:.4f}" for v in vector[:4]) + ", ...]")
print(f"dimension: {len(vector)}")
