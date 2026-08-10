from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import log2

from .embeddings import EmbeddingProvider, LocalHashEmbeddingProvider
from .models import Chunk
from .retrieval import VectorIndex


def evaluate(
    results: Sequence[Chunk],
    relevant_ids: Iterable[str],
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[str, float]:
    identifiers, relevant = [chunk.id for chunk in results], set(relevant_ids)
    metrics = {
        f"recall@{k}": len(set(identifiers[:k]) & relevant) / max(1, len(relevant))
        for k in ks
    }
    metrics["mrr"] = next(
        (
            1 / (index + 1)
            for index, value in enumerate(identifiers)
            if value in relevant
        ),
        0.0,
    )
    dcg = sum(
        1 / log2(index + 2)
        for index, value in enumerate(identifiers)
        if value in relevant
    )
    ideal = sum(
        1 / log2(index + 2) for index in range(min(len(relevant), len(identifiers)))
    )
    metrics["ndcg"] = dcg / ideal if ideal else 0.0
    return metrics


def matryoshka_experiment(
    chunks: Sequence[Chunk],
    questions: Sequence[dict[str, object]],
    provider: EmbeddingProvider | None = None,
    dimensions: tuple[int, ...] = (1024, 768, 512, 256, 128),
) -> list[dict[str, int | float]]:
    provider = provider or LocalHashEmbeddingProvider()
    results = []
    for requested in dimensions:
        dimension = min(requested, provider.dimension)
        index = VectorIndex(chunks, provider, dimension)
        scores = [
            evaluate(index.search(question["query"], 10), question["relevant_ids"])
            for question in questions
        ]
        results.append(
            {
                "dimension": dimension,
                **{
                    key: sum(score[key] for score in scores) / len(scores)
                    for key in scores[0]
                },
            }
        )
    return results
