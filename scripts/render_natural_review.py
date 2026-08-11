"""Render a review ledger from a natural-language query dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.queries.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw["queries"]
    output = [
        "# Проверка русских запросов",
        "",
        "Статус и ожидаемая релевантность фиксируются после просмотра исходного BSL-кода. Исключённые строки остаются в журнале с причиной и не входят в метрики.",
        "",
        "| ID | Вопрос | Source paths | Статус | Основание |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        paths = row.get("expected_relevant_paths", row.get("proposed_relevant_paths", []))
        rendered_paths = "<br>".join(f"`{path}`" for path in paths) or "—"
        reason = row.get("review_note", row.get("exclusion_reason", row.get("rationale", "—")))
        output.append(f"| {row['id']} | {row['query']} | {rendered_paths} | {row['review_status']} | {reason} |")
    args.out.write_text("\n".join(output) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
