from __future__ import annotations

from collections.abc import Iterable

from .models import Chunk


def estimate_tokens(text: str) -> int:
    """Conservative dependency-free estimate; production may inject a model tokenizer."""
    return max(1, (len(text) + 3) // 4)


def context_pack(
    ranked: Iterable[Chunk],
    budget_tokens: int = 120,
    neighbors: Iterable[Chunk] | None = None,
) -> list[Chunk]:
    """Deduplicate results, preserve hierarchy and add adjacent chunks within budget."""
    ranked = list(ranked)
    universe = list(neighbors or ())
    candidates: list[Chunk] = []
    for chunk in ranked:
        candidates.append(chunk)
        same_object = [
            candidate
            for candidate in universe
            if candidate.object_name == chunk.object_name and candidate.id != chunk.id
        ]
        headers = [
            candidate for candidate in same_object if candidate.procedure_name is None
        ]
        adjacent = sorted(
            (
                candidate
                for candidate in same_object
                if abs(candidate.line_start - chunk.line_end) <= 2
                or abs(chunk.line_start - candidate.line_end) <= 2
            ),
            key=lambda candidate: (candidate.line_start, candidate.id),
        )
        candidates.extend(headers)
        candidates.extend(adjacent)

    packed: list[Chunk] = []
    seen: set[str] = set()
    used = 0
    for chunk in candidates:
        tokens = estimate_tokens(chunk.text)
        if chunk.id in seen or used + tokens > budget_tokens:
            continue
        packed.append(chunk)
        seen.add(chunk.id)
        used += tokens
    return packed
