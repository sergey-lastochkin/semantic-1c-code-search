# Project status

## IMPLEMENTED

BSL structure parsing; five chunk strategies and full retrieval metadata; local test/baseline embedding providers plus optional SentenceTransformer/OpenAI-compatible adapters; in-memory and embedded Qdrant backends; optional FAISS and a DB-API pgvector adapter; BM25/vector/RRF; filters; context pack; dependency graph; evaluation metrics; Matryoshka experiment; CLI; FastAPI; persisted JSON/CSV results.

## TESTED

Python 3.12 tests, real qdrant-client embedded mode, CLI index/search/eval, graph export, API smoke and deterministic evaluation dataset.

## NOT TESTED

1C runtime, downloaded SentenceTransformer model, OpenAI-compatible network request, FAISS persistence, PostgreSQL or live Qdrant server.

## EXTERNAL DEPENDENCIES

Python 3.11+; FastAPI/Pydantic/Uvicorn are required for the documented local API. Optional extras are qdrant-client, faiss-cpu plus NumPy, sentence-transformers and psycopg for a caller-supplied pgvector connection.

## KNOWN LIMITATIONS

The bundled relevance set is small and synthetic. Lexical-hash baseline results must not be generalized to semantic model quality. Parser coverage excludes the full BSL grammar and dynamic dispatch.

## NEXT PRODUCTION STEPS

Ingest an approved larger configuration corpus, label a representative question set, run a downloaded multilingual model, compare chunk/filter strategies, implement authenticated persistent Qdrant/pgvector and validate tokenizer-specific budgets.
