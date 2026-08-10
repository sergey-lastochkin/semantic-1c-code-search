"""Embedding providers. LocalHash is a lexical baseline, not semantic embedding."""

import json
import re
import urllib.request
from hashlib import sha256
from math import sqrt
from typing import Protocol

TOKENS = re.compile(r"[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*")


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, text: str, dimension: int | None = None) -> list[float]: ...


def normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class DeterministicFakeEmbeddingProvider:
    """Stable test-double only; never choose it for a user-facing demo."""

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def embed(self, text: str, dimension: int | None = None) -> list[float]:
        return self._hash(text, dimension or self.dimension, signed=False)

    def truncate(self, vector: list[float], dimension: int) -> list[float]:
        return normalize(vector[:dimension])

    def _hash(self, text: str, dimension: int, signed: bool) -> list[float]:
        vector = [0.0] * dimension
        for token in TOKENS.findall(text.lower()):
            digest = int(sha256(token.encode()).hexdigest(), 16)
            vector[digest % dimension] += -1 if signed and digest & 1 else 1
        return normalize(vector)


class LocalHashEmbeddingProvider(DeterministicFakeEmbeddingProvider):
    """Dependency-free lexical hashing baseline. Token overlap drives similarity."""

    def embed(self, text: str, dimension: int | None = None) -> list[float]:
        return self._hash(text, dimension or self.dimension, signed=True)


class SentenceTransformerProvider:
    """Local SentenceTransformer adapter with an explicitly pinned revision.

    `query_prefix` and `passage_prefix` are kept here rather than hidden in a
    benchmark script: retrieval models such as multilingual-e5 require them.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        revision: str | None = None,
        device: str | None = None,
        query_prefix: str = "",
        passage_prefix: str = "",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Install optional dependency: pip install '.[embeddings]'"
            ) from error
        self.model_name = model_name
        self.revision = revision
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix
        self.model = SentenceTransformer(model_name, revision=revision, device=device)
        self.dimension = int(self.model.get_sentence_embedding_dimension())

    def embed(self, text: str, dimension: int | None = None) -> list[float]:
        return self.encode_queries([text], dimension=dimension)[0]

    def encode_queries(
        self, texts: list[str], dimension: int | None = None, batch_size: int = 32
    ) -> list[list[float]]:
        return self._encode(texts, self.query_prefix, dimension, batch_size)

    def encode_passages(
        self, texts: list[str], dimension: int | None = None, batch_size: int = 32
    ) -> list[list[float]]:
        return self._encode(texts, self.passage_prefix, dimension, batch_size)

    def _encode(
        self,
        texts: list[str],
        prefix: str,
        dimension: int | None,
        batch_size: int,
    ) -> list[list[float]]:
        vectors = self.model.encode(
            [prefix + text for text in texts],
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False,
        )
        return [normalize(vector.tolist()[:dimension]) for vector in vectors]


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        dimension: int = 1536,
    ) -> None:
        self.base_url, self.model, self.api_key, self.dimension = (
            base_url.rstrip("/"),
            model,
            api_key,
            dimension,
        )

    def embed(self, text: str, dimension: int | None = None) -> list[float]:
        if not self.api_key:
            raise RuntimeError(
                "No API key supplied; network request was intentionally not attempted"
            )
        request = urllib.request.Request(
            self.base_url + "/embeddings",
            data=json.dumps({"model": self.model, "input": text}).encode(),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return normalize(json.load(response)["data"][0]["embedding"][:dimension])
