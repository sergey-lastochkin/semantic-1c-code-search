"""Render compact SVG charts directly from a benchmark results JSON file."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path


def chart(rows, field: str, title: str, output: Path) -> None:
    width, height, left = 760, 360, 175
    maximum = max(float(row[field]) for row in rows) or 1.0
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="24" y="32" font-family="sans-serif" font-size="20">{escape(title)}</text>',
    ]
    for position, row in enumerate(rows):
        y = 60 + position * 54
        value = float(row[field])
        bar = (width - left - 32) * value / maximum
        pieces.extend(
            [
                f'<text x="24" y="{y + 20}" font-family="monospace" font-size="14">{escape(str(row["method"]))}</text>',
                f'<rect x="{left}" y="{y}" width="{bar:.2f}" height="28" fill="#2563eb"/>',
                f'<text x="{left + bar + 8:.2f}" y="{y + 20}" font-family="monospace" font-size="14">{value:.4f}</text>',
            ]
        )
    pieces.append(f'<text x="24" y="{height - 16}" font-family="sans-serif" font-size="12" fill="#475569">Источник: results.json</text>')
    pieces.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(pieces), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.results.read_text(encoding="utf-8"))["methods"]
    chart(rows, "ndcg_at_10", "nDCG@10 на детерминированной проверке", args.out / "quality.svg")
    chart(rows, "search_p95_ms", "p95 задержки поиска, мс", args.out / "latency.svg")


if __name__ == "__main__":
    main()
