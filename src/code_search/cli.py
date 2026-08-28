from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .dependencies import DependencyGraph
from .embeddings import SentenceTransformerProvider
from .evaluation import matryoshka_experiment
from .models import Chunk
from .parser import BSLParser
from .retrieval import BM25Index, HybridRetriever

DEFAULT_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
EXCLUDED_DIRECTORIES = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def load(path: str | Path) -> list[Chunk]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"BSL source does not exist: {source}")

    paths = [source] if source.is_file() else [
        candidate
        for candidate in sorted(source.rglob("*.bsl"))
        if not EXCLUDED_DIRECTORIES.intersection(candidate.parts)
    ]
    if not paths:
        raise ValueError(f"No .bsl files found under: {source}")

    parser = BSLParser()
    chunks: list[Chunk] = []
    for candidate in paths:
        object_name = (
            candidate.stem
            if source.is_file()
            else candidate.relative_to(source).with_suffix("").as_posix()
        )
        chunks.extend(
            parser.chunks(
                candidate.read_text(encoding="utf-8-sig"),
                "module_hierarchy",
                configuration=source.stem,
                version="local",
                object_name=object_name,
                module_type="BSLModule",
            )
        )
    if not chunks:
        raise ValueError(f"No searchable BSL code found under: {source}")
    return chunks


def _format_results(results: list[Chunk]) -> str:
    if not results:
        return "Nothing found. Try a procedure name or a term used in the code."
    blocks = []
    for position, chunk in enumerate(results, 1):
        name = chunk.procedure_name or "module code"
        location = f"{chunk.object_name}:{chunk.line_start}-{chunk.line_end}"
        preview = next(
            (line.strip() for line in chunk.text.splitlines() if line.strip()), ""
        )
        blocks.append(f"{position}. {name}  [{location}]\n   {preview}")
    return "\n\n".join(blocks)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Offline search across BSL files")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("source")
    i.add_argument("--out", default="experiments/index.json")
    s = sub.add_parser("search")
    s.add_argument("source")
    s.add_argument("query")
    s.add_argument("--k", type=int, default=5)
    s.add_argument(
        "--engine", choices=("bm25", "hybrid"), default="bm25",
        help="bm25 is dependency-free; hybrid uses a local embedding model",
    )
    s.add_argument("--model", default=DEFAULT_MODEL)
    s.add_argument("--device", default=None)
    s.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    g = sub.add_parser("graph")
    g.add_argument("source")
    g.add_argument("--format", choices=["json", "mermaid", "dot"], default="json")
    e = sub.add_parser("eval")
    e.add_argument("source")
    e.add_argument("questions")
    e.add_argument("--out", default="experiments/results")
    a = p.parse_args(argv)
    cs = load(a.source)
    if a.cmd == "index":
        output = Path(a.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps([c.metadata() for c in cs], ensure_ascii=False, indent=2)
        )
        print(json.dumps({"chunks": len(cs), "output": str(output)}))
        return
    if a.cmd == "search":
        if a.engine == "hybrid":
            provider = SentenceTransformerProvider(
                model_name=a.model,
                revision=(
                    DEFAULT_MODEL_REVISION if a.model == DEFAULT_MODEL else None
                ),
                device=a.device,
                query_prefix="query: ",
                passage_prefix="passage: ",
            )
            results = HybridRetriever(
                cs, provider, dimension=provider.dimension
            ).search(a.query, a.k)
        else:
            results = BM25Index(cs).search(a.query, a.k)
        print(
            json.dumps(
                [c.metadata() for c in results], ensure_ascii=False, indent=2
            )
            if a.json
            else _format_results(results)
        )
        return
    if a.cmd == "graph":
        graph = DependencyGraph()
        parser = BSLParser()
        for c in cs:
            graph.add_chunk(parser, c)
        val = (
            {k: sorted(v) for k, v in graph.edges.items()}
            if a.format == "json"
            else getattr(graph, a.format)()
        )
        print(
            json.dumps(val, ensure_ascii=False, indent=2) if a.format == "json" else val
        )
        return
    qs = [
        json.loads(x) for x in Path(a.questions).read_text().splitlines() if x.strip()
    ]
    names = {c.procedure_name: c.id for c in cs}
    prepared = [
        {
            "query": q["query"],
            "relevant_ids": [
                names[x] for x in q.get("expected_procedures", []) if x in names
            ],
        }
        for q in qs
    ]
    rows = matryoshka_experiment(cs, prepared)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    with out.with_suffix(".csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0])
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
