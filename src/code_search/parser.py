"""Static, conservative BSL parser. It never executes 1C code."""

import re
from hashlib import sha256

from .models import BSLUnit, Chunk

HEADER = re.compile(
    r"(?im)^\s*(Процедура|Функция)\s+([\wА-Яа-яЁё]+)\s*\((.*?)\)\s*(Экспорт)?\s*$"
)
END = re.compile(r"(?im)^\s*Конец(?:Процедуры|Функции)\s*$")
QUERY = re.compile(r'(?is)(?:Запрос\.Текст|ТекстЗапроса)\s*=\s*["\'](.*?)["\']')
METADATA = re.compile(
    r"\b(Справочники|Документы|РегистрыНакопления|РегистрыСведений|Перечисления)\.([\wА-Яа-яЁё]+)"
)
CALL = re.compile(r"\b([\wА-Яа-яЁё]+)\s*\(")
KEYWORDS = {"Если", "Для", "Пока", "Функция", "Процедура", "Возврат", "Запрос"}


class BSLParser:
    def parse(self, text: str) -> list[BSLUnit]:
        lines, units = text.splitlines(), []
        for match in HEADER.finditer(text):
            start = text[: match.start()].count("\n")
            end_match = END.search(text, match.end())
            end = text[: end_match.end()].count("\n") if end_match else len(lines) - 1
            body = "\n".join(lines[start : end + 1])
            refs = tuple(
                sorted({f"{kind}.{name}" for kind, name in METADATA.findall(body)})
            )
            units.append(
                BSLUnit(
                    match.group(1).lower(),
                    match.group(2),
                    match.group(3).strip(),
                    bool(match.group(4)),
                    start + 1,
                    end + 1,
                    body,
                    tuple(QUERY.findall(body)),
                    refs,
                )
            )
        return units

    def chunks(
        self, text: str, strategy: str = "procedure_aware", **metadata: str
    ) -> list[Chunk]:
        base = self._base_metadata(metadata)
        if strategy in {"fixed", "fixed_overlap"}:
            return self.fixed(
                text, 120, 20 if strategy == "fixed_overlap" else 0, strategy, base
            )
        units = self.parse(text)
        if strategy == "module_hierarchy":
            prefix_end = units[0].line_start - 1 if units else len(text.splitlines())
            prefix = "\n".join(text.splitlines()[:prefix_end]).strip()
            chunks = (
                [self._chunk(prefix, base, None, 1, prefix_end, False, strategy)]
                if prefix
                else []
            )
        elif strategy in {"procedure_aware", "structure_aware"}:
            chunks = []
        else:
            raise ValueError(f"unknown chunk strategy: {strategy}")
        return chunks + [
            self._chunk(
                unit.text,
                base,
                unit.name,
                unit.line_start,
                unit.line_end,
                unit.is_export,
                strategy,
                unit.metadata_refs,
            )
            for unit in units
        ]

    def fixed(
        self,
        text: str,
        size: int = 120,
        overlap: int = 0,
        strategy: str = "fixed",
        base: dict[str, str] | None = None,
    ) -> list[Chunk]:
        words, step, chunks = text.split(), max(1, size - overlap), []
        for offset in range(0, len(words), step):
            part = words[offset : offset + size]
            if not part:
                break
            chunks.append(
                self._chunk(
                    " ".join(part),
                    base or self._base_metadata({}),
                    None,
                    1,
                    1,
                    False,
                    strategy,
                )
            )
            if offset + size >= len(words):
                break
        return chunks

    def calls(self, chunk: Chunk) -> list[str]:
        return sorted(set(CALL.findall(chunk.text)) - KEYWORDS - {chunk.procedure_name})

    def _base_metadata(self, supplied: dict[str, str]) -> dict[str, str]:
        module_type = supplied.get("module_type", "CommonModule")
        return {
            "configuration": supplied.get("configuration", "DemoConfiguration"),
            "version": supplied.get("version", "synthetic-1"),
            "object_type": supplied.get("object_type", module_type),
            "object_name": supplied.get("object_name", "CommonModule.Demo"),
            "module_type": module_type,
        }

    def _chunk(
        self,
        text: str,
        base: dict[str, str],
        name: str | None,
        start: int,
        end: int,
        exported: bool,
        strategy: str,
        refs: tuple[str, ...] = (),
    ) -> Chunk:
        identifier = sha256(
            f"{base['object_name']}:{name}:{start}:{strategy}:{text}".encode()
        ).hexdigest()[:16]
        path = f"{base['object_name']}/{name}" if name else base["object_name"]
        return Chunk(
            identifier,
            text,
            **base,
            procedure_name=name,
            line_start=start,
            line_end=end,
            is_export=exported,
            context_path=path,
            strategy=strategy,
            metadata_refs=refs,
        )
