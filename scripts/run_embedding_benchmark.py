"""Benchmark a pinned local embedding model over the checked-out BSL corpus."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import platform
import statistics
import subprocess
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
from run_benchmark import make_queries, percentile

from code_search.corpus import load_bsl_chunks
from code_search.embeddings import SentenceTransformerProvider
from code_search.evaluation import evaluate
from code_search.impact import ImpactGraph
from code_search.retrieval import BM25Index, rrf
from code_search.review import raw_rankings, resolve_reviewed_natural_queries

MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_LICENSE = "MIT"


class EmbeddingIndex:
    def __init__(self, chunks, provider: SentenceTransformerProvider, batch_size: int):
        self.chunks = list(chunks)
        started = time.perf_counter()
        self.vectors = np.asarray(
            provider.encode_passages([chunk.text for chunk in self.chunks], batch_size=batch_size),
            dtype=np.float32,
        )
        self.index_seconds = time.perf_counter() - started
        self.index_bytes = int(self.vectors.nbytes)
        self.provider = provider

    def search(self, query: str, k: int = 10):
        query_vector = np.asarray(self.provider.encode_queries([query])[0], dtype=np.float32)
        scores = self.vectors @ query_vector
        ordered = sorted(range(len(self.chunks)), key=lambda i: (-float(scores[i]), self.chunks[i].id))
        return [self.chunks[index] for index in ordered[:k]]


@dataclass
class PreparedIndex:
    value: object
    index_seconds: float
    index_bytes: int


def query_hash(rows: list[dict[str, object]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def mean(scores: list[dict[str, float]], key: str) -> float:
    return round(statistics.fmean(row[key] for row in scores), 6)


def prepare(build) -> PreparedIndex:
    started = time.perf_counter()
    value = build()
    elapsed = time.perf_counter() - started
    return PreparedIndex(
        value=value,
        index_seconds=float(getattr(value, "index_seconds", elapsed)),
        index_bytes=int(
            getattr(value, "index_bytes", len(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)))
        ),
    )


def measure(name: str, index: PreparedIndex, search, queries) -> dict[str, object]:
    latencies: list[float] = []
    scores: list[dict[str, float]] = []
    for row in queries:
        started = time.perf_counter()
        result = search(index.value, str(row["query"]))[:10]
        latencies.append((time.perf_counter() - started) * 1000)
        scores.append(evaluate(result, row["relevant_ids"], ks=(1, 5, 10)))
    return {
        "method": name,
        "index_seconds": round(index.index_seconds, 6),
        "serialized_index_bytes": index.index_bytes,
        "recall_at_1": mean(scores, "recall@1"),
        "recall_at_5": mean(scores, "recall@5"),
        "recall_at_10": mean(scores, "recall@10"),
        "mrr_at_10": mean(scores, "mrr"),
        "ndcg_at_10": mean(scores, "ndcg"),
        "search_p50_ms": round(statistics.median(latencies), 4),
        "search_p95_ms": round(percentile(latencies, 0.95), 4),
    }


def exact_index(chunks):
    return {
        chunk.procedure_name.casefold(): chunk
        for chunk in chunks
        if chunk.procedure_name
    }


def methods(indexes: dict[str, PreparedIndex], queries) -> list[dict[str, object]]:
    return [
        measure(name, prepared, search, queries)
        for name, prepared, search in search_methods(indexes)
    ]


def search_methods(indexes: dict[str, PreparedIndex]):
    return [
        (
            "exact_name",
            indexes["exact"],
            lambda index, query: [index[query.casefold()]] if query.casefold() in index else [],
        ),
        ("bm25", indexes["bm25"], lambda index, query: index.search(query, 10)),
        (
            "embeddings",
            indexes["embedding"],
            lambda index, query: index.search(query, 10),
        ),
        (
            "rrf_bm25_embeddings",
            indexes["rrf"],
            lambda index, query: rrf([index[0].search(query, 20), index[1].search(query, 20)])[:10],
        ),
        (
            "graph_context",
            indexes["graph"],
            lambda index, query: index.search_context(query, 10),
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--natural-queries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    source_data = json.loads(args.sources.read_text(encoding="utf-8"))
    corpus_manifest = json.loads(args.corpus_manifest.read_text(encoding="utf-8"))
    versions = {row["directory"]: row["commit"] for row in source_data["sources"]}
    chunks = load_bsl_chunks(args.corpus, versions)
    graph = ImpactGraph(chunks)
    deterministic = make_queries(chunks, graph)
    natural, natural_review = resolve_reviewed_natural_queries(args.natural_queries, chunks)
    provider = SentenceTransformerProvider(
        MODEL_NAME,
        revision=MODEL_REVISION,
        device=args.device,
        query_prefix="query: ",
        passage_prefix="passage: ",
    )
    if provider.dimension != 384:
        raise RuntimeError(f"Expected 384-dim model, received {provider.dimension}")
    indexes = {
        "exact": prepare(lambda: exact_index(chunks)),
        "bm25": prepare(lambda: BM25Index(chunks)),
        "embedding": prepare(lambda: EmbeddingIndex(chunks, provider, args.batch_size)),
        "graph": prepare(lambda: graph),
    }
    indexes["rrf"] = PreparedIndex(
        value=(indexes["bm25"].value, indexes["embedding"].value),
        index_seconds=indexes["bm25"].index_seconds + indexes["embedding"].index_seconds,
        index_bytes=indexes["bm25"].index_bytes + indexes["embedding"].index_bytes,
    )
    result = {
        "run": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "python": platform.python_version(),
            "machine": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor() or "unknown",
                "cpu_count": os.cpu_count(),
                "device": args.device,
            },
        },
        "model": {
            "name": MODEL_NAME,
            "revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
            "dimension": provider.dimension,
            "input_prefixes": {"query": "query: ", "passage": "passage: "},
            "matryoshka": {
                "supported": False,
                "reason": "The published model card does not state Matryoshka training; dimensions 512, 256 and 128 are not benchmarked as Matryoshka vectors.",
            },
        },
        "corpus": {
            **corpus_manifest["totals"],
            "chunks": len(chunks),
            "graph_links": sum(len(value) for value in graph.outbound.values()),
            "source_manifest_sha256": sha256(args.sources.read_bytes()).hexdigest(),
            "corpus_manifest_sha256": sha256(args.corpus_manifest.read_bytes()).hexdigest(),
        },
        "query_sets": {
            "deterministic_static_gold": {
                "query_count": len(deterministic),
                "query_set_sha256": query_hash(deterministic),
                "review_status": "generated_static_gold",
            },
            "natural_language_reviewed_v2": {
                "path": args.natural_queries.as_posix(),
                "query_count": len(natural),
                "query_set_sha256": sha256(args.natural_queries.read_bytes()).hexdigest(),
                **natural_review,
            },
        },
        "methods": {
            "deterministic_static_gold": methods(indexes, deterministic),
            "natural_language_reviewed_v2": methods(indexes, natural),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ranking_path = args.out.with_name("natural-language-query-rankings.jsonl")
    rankings = raw_rankings(search_methods(indexes), natural)
    ranking_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rankings),
        encoding="utf-8",
    )
    print(json.dumps({"chunks": len(chunks), "query_sets": {key: len(value) for key, value in {"deterministic": deterministic, "natural": natural}.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
