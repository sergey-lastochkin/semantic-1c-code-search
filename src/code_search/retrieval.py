from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import log

from .backends import InMemoryVectorBackend, VectorBackend
from .embeddings import TOKENS, EmbeddingProvider, LocalHashEmbeddingProvider
from .models import Chunk


class VectorIndex:
    def __init__(
        self,
        chunks: Iterable[Chunk],
        provider: EmbeddingProvider,
        dimension: int = 256,
        backend: VectorBackend | None = None,
    ) -> None:
        self.chunks, self.provider, self.dimension = list(chunks), provider, dimension
        self.backend = backend or InMemoryVectorBackend()
        self.backend.upsert(self.chunks, provider, dimension)

    def search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        return self.backend.search(query, self.provider, k, filters)


class BM25Index:
    def __init__(
        self, chunks: Iterable[Chunk], k1: float = 1.5, b: float = 0.75
    ) -> None:
        chunks = list(chunks)
        self.chunks, self.k1, self.b = list(chunks), k1, b
        self.docs = [TOKENS.findall(chunk.text.lower()) for chunk in chunks]
        self.df = {}
        for document in self.docs:
            for token in set(document):
                self.df[token] = self.df.get(token, 0) + 1
        self.average_length = sum(map(len, self.docs)) / max(1, len(self.docs))

    def search(self, query: str, k: int = 10) -> list[Chunk]:
        query_tokens, total, scored = TOKENS.findall(query.lower()), len(self.docs), []
        for chunk, document in zip(self.chunks, self.docs):
            score = 0.0
            for token in query_tokens:
                frequency, document_frequency = (
                    document.count(token),
                    self.df.get(token, 0),
                )
                if frequency:
                    score += (
                        log(
                            1
                            + (total - document_frequency + 0.5)
                            / (document_frequency + 0.5)
                        )
                        * frequency
                        * (self.k1 + 1)
                        / (
                            frequency
                            + self.k1
                            * (
                                1
                                - self.b
                                + self.b * len(document) / (self.average_length or 1)
                            )
                        )
                    )
            if score:
                scored.append((score, chunk))
        return [
            chunk
            for _, chunk in sorted(scored, key=lambda item: (-item[0], item[1].id))[:k]
        ]


def rrf(rankings: Sequence[Sequence[Chunk]], constant: int = 60) -> list[Chunk]:
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, 1):
            scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (constant + rank)
            chunks[chunk.id] = chunk
    return [
        chunks[identifier]
        for identifier in sorted(
            scores, key=lambda identifier: (-scores[identifier], identifier)
        )
    ]


class HybridRetriever:
    def __init__(
        self,
        chunks: Iterable[Chunk],
        provider: EmbeddingProvider | None = None,
        dimension: int = 256,
        backend: VectorBackend | None = None,
    ) -> None:
        chunks = list(chunks)
        self.vector = VectorIndex(
            chunks,
            provider or LocalHashEmbeddingProvider(dimension),
            dimension,
            backend,
        )
        self.bm25 = BM25Index(chunks)

    def search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        return rrf([self.vector.search(query, k, filters), self.bm25.search(query, k)])[
            :k
        ]
