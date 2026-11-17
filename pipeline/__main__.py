"""Run the pipeline.

    python -m pipeline [export.json]                       loader, then stops at the first unwritten section
    python -m pipeline --inventory [export.json] [--out F]  data quality inventory of the raw export
"""

from __future__ import annotations

import argparse
import logging
import sys

from pipeline import config
from pipeline.loader import DEFAULT_EXPORT_PATH


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    parser.add_argument("export", nargs="?", default=config.get("EXPORT_PATH", str(DEFAULT_EXPORT_PATH)))
    parser.add_argument("--inventory", action="store_true", help="list data quality problems per page")
    parser.add_argument("--out", help="also write the inventory to this file")
    args = parser.parse_args(argv[1:])

    if args.inventory:
        from pipeline.inventory import run
        report, _ = run(args.export)
        print(report, end="")
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(report)
            print(f"\nWritten to {args.out}")
        return 0

    from pipeline.chunker import chunk_documents
    from pipeline.loader import load_export

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    meta, docs = load_export(args.export)
    print(f"{meta.export_id}: {len(docs)} documents loaded")
    try:
        chunk_documents(docs)
    except NotImplementedError as exc:
        print(f"Stopped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
