"""Run deterministic BSL retrieval checks over a checked-out public corpus."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path

from code_search.corpus import load_bsl_chunks
from code_search.embeddings import LocalHashEmbeddingProvider
from code_search.evaluation import evaluate
from code_search.impact import ImpactGraph
from code_search.retrieval import BM25Index, HybridRetriever, VectorIndex


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def make_queries(chunks, graph: ImpactGraph) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for chunk in sorted(chunks, key=lambda item: item.context_path):
        if not chunk.procedure_name:
            continue
        name = chunk.procedure_name.casefold()
        if name not in seen_names and len(seen_names) < 30:
            rows.append(
                {
                    "kind": "exact_procedure",
                    "query": chunk.procedure_name,
                    "relevant_ids": [chunk.id],
                    "expected_paths": [chunk.context_path],
                }
            )
            seen_names.add(name)
    calls = [link for links in graph.outbound.values() for link in links if link.kind == "call"]
    for link in sorted(calls, key=lambda item: (item.evidence, item.source, item.target))[:30]:
        target = graph.chunks[link.target]
        rows.append(
            {
                "kind": "known_call",
                "query": link.evidence,
                "relevant_ids": [target.id],
                "expected_paths": [link.target],
            }
        )
    references: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        for reference in chunk.metadata_refs:
            references[reference].append(chunk.id)
    for reference, identifiers in sorted(references.items())[:30]:
        rows.append(
            {
                "kind": "metadata_reference",
                "query": reference,
                "relevant_ids": sorted(set(identifiers)),
            }
        )
    return rows


def measure(name: str, build, search, queries) -> dict[str, object]:
    tracemalloc.start()
    started = time.perf_counter()
    index = build()
    index_seconds = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    latencies: list[float] = []
    scores: list[dict[str, float]] = []
    for row in queries:
        started = time.perf_counter()
        result = search(index, str(row["query"]))[:10]
        latencies.append((time.perf_counter() - started) * 1000)
        scores.append(evaluate(result, row["relevant_ids"], ks=(1, 5, 10)))
    return {
        "method": name,
        "index_seconds": round(index_seconds, 6),
        "index_peak_bytes": peak,
        "recall_at_1": round(statistics.fmean(row["recall@1"] for row in scores), 6),
        "recall_at_5": round(statistics.fmean(row["recall@5"] for row in scores), 6),
        "recall_at_10": round(statistics.fmean(row["recall@10"] for row in scores), 6),
        "mrr_at_10": round(statistics.fmean(row["mrr"] for row in scores), 6),
        "ndcg_at_10": round(statistics.fmean(row["ndcg"] for row in scores), 6),
        "search_p50_ms": round(statistics.median(latencies), 4),
        "search_p95_ms": round(percentile(latencies, 0.95), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source_data = json.loads(args.sources.read_text(encoding="utf-8"))
    versions = {row["directory"]: row["commit"] for row in source_data["sources"]}
    chunks = load_bsl_chunks(args.corpus, versions)
    graph = ImpactGraph(chunks)
    queries = make_queries(chunks, graph)
    provider = LocalHashEmbeddingProvider(256)
    rows = [
        measure(
            "exact_name",
            lambda: {chunk.procedure_name.casefold(): chunk for chunk in chunks if chunk.procedure_name},
            lambda index, query: [index[query.casefold()]] if query.casefold() in index else [],
            queries,
        ),
        measure("bm25", lambda: BM25Index(chunks), lambda index, query: index.search(query, 10), queries),
        measure(
            "hash_vector",
            lambda: VectorIndex(chunks, provider),
            lambda index, query: index.search(query, 10),
            queries,
        ),
        measure(
            "rrf_hybrid",
            lambda: HybridRetriever(chunks, provider),
            lambda index, query: index.search(query, 10),
            queries,
        ),
        measure(
            "graph_context",
            lambda: graph,
            lambda index, query: index.search_context(query, 10),
            queries,
        ),
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "benchmark_kind": "deterministic_static_gold",
                "vector_note": "hash_vector uses LocalHashEmbeddingProvider; it is a lexical hash baseline, not a semantic model.",
                "corpus": {"chunks": len(chunks), "graph_links": sum(len(v) for v in graph.outbound.values())},
                "queries": queries,
                "methods": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"chunks": len(chunks), "queries": len(queries), "methods": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
