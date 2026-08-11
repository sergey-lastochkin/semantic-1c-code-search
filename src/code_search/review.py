"""Dependency-free validation and evidence helpers for reviewed query sets."""

from __future__ import annotations

import json
from pathlib import Path


def resolve_reviewed_natural_queries(path: Path, chunks) -> tuple[list[dict[str, object]], dict[str, object]]:
    by_path = {chunk.context_path: chunk for chunk in chunks}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        metadata: dict[str, object] = {
            "dataset_id": "natural-language-legacy",
            "review_status": "pending",
            "source_query_count": len(raw),
        }
        source_rows = raw
    else:
        metadata = dict(raw["metadata"])
        source_rows = raw["queries"]
    rows: list[dict[str, object]] = []
    excluded: list[str] = []
    for row in source_rows:
        status = row.get("review_status")
        if status == "excluded":
            if not row.get("exclusion_reason"):
                raise ValueError(f"Excluded query requires a reason: {row['id']}")
            excluded.append(str(row["id"]))
            continue
        if status != "reviewed":
            raise ValueError(f"Natural-language query is not reviewed: {row['id']}")
        paths = row.get("expected_relevant_paths")
        if not paths:
            raise ValueError(f"Reviewed query requires expected paths: {row['id']}")
        missing = [value for value in paths if value not in by_path]
        if missing:
            raise ValueError(f"Natural-language relevance paths are absent from corpus: {missing}")
        rows.append(
            {
                **row,
                "relevant_ids": [by_path[value].id for value in paths],
                "expected_paths": paths,
            }
        )
    if not rows:
        raise ValueError("Natural-language benchmark contains no reviewed queries")
    return rows, {
        **metadata,
        "source_query_count": len(source_rows),
        "reviewed_query_count": len(rows),
        "excluded_query_count": len(excluded),
        "excluded_query_ids": excluded,
    }


def raw_rankings(searches, queries) -> list[dict[str, object]]:
    """Keep the top-ten paths for every reviewed natural-language judgement."""

    ranked: list[dict[str, object]] = []
    for row in queries:
        ranked.append(
            {
                "id": row["id"],
                "query": row["query"],
                "expected_paths": row["expected_paths"],
                "ranking": {
                    name: [chunk.context_path for chunk in search(prepared.value, row["query"])[:10]]
                    for name, prepared, search in searches
                },
            }
        )
    return ranked
