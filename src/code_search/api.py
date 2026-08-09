from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .context import context_pack, estimate_tokens
from .evaluation import matryoshka_experiment
from .models import Chunk
from .parser import BSLParser
from .retrieval import HybridRetriever


class IndexRequest(BaseModel):
    source: str = Field(min_length=1)
    strategy: str = "structure_aware"
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, object] = Field(default_factory=dict)


class RetrieveRequest(SearchRequest):
    token_budget: int = Field(default=1200, ge=1, le=100_000)


class Question(BaseModel):
    query: str
    relevant_ids: list[str]


class ExperimentRequest(BaseModel):
    questions: list[Question]
    dimensions: list[int] = Field(default_factory=lambda: [1024, 768, 512, 256, 128])


def create_app() -> FastAPI:
    app = FastAPI(title="Offline 1C semantic code search")
    app.state.chunks = []
    app.state.experiments = []

    def require_index() -> list[Chunk]:
        if not app.state.chunks:
            raise HTTPException(409, "index source first")
        return app.state.chunks

    @app.post("/index")
    def index(payload: IndexRequest) -> dict[str, object]:
        app.state.chunks = BSLParser().chunks(
            payload.source, payload.strategy, **payload.metadata
        )
        return {
            "chunks": len(app.state.chunks),
            "strategy": payload.strategy,
            "ids": [chunk.id for chunk in app.state.chunks],
        }

    @app.post("/search")
    def search(payload: SearchRequest) -> dict[str, object]:
        chunks = require_index()
        results = HybridRetriever(chunks).search(
            payload.query, payload.k, payload.filters or None
        )
        return {
            "query": payload.query,
            "results": [chunk.metadata() for chunk in results],
        }

    @app.get("/search", include_in_schema=False)
    def search_legacy(q: str, k: int = 5) -> list[dict[str, object]]:
        return search(SearchRequest(query=q, k=k))["results"]

    @app.post("/retrieve")
    def retrieve(payload: RetrieveRequest) -> dict[str, object]:
        chunks = require_index()
        ranked = HybridRetriever(chunks).search(
            payload.query, payload.k, payload.filters or None
        )
        packed = context_pack(ranked, payload.token_budget, chunks)
        return {
            "query": payload.query,
            "token_budget": payload.token_budget,
            "estimated_tokens": sum(estimate_tokens(chunk.text) for chunk in packed),
            "chunks": [chunk.metadata() for chunk in packed],
        }

    @app.post("/experiments/run")
    def run_experiment(payload: ExperimentRequest) -> dict[str, object]:
        chunks = require_index()
        if not payload.questions:
            raise HTTPException(422, "questions must not be empty")
        rows = matryoshka_experiment(
            chunks,
            [question.model_dump() for question in payload.questions],
            dimensions=tuple(payload.dimensions),
        )
        record = {
            "id": str(uuid4()),
            "rows": rows,
            "question_count": len(payload.questions),
        }
        app.state.experiments.append(record)
        return record

    @app.get("/experiments")
    def experiments() -> list[dict[str, object]]:
        return app.state.experiments

    return app


app = create_app()
