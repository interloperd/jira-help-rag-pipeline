"""Create the Pinecone index with the same dimension as the embedding model, then show its details.

Usage: python create_index.py
Needs OPENAI_API_KEY and PINECONE_API_KEY in .env.

The dimension is not typed by hand: the script embeds one test sentence and uses
the length of that vector, so the index always matches EMBED_MODEL.
If the index already exists, nothing is created; the script checks its dimension instead.
"""

import sys
import time

from pinecone import Pinecone, ServerlessSpec

from pipeline import config
from pipeline.embed import DEFAULT_MODEL, embed_texts

INDEX_NAME = config.get("PINECONE_INDEX", "jira-cloud-help-docs")
CLOUD = config.get("PINECONE_CLOUD", "aws")
REGION = config.get("PINECONE_REGION", "us-east-1")
METRIC = "cosine"


def model_dimension() -> int:
    model = config.get("EMBED_MODEL", DEFAULT_MODEL)
    dim = len(embed_texts(["How do I reset a board filter?"], model=model)[0])
    print(f"Model {model} returns vectors of dimension {dim}")
    return dim


def wait_until_ready(pc: Pinecone, name: str, timeout: int = 120) -> None:
    start = time.time()
    while not pc.describe_index(name).status["ready"]:
        if time.time() - start > timeout:
            sys.exit(f"Index {name} is still not ready after {timeout}s, check the Pinecone console.")
        time.sleep(2)


def main() -> int:
    dim = model_dimension()
    pc = Pinecone(api_key=config.get("PINECONE_API_KEY", required=True))

    if INDEX_NAME in pc.list_indexes().names():
        print(f"Index {INDEX_NAME} already exists, not creating it again")
    else:
        pc.create_index(
            name=INDEX_NAME,
            dimension=dim,
            metric=METRIC,
            spec=ServerlessSpec(cloud=CLOUD, region=REGION),
        )
        print(f"Created index {INDEX_NAME}")
        wait_until_ready(pc, INDEX_NAME)

    desc = pc.describe_index(INDEX_NAME).to_dict()
    serverless = desc.get("spec", {}).get("serverless", {})
    print(f"name: {desc.get('name')}")
    print(f"dimension: {desc.get('dimension')}  metric: {desc.get('metric')}")
    print(f"status: {desc.get('status', {}).get('state')}  cloud: {serverless.get('cloud')} {serverless.get('region')}")
    print(f"host: {desc.get('host')}")

    if desc.get("dimension") != dim:
        print(f"MISMATCH: index has dimension {desc.get('dimension')} but the model gives {dim}.")
        print("Delete the index in the Pinecone console or set another PINECONE_INDEX, then rerun.")
        return 1

    print(f"Index {INDEX_NAME} matches your model at {dim} dimensions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
