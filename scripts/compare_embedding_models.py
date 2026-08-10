"""Small, reproducible model-selection smoke test for the BSL corpus."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import time
from hashlib import sha256
from pathlib import Path

import numpy as np

from code_search.corpus import load_bsl_chunks
from code_search.embeddings import SentenceTransformerProvider
from code_search.evaluation import evaluate

MODELS = (
    {
        "name": "intfloat/multilingual-e5-small",
        "revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "license": "MIT",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
    {
        "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        "license": "Apache-2.0",
        "query_prefix": "",
        "passage_prefix": "",
    },
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="mps")
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    chunks = [
        chunk
        for chunk in load_bsl_chunks(
            args.corpus,
            {row["directory"]: row["commit"] for row in sources["sources"]},
        )
        if chunk.configuration == "Connector"
    ]
    by_path = {chunk.context_path: chunk for chunk in chunks}
    queries = [
        row
        for row in json.loads(args.queries.read_text(encoding="utf-8"))[:20]
        if all(path in by_path for path in row["proposed_relevant_paths"])
    ]
    rows = []
    for spec in MODELS:
        provider = SentenceTransformerProvider(
            spec["name"],
            revision=spec["revision"],
            device=args.device,
            query_prefix=spec["query_prefix"],
            passage_prefix=spec["passage_prefix"],
        )
        started = time.perf_counter()
        vectors = np.asarray(provider.encode_passages([chunk.text for chunk in chunks], batch_size=64))
        index_seconds = time.perf_counter() - started
        scores = []
        for query in queries:
            vector = np.asarray(provider.encode_queries([query["query"]])[0])
            ranked = [
                chunks[index]
                for index in sorted(
                    range(len(chunks)),
                    key=lambda index: (-float(vectors[index] @ vector), chunks[index].id),
                )[:10]
            ]
            scores.append(
                evaluate(
                    ranked,
                    [by_path[path].id for path in query["proposed_relevant_paths"]],
                    ks=(1, 5, 10),
                )
            )
        rows.append(
            {
                "model": spec["name"],
                "revision": spec["revision"],
                "license": spec["license"],
                "dimension": provider.dimension,
                "query_count": len(queries),
                "review_status": "pending",
                "index_seconds": round(index_seconds, 6),
                "recall_at_5": round(statistics.fmean(score["recall@5"] for score in scores), 6),
                "mrr_at_10": round(statistics.fmean(score["mrr"] for score in scores), 6),
            }
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "python": platform.python_version(),
                "device": args.device,
                "corpus_chunks": len(chunks),
                "query_set_sha256": sha256(args.queries.read_bytes()).hexdigest(),
                "note": "Selection smoke on 20 pending Russian questions; it is not a human-reviewed public metric.",
                "models": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
