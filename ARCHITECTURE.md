# Architecture

Parsing and chunk construction create backend-neutral `Chunk` records. Embedding providers and vector backends are separate protocols; BM25 shares only chunk IDs and metadata. Hybrid retrieval combines independent ranks with reciprocal-rank fusion. Context assembly is downstream of ranking, allowing deduplication, neighbor expansion and budget enforcement without changing index semantics. Evaluation consumes query/relevant-ID fixtures and reports strategy/dimension metrics; it does not mutate the index.
