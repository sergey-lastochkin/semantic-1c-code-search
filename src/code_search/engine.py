"""Compatibility facade; new code should import the focused modules directly."""

from .backends import (
    FaissVectorBackend,
    InMemoryVectorBackend,
    PgVectorBackend,
    QdrantLocalBackend,
    VectorBackend,
)
from .context import context_pack
from .dependencies import DependencyGraph
from .embeddings import (
    DeterministicFakeEmbeddingProvider,
    LocalHashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    SentenceTransformerProvider,
    cosine,
)
from .evaluation import evaluate, matryoshka_experiment
from .impact import ImpactGraph, Link
from .models import BSLUnit, Chunk
from .parser import BSLParser
from .retrieval import BM25Index, HybridRetriever, VectorIndex, rrf

FakeEmbeddingProvider = DeterministicFakeEmbeddingProvider
QdrantVectorBackend = QdrantLocalBackend
LexicalIndex = BM25Index

__all__ = [
    "BM25Index",
    "BSLParser",
    "BSLUnit",
    "Chunk",
    "DependencyGraph",
    "DeterministicFakeEmbeddingProvider",
    "FaissVectorBackend",
    "FakeEmbeddingProvider",
    "HybridRetriever",
    "ImpactGraph",
    "InMemoryVectorBackend",
    "LexicalIndex",
    "Link",
    "LocalHashEmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "PgVectorBackend",
    "QdrantLocalBackend",
    "QdrantVectorBackend",
    "SentenceTransformerProvider",
    "VectorBackend",
    "VectorIndex",
    "context_pack",
    "cosine",
    "evaluate",
    "matryoshka_experiment",
    "rrf",
]
