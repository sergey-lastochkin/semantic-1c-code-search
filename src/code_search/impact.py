"""Procedure and metadata links used for impact inspection and graph context."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .models import Chunk
from .parser import BSLParser


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    kind: str
    evidence: str


class ImpactGraph:
    """Conservative graph built from static procedure bodies, never from execution."""

    def __init__(self, chunks: list[Chunk], parser: BSLParser | None = None) -> None:
        self.chunks = {chunk.context_path: chunk for chunk in chunks}
        self.by_name: dict[str, list[Chunk]] = defaultdict(list)
        self.outbound: dict[str, list[Link]] = defaultdict(list)
        self.inbound: dict[str, list[Link]] = defaultdict(list)
        for chunk in chunks:
            if chunk.procedure_name:
                self.by_name[chunk.procedure_name.casefold()].append(chunk)
        self._link(parser or BSLParser())

    def _link(self, parser: BSLParser) -> None:
        seen: set[Link] = set()
        for chunk in self.chunks.values():
            for call in parser.calls(chunk):
                for target in self.by_name.get(call.casefold(), []):
                    self._add(Link(chunk.context_path, target.context_path, "call", call), seen)
            for reference in chunk.metadata_refs:
                self._add(Link(chunk.context_path, reference, "metadata", reference), seen)

    def _add(self, link: Link, seen: set[Link]) -> None:
        if link not in seen:
            seen.add(link)
            self.outbound[link.source].append(link)
            self.inbound[link.target].append(link)

    def affected_by(self, context_path: str, depth: int = 3) -> list[Link]:
        """Follow callers to show where a changed procedure can propagate."""
        queue = deque([(context_path, 0)])
        visited = {context_path}
        result: list[Link] = []
        while queue:
            target, level = queue.popleft()
            if level >= depth:
                continue
            for link in self.inbound.get(target, []):
                if link.source not in visited:
                    visited.add(link.source)
                    result.append(link)
                    queue.append((link.source, level + 1))
        return result

    def search_context(self, query: str, limit: int = 10) -> list[Chunk]:
        """Rank exact names and metadata matches, then add their immediate neighbours."""
        needle = query.casefold()
        scores: dict[str, int] = defaultdict(int)
        for path, chunk in self.chunks.items():
            if chunk.procedure_name and chunk.procedure_name.casefold() == needle:
                scores[path] += 8
            if needle in chunk.text.casefold():
                scores[path] += 2
            if any(needle == item.casefold() for item in chunk.metadata_refs):
                scores[path] += 5
        for path, score in list(scores.items()):
            if score:
                for link in self.outbound.get(path, []) + self.inbound.get(path, []):
                    if link.target in self.chunks:
                        scores[link.target] += 1
                    if link.source in self.chunks:
                        scores[link.source] += 1
        return [
            self.chunks[path]
            for path in sorted(scores, key=lambda key: (-scores[key], key))[:limit]
        ]

    def dot(self) -> str:
        rows = ["digraph bsl_dependencies {"]
        for source in sorted(self.outbound):
            for link in sorted(self.outbound[source], key=lambda item: (item.target, item.kind)):
                rows.append(
                    f'  "{link.source}" -> "{link.target}" [label="{link.kind}"];'
                )
        rows.append("}")
        return "\n".join(rows)
