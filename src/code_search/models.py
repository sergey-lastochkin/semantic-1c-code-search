from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BSLUnit:
    kind: str
    name: str
    signature: str
    is_export: bool
    line_start: int
    line_end: int
    text: str
    queries: tuple[str, ...] = ()
    metadata_refs: tuple[str, ...] = ()


@dataclass
class Chunk:
    id: str
    text: str
    configuration: str = "Unspecified"
    version: str = "unversioned"
    object_type: str = "CommonModule"
    object_name: str = "CommonModule.Demo"
    module_type: str = "CommonModule"
    procedure_name: str | None = None
    line_start: int = 1
    line_end: int = 1
    is_export: bool = False
    context_path: str = "CommonModule.Demo"
    strategy: str = "procedure_aware"
    metadata_refs: tuple[str, ...] = ()

    def metadata(self) -> dict[str, Any]:
        return asdict(self)
