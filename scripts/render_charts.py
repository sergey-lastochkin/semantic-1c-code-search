"""Render compact SVG charts directly from a benchmark results JSON file."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path


def display(value: float, field: str) -> str:
    if field == "serialized_index_bytes":
        return f"{value / 1024 / 1024:.1f} MiB"
    if field.endswith("_ms"):
        return f"{value:.2f} мс"
    return f"{value:.4f}"


def chart(rows, field: str, title: str, output: Path) -> None:
    width, height, left = 900, 360, 220
    maximum = max(float(row[field]) for row in rows) or 1.0
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="24" y="32" font-family="sans-serif" font-size="20">{escape(title)}</text>',
    ]
    for position, row in enumerate(rows):
        y = 60 + position * 54
        value = float(row[field])
        # Leave a generous right margin for the numeric label in GitHub's SVG renderer.
        bar = (width - left - 220) * value / maximum
        pieces.extend(
            [
                f'<text x="24" y="{y + 20}" font-family="monospace" font-size="14">{escape(str(row["method"]))}</text>',
                f'<rect x="{left}" y="{y}" width="{bar:.2f}" height="28" fill="#2563eb"/>',
                f'<text x="{left + bar + 8:.2f}" y="{y + 20}" font-family="monospace" font-size="14">{display(value, field)}</text>',
            ]
        )
    pieces.append(f'<text x="24" y="{height - 16}" font-family="sans-serif" font-size="12" fill="#475569">Источник: JSON с результатами</text>')
    pieces.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(pieces), encoding="utf-8")


def graph(edges, output: Path) -> None:
    width, height = 980, max(300, 84 + len(edges) * 30)
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#334155"/></marker></defs>',
        '<text x="24" y="32" font-family="sans-serif" font-size="20">Фрагмент графа зависимостей из results.json</text>',
    ]
    for number, edge in enumerate(edges):
        y = 58 + number * 30
        source = escape(str(edge["source"])[:62])
        target = escape(str(edge["target"])[:62])
        pieces.extend(
            [
                f'<text x="24" y="{y + 15}" font-family="monospace" font-size="12">{source}</text>',
                f'<line x1="455" y1="{y + 10}" x2="540" y2="{y + 10}" stroke="#334155" marker-end="url(#arrow)"/>',
                f'<text x="560" y="{y + 15}" font-family="monospace" font-size="12">{target}</text>',
            ]
        )
    pieces.append("</svg>")
    output.write_text("\n".join(pieces), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.results.read_text(encoding="utf-8"))
    methods = result["methods"]
    if isinstance(methods, list):
        chart(methods, "ndcg_at_10", "nDCG@10 на детерминированной проверке", args.out / "quality.svg")
        chart(methods, "search_p95_ms", "p95 задержки поиска, мс", args.out / "latency.svg")
    else:
        deterministic = methods["deterministic_static_gold"]
        natural_key = "natural_language_reviewed_v2"
        if natural_key not in methods:
            natural_key = "natural_language_pending"
        natural = methods[natural_key]
        chart(deterministic, "recall_at_5", "Recall@5: детерминированные запросы", args.out / "deterministic-recall-at-5.svg")
        chart(deterministic, "mrr_at_10", "MRR@10: детерминированные запросы", args.out / "deterministic-mrr-at-10.svg")
        chart(natural, "recall_at_5", "Recall@5: русские вопросы, reviewed V2", args.out / "natural-recall-at-5.svg")
        chart(deterministic, "search_p95_ms", "p95 поиска: детерминированные запросы", args.out / "latency-p95.svg")
        chart(deterministic, "serialized_index_bytes", "Размер индекса: детерминированный прогон", args.out / "index-size.svg")
    if "graph_sample" in result:
        graph(result["graph_sample"], args.out / "dependency-graph.svg")


if __name__ == "__main__":
    main()
