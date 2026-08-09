from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .dependencies import DependencyGraph
from .evaluation import matryoshka_experiment
from .models import Chunk
from .parser import BSLParser
from .retrieval import HybridRetriever


def load(path: str | Path) -> list[Chunk]:
    return BSLParser().chunks(
        Path(path).read_text(encoding="utf8"),
        "structure_aware",
        object_name=Path(path).stem,
        module_type="CommonModule",
    )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Offline BSL semantic code search")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("source")
    i.add_argument("--out", default="experiments/index.json")
    s = sub.add_parser("search")
    s.add_argument("source")
    s.add_argument("query")
    s.add_argument("--k", type=int, default=5)
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
        print(
            json.dumps(
                [c.metadata() for c in HybridRetriever(cs).search(a.query, a.k)],
                ensure_ascii=False,
                indent=2,
            )
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
