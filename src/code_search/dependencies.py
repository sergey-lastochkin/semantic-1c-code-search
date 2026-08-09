import re
from dataclasses import dataclass, field

from .models import Chunk
from .parser import BSLParser


@dataclass
class DependencyGraph:
    edges: dict[str, set[str]] = field(default_factory=dict)

    def add_chunk(self, parser: BSLParser, chunk: Chunk) -> None:
        self.edges.setdefault(chunk.context_path, set()).update(
            f"{chunk.object_name}/{call}" for call in parser.calls(chunk)
        )

    def mermaid(self) -> str:
        return "graph TD\n" + "\n".join(
            f'  {re.sub(r"\\W", "_", source)}["{source}"] --> {re.sub(r"\\W", "_", target)}["{target}"]'
            for source, targets in sorted(self.edges.items())
            for target in sorted(targets)
        )

    def dot(self) -> str:
        return (
            "digraph dependencies {\n"
            + "\n".join(
                f'  "{source}" -> "{target}";'
                for source, targets in self.edges.items()
                for target in targets
            )
            + "\n}"
        )
