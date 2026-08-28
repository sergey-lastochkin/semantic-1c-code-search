"""Vector backends: local memory/Qdrant/FAISS and deployable pgvector code."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from typing import Any, Protocol

from .embeddings import EmbeddingProvider, cosine, embed_passage, embed_query
from .models import Chunk


class VectorBackend(Protocol):
    def upsert(
        self, chunks: Iterable[Chunk], provider: EmbeddingProvider, dimension: int
    ) -> None: ...

    def search(
        self,
        query: str,
        provider: EmbeddingProvider,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]: ...


class InMemoryVectorBackend:
    def upsert(
        self, chunks: Iterable[Chunk], provider: EmbeddingProvider, dimension: int
    ) -> None:
        self.dimension = dimension
        self.rows = [
            (chunk, embed_passage(provider, chunk.text, dimension))
            for chunk in list(chunks)
        ]

    def search(
        self,
        query: str,
        provider: EmbeddingProvider,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        query_vector = embed_query(provider, query, self.dimension)

        def allowed(chunk: Chunk) -> bool:
            return not filters or all(
                getattr(chunk, key, None) == value for key, value in filters.items()
            )

        ranked = (
            (cosine(query_vector, vector), chunk)
            for chunk, vector in self.rows
            if allowed(chunk)
        )
        return [
            chunk
            for _, chunk in sorted(ranked, key=lambda item: (-item[0], item[1].id))[:k]
        ]


class QdrantLocalBackend:
    """Actual qdrant-client `:memory:` mode; no daemon or Docker required."""

    def __init__(self, collection: str = "bsl_chunks") -> None:
        try:
            from qdrant_client import QdrantClient
        except ImportError as error:
            raise RuntimeError(
                "Install optional dependency: pip install '.[qdrant]'"
            ) from error
        self.client = QdrantClient(":memory:")
        self.collection = collection
        self.by_id: dict[int, Chunk] = {}

    def upsert(
        self, chunks: Iterable[Chunk], provider: EmbeddingProvider, dimension: int
    ) -> None:
        from qdrant_client.models import Distance, PointStruct, VectorParams

        self.dimension = dimension
        self.by_id = {}
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        points = []
        for point_id, chunk in enumerate(chunks):
            self.by_id[point_id] = chunk
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embed_passage(provider, chunk.text, dimension),
                    payload={
                        "object_name": chunk.object_name,
                        "module_type": chunk.module_type,
                        "is_export": chunk.is_export,
                    },
                )
            )
        if points:
            self.client.upsert(self.collection, points)

    def search(
        self,
        query: str,
        provider: EmbeddingProvider,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in (filters or {}).items()
        ]
        result = self.client.query_points(
            self.collection,
            query=embed_query(provider, query, self.dimension),
            query_filter=Filter(must=conditions) if conditions else None,
            limit=k,
        )
        return [self.by_id[int(point.id)] for point in result.points]


class FaissVectorBackend:
    """Optional real FAISS adapter; constructor makes capability explicit."""

    def __init__(self) -> None:
        try:
            import faiss
        except ImportError as error:
            raise RuntimeError(
                "FAISS is unavailable; install optional extra '.[faiss]'"
            ) from error
        self.faiss = faiss

    def upsert(
        self, chunks: Iterable[Chunk], provider: EmbeddingProvider, dimension: int
    ) -> None:
        import numpy as np

        self.chunks = list(chunks)
        self.dimension = dimension
        self.index = self.faiss.IndexFlatIP(dimension)
        self.index.add(
            np.asarray(
                [
                    embed_passage(provider, chunk.text, dimension)
                    for chunk in self.chunks
                ],
                dtype="float32",
            )
        )

    def search(
        self,
        query: str,
        provider: EmbeddingProvider,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        import numpy as np

        _scores, identifiers = self.index.search(
            np.asarray([embed_query(provider, query, self.dimension)], dtype="float32"),
            min(k, len(self.chunks)),
        )
        return [
            self.chunks[int(identifier)]
            for identifier in identifiers[0]
            if identifier >= 0
            and (
                not filters
                or all(
                    getattr(self.chunks[int(identifier)], key) == value
                    for key, value in filters.items()
                )
            )
        ]


class PgVectorBackend:
    """DB-API pgvector adapter; integration requires provisioned PostgreSQL."""

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        table: str = "bsl_chunks",
    ) -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", table):
            raise ValueError("unsafe pgvector table name")
        self.connection_factory = connection_factory
        self.table = table

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(f"{value:.10g}" for value in vector) + "]"

    def upsert(
        self, chunks: Iterable[Chunk], provider: EmbeddingProvider, dimension: int
    ) -> None:
        connection = self.connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table} ("
                "chunk_id text PRIMARY KEY, payload jsonb NOT NULL, embedding "
                f"vector({int(dimension)}) NOT NULL)"
            )
            for chunk in chunks:
                cursor.execute(
                    f"INSERT INTO {self.table}(chunk_id,payload,embedding) "
                    "VALUES(%s,%s::jsonb,%s::vector) "
                    "ON CONFLICT(chunk_id) DO UPDATE SET "
                    "payload=excluded.payload,embedding=excluded.embedding",
                    (
                        chunk.id,
                        json.dumps(chunk.metadata(), ensure_ascii=False),
                        self._vector_literal(
                            embed_passage(provider, chunk.text, dimension)
                        ),
                    ),
                )
            connection.commit()
            self.dimension = dimension
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def search(
        self,
        query: str,
        provider: EmbeddingProvider,
        k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        connection = self.connection_factory()
        cursor = connection.cursor()
        where_parts: list[str] = []
        params: list[object] = []
        for key, value in (filters or {}).items():
            where_parts.append("payload ->> %s = %s")
            params.extend((key, str(value)))
        where = " WHERE " + " AND ".join(where_parts) if where_parts else ""
        params.extend((self._vector_literal(embed_query(provider, query, self.dimension)), k))
        try:
            cursor.execute(
                f"SELECT payload FROM {self.table}{where} "
                "ORDER BY embedding <=> %s::vector LIMIT %s",
                tuple(params),
            )
            chunks = []
            for row in cursor.fetchall():
                payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                payload["metadata_refs"] = tuple(payload.get("metadata_refs", ()))
                chunks.append(Chunk(**payload))
            return chunks
        finally:
            cursor.close()
            connection.close()
