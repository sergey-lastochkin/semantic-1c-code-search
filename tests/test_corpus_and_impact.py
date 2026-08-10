from code_search.impact import ImpactGraph
from code_search.parser import BSLParser

TEXT = """Функция Помощник() Экспорт
 Возврат Справочники.Товары.ПустаяСсылка();
КонецФункции
Процедура Вход() Экспорт
 Помощник();
КонецПроцедуры
"""


def test_impact_graph_resolves_calls_metadata_and_callers():
    chunks = BSLParser().chunks(TEXT, "structure_aware", object_name="Demo")
    graph = ImpactGraph(chunks)
    entry = next(chunk for chunk in chunks if chunk.procedure_name == "Вход")
    helper = next(chunk for chunk in chunks if chunk.procedure_name == "Помощник")
    assert any(link.target == helper.context_path for link in graph.outbound[entry.context_path])
    assert graph.affected_by(helper.context_path)[0].source == entry.context_path
    assert graph.search_context("Справочники.Товары")[0].procedure_name == "Помощник"
