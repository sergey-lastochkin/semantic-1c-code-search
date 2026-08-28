import importlib.util
import json

import pytest
from fastapi.testclient import TestClient

from code_search.api import create_app
from code_search.backends import (
    InMemoryVectorBackend,
    PgVectorBackend,
    QdrantLocalBackend,
)
from code_search.cli import load, main
from code_search.context import context_pack
from code_search.dependencies import DependencyGraph
from code_search.embeddings import (
    DeterministicFakeEmbeddingProvider,
    LocalHashEmbeddingProvider,
)
from code_search.evaluation import evaluate, matryoshka_experiment
from code_search.parser import BSLParser
from code_search.retrieval import BM25Index, HybridRetriever, VectorIndex, rrf

TEXT = """// module header
Функция СформироватьНазначениеПлатежа(Документ) Экспорт
 Возврат Документы.Платежи.СоздатьДокумент();
КонецФункции
Процедура СоздатьПлатеж(Заявка) Экспорт
 Назначение = СформироватьНазначениеПлатежа(Заявка);
 Запрос.Текст = "ВЫБРАТЬ * ИЗ РегистрыНакопления.Остатки";
КонецПроцедуры
"""


def chunks(strategy="structure_aware"):
    return BSLParser().chunks(
        TEXT, strategy, object_name="Документ.Платеж", module_type="ObjectModule"
    )


def test_parser_extracts_signature_ranges_query_and_metadata():
    units = BSLParser().parse(TEXT)
    assert (units[0].name, units[0].signature, units[0].is_export) == (
        "СформироватьНазначениеПлатежа",
        "Документ",
        True,
    )
    assert (
        units[1].line_start > units[0].line_start
        and "РегистрыНакопления.Остатки" in units[1].queries[0]
    )


def test_all_chunk_strategies_and_metadata():
    parsed = BSLParser()
    for strategy in (
        "fixed",
        "fixed_overlap",
        "procedure_aware",
        "module_hierarchy",
        "structure_aware",
    ):
        assert parsed.chunks(TEXT, strategy)
    assert chunks()[0].context_path.endswith("СформироватьНазначениеПлатежа")


def test_bm25_vector_hybrid_rrf_and_filters():
    data = chunks()
    provider = LocalHashEmbeddingProvider()
    bm25 = BM25Index(data)
    assert bm25.search("назначение")
    ranked = bm25.ranked("назначение")
    assert ranked[0][0] > 0 and ranked[0][1] == bm25.search("назначение")[0]
    assert VectorIndex(data, provider, backend=InMemoryVectorBackend()).search(
        "назначение", filters={"object_name": "Документ.Платеж"}
    )
    assert len(HybridRetriever(data, provider).search("назначение")) == 2
    assert len(rrf([data, data[::-1]])) == 2


def test_real_qdrant_local_mode_filters():
    pytest.importorskip(
        "qdrant_client", reason="optional qdrant extra is not installed"
    )
    data = chunks()
    index = VectorIndex(
        data, LocalHashEmbeddingProvider(), backend=QdrantLocalBackend()
    )
    result = index.search("назначение", filters={"object_name": "Документ.Платеж"})
    assert result and all(row.object_name == "Документ.Платеж" for row in result)


def test_qdrant_missing_extra_has_actionable_error():
    if importlib.util.find_spec("qdrant_client") is not None:
        pytest.skip("boundary is exercised in the minimal dependency environment")
    with pytest.raises(RuntimeError, match=r"\[qdrant\]"):
        QdrantLocalBackend()


def test_pgvector_emits_real_extension_table_upsert_and_search_sql():
    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))

        def fetchall(self):
            return [(chunks()[0].metadata(),)]

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()
            self.committed = False

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            self.committed = True

        def rollback(self):
            raise AssertionError("rollback not expected")

        def close(self):
            pass

    connections = []

    def connect():
        connection = Connection()
        connections.append(connection)
        return connection

    backend = PgVectorBackend(connect)
    backend.upsert(chunks(), LocalHashEmbeddingProvider(), 256)
    result = backend.search(
        "назначение",
        LocalHashEmbeddingProvider(),
        filters={"object_name": "Документ.Платеж"},
    )
    assert connections[0].committed and any(
        "CREATE EXTENSION" in sql for sql, _ in connections[0].cursor_instance.calls
    )
    assert any("<=>" in sql for sql, _ in connections[1].cursor_instance.calls)
    assert result[0].object_name == "Документ.Платеж"


def test_metrics_context_dependencies_and_experiment():
    data = chunks()
    graph = DependencyGraph()
    for row in data:
        graph.add_chunk(BSLParser(), row)
    assert (
        "СформироватьНазначениеПлатежа" in graph.mermaid() and "digraph" in graph.dot()
    )
    assert sum(len(row.text.split()) for row in context_pack(data, 20)) <= 20
    assert evaluate(data, [data[1].id])["recall@3"] == 1
    assert [
        row["dimension"]
        for row in matryoshka_experiment(
            data, [{"query": "назначение", "relevant_ids": [data[0].id]}]
        )
    ] == [256, 256, 256, 256, 128]


def test_fake_is_test_double_and_api_smoke():
    fake = DeterministicFakeEmbeddingProvider()
    assert len(fake.truncate(fake.embed("x"), 128)) == 128
    client = TestClient(create_app())
    indexed = client.post("/index", json={"source": TEXT}).json()
    assert indexed["chunks"] == 2
    assert (
        len(client.post("/search", json={"query": "назначение"}).json()["results"]) == 2
    )
    retrieved = client.post(
        "/retrieve", json={"query": "назначение", "token_budget": 200}
    ).json()
    assert retrieved["estimated_tokens"] <= 200 and retrieved["chunks"]
    experiment = client.post(
        "/experiments/run",
        json={
            "questions": [{"query": "назначение", "relevant_ids": [indexed["ids"][0]]}]
        },
    ).json()
    assert (
        experiment["rows"]
        and client.get("/experiments").json()[0]["id"] == experiment["id"]
    )
    assert create_app().openapi()["info"]["title"] == "Offline 1C semantic code search"


def test_cli_searches_a_directory_and_prints_locations(tmp_path, capsys):
    nested = tmp_path / "CommonModules" / "Payments"
    nested.mkdir(parents=True)
    (nested / "Module.bsl").write_text(TEXT, encoding="utf-8-sig")

    indexed = load(tmp_path)
    assert len(indexed) == 3
    assert indexed[0].object_name == "CommonModules/Payments/Module"

    main(["search", str(tmp_path), "СформироватьНазначениеПлатежа", "--k", "1"])
    output = capsys.readouterr().out
    assert "СформироватьНазначениеПлатежа" in output
    assert "CommonModules/Payments/Module" in output


def test_cli_json_output_remains_available(tmp_path, capsys):
    source = tmp_path / "Module.bsl"
    source.write_text(TEXT, encoding="utf-8")

    main(["search", str(source), "СформироватьНазначениеПлатежа", "--json"])
    output = json.loads(capsys.readouterr().out)
    assert output[0]["procedure_name"] == "СформироватьНазначениеПлатежа"
