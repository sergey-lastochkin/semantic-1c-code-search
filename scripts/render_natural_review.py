"""Render the owner review checklist from the pending natural-language JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.queries.read_text(encoding="utf-8"))
    output = [
        "# Проверка русских запросов",
        "",
        "Все вопросы имеют `review_status: pending`. Предлагаемая релевантность составлена по именам и тексту открытого BSL-корпуса. Это рабочая разметка для эксперимента, не ручная оценка качества поиска.",
        "",
        "Перед публикацией итоговых метрик владелец подтверждает или исправляет каждую строку. После проверки статус в JSON меняется на `reviewed`, а benchmark запускается заново.",
        "",
        "| Вопрос | Предлагаемые процедуры | Source paths | Причина | Подтверждено |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        procedures = ", ".join(f"`{path.rsplit('/', 1)[-1]}`" for path in row["proposed_relevant_paths"])
        paths = "<br>".join(f"`{path}`" for path in row["proposed_relevant_paths"])
        output.append(f"| {row['query']} | {procedures} | {paths} | {row['rationale']} | [ ] |")
    args.out.write_text("\n".join(output) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
