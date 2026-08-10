"""Serve a read-only local BSL search page for a checked-out corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from code_search.corpus import load_bsl_chunks, scan_bsl_files
from code_search.viewer import create_viewer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    versions = {row["directory"]: row["commit"] for row in sources["sources"]}
    chunks = load_bsl_chunks(args.corpus, versions)
    file_count = len(scan_bsl_files(args.corpus, set(versions)))
    uvicorn.run(create_viewer(chunks, file_count), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
