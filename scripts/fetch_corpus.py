"""Fetch the exact public BSL sources declared in studies/oss-bsl-corpus-2026-08-10."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from code_search.corpus import scan_bsl_files


def command(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    args.target.mkdir(parents=True, exist_ok=True)
    for source in sources["sources"]:
        checkout = args.target / source["directory"]
        if not checkout.exists():
            command("git", "clone", "--quiet", source["url"], str(checkout))
        command("git", "-C", str(checkout), "fetch", "--quiet", "origin", source["commit"])
        command("git", "-C", str(checkout), "checkout", "--quiet", "--detach", source["commit"])
    files = scan_bsl_files(args.target)
    manifest = {
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sources": sources["sources"],
        "files": files,
        "totals": {
            "bsl_files": len(files),
            "lines": sum(int(row["lines"]) for row in files),
            "bytes": sum(int(row["bytes"]) for row in files),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
