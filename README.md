# 1C Semantic Code Search

## What

Offline-first retrieval engineering demo for synthetic BSL source. It parses structure, builds five chunk variants, indexes lexical/vector representations, performs BM25/vector/RRF retrieval, packages bounded context, builds a call graph and evaluates relevance.

## Why

Fixed text windows lose procedure and metadata context; vector-only search misses exact BSL identifiers; lexical-only search misses paraphrases. A useful code retriever needs structured chunks, metadata filters, hybrid ranking, context budgeting and reproducible relevance metrics—not an unmeasured “RAG” label.

## Architecture

- BSL parser: modules, procedures/functions, signatures, export flags, line ranges, queries and metadata references.
- Chunker: `fixed`, `fixed_overlap`, `procedure_aware`, `module_hierarchy`, `structure_aware`.
- Embeddings: deterministic test double, local lexical-hash baseline, optional SentenceTransformer and OpenAI-compatible providers.
- Backends: in-memory, real embedded Qdrant local mode, optional FAISS and a DB-API pgvector adapter.
- Retrieval/evaluation: BM25, cosine vector, RRF, metadata filters, Recall@k, MRR and nDCG.
- Interfaces: `index/search/eval` CLI plus FastAPI index/search/retrieve/experiment endpoints.

## Key engineering decisions

- The zero-setup local hash provider is clearly labeled lexical, not semantic.
- Qdrant is exercised through `qdrant-client` embedded `:memory:` mode.
- FAISS/pgvector never silently degrade while claiming an external backend.
- Context packing deduplicates, preserves module hierarchy, adds neighbors and enforces a token estimate.
- Matryoshka dimensions `1024/768/512/256/128` are capped by provider capability.
- Evaluation results are persisted; no strategy winner is claimed without evidence.

## Run

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m code_search.cli index fixtures/demo.bsl
.venv/bin/python -m code_search.cli search fixtures/demo.bsl "где формируется назначение платежа"
.venv/bin/python -m code_search.cli eval fixtures/demo.bsl examples/questions.jsonl
.venv/bin/uvicorn code_search.api:app
```

FastAPI: `POST /index`, `POST /search`, `POST /retrieve`, `POST /experiments/run`, `GET /experiments`. The minimal install supports the in-memory vector index, BM25, hybrid RRF, deterministic fake provider and LocalHash lexical baseline.

### Optional integrations

| Backend/provider | Minimal install | Extra | Service/model requirement |
|---|---:|---|---|
| In-memory vector, BM25, hybrid RRF | yes | — | no |
| Embedded Qdrant local | no | `.[qdrant]` | no daemon; local client only |
| FAISS | no | `.[faiss]` | no service |
| pgvector DB-API adapter | no | `.[postgres]` | provisioned PostgreSQL with pgvector |
| SentenceTransformer provider | no | `.[embeddings]` | model download on construction |

Optional backend constructors give an actionable error when their extra is absent. The base test suite skips the real Qdrant test without `qdrant-client`; it still tests the missing-extra boundary.

## Test

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

The minimal suite covers parsing/chunks, metadata, BM25, in-memory vector filters, hybrid/RRF, missing-Qdrant behavior, pgvector SQL generation, metrics, context, dependencies and API flows. `.[qdrant]` additionally enables the embedded-Qdrant test. CLI index/search/eval are executed above.

## Limitations

- No 1C runtime or real exported customer configuration was used.
- `fixtures/demo.bsl` is synthetic static parser input, not a deployed 1C module.
- SentenceTransformer model download, live OpenAI-compatible request, FAISS persistence and PostgreSQL/pgvector integration were not executed.
- The BSL parser is structural/heuristic, not a complete compiler frontend.
