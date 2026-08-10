"""Loading and manifest helpers for a local checked-out BSL corpus."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .models import Chunk
from .parser import BSLParser


def _bsl_paths(corpus_root: Path, source_names: set[str]):
    for path in sorted(corpus_root.rglob("*.bsl")):
        if ".git" not in path.parts and path.relative_to(corpus_root).parts[0] in source_names:
            yield path


def scan_bsl_files(corpus_root: Path, source_names: set[str]) -> list[dict[str, object]]:
    """Return stable metadata for checked-out source files without copying them."""
    rows: list[dict[str, object]] = []
    for path in _bsl_paths(corpus_root, source_names):
        payload = path.read_bytes()
        relative = path.relative_to(corpus_root).as_posix()
        rows.append(
            {
                "path": relative,
                "sha256": sha256(payload).hexdigest(),
                "bytes": len(payload),
                "lines": payload.count(b"\n") + bool(payload),
            }
        )
    return rows


def load_bsl_chunks(corpus_root: Path, source_versions: dict[str, str]) -> list[Chunk]:
    """Parse BSL procedures from a corpus checkout selected by source directory."""
    parser = BSLParser()
    chunks: list[Chunk] = []
    for path in _bsl_paths(corpus_root, set(source_versions)):
        relative = path.relative_to(corpus_root)
        source = relative.parts[0]
        chunks.extend(
            parser.chunks(
                path.read_text(encoding="utf-8"),
                "structure_aware",
                configuration=source,
                version=source_versions[source],
                module_type="BSLModule",
                object_name=relative.with_suffix("").as_posix(),
            )
        )
    return chunks
