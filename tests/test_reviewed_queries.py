import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parents[1] / "scripts"))
from run_embedding_benchmark import raw_rankings, resolve_natural_queries

from code_search.models import Chunk


def chunk(path: str) -> Chunk:
    return Chunk(id=path, text="body", context_path=path)


def test_reviewed_query_resolver_keeps_only_reviewed_rows(tmp_path):
    query_path = tmp_path / "queries.json"
    query_path.write_text(
        json.dumps(
            {
                "metadata": {"dataset_id": "test-v2"},
                "queries": [
                    {
                        "id": "kept",
                        "query": "проверенный вопрос",
                        "review_status": "reviewed",
                        "expected_relevant_paths": ["Source/Module/Target"],
                    },
                    {
                        "id": "dropped",
                        "query": "слишком простой вопрос",
                        "review_status": "excluded",
                        "exclusion_reason": "name-level",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows, metadata = resolve_natural_queries(query_path, [chunk("Source/Module/Target")])

    assert [row["id"] for row in rows] == ["kept"]
    assert metadata["reviewed_query_count"] == 1
    assert metadata["excluded_query_ids"] == ["dropped"]


def test_reviewed_query_resolver_rejects_unreviewed_or_unexplained_rows(tmp_path):
    query_path = tmp_path / "queries.json"
    query_path.write_text(
        json.dumps({"metadata": {}, "queries": [{"id": "bad", "query": "x", "review_status": "pending"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not reviewed"):
        resolve_natural_queries(query_path, [])


def test_raw_rankings_keep_paths_in_query_and_ranked_result():
    expected = chunk("Source/Module/Target")

    class Searchable:
        def search(self, _query, _limit):
            return [expected]

    class Graph:
        def search_context(self, _query, _limit):
            return [expected]

    class Prepared:
        def __init__(self, value):
            self.value = value

    rankings = raw_rankings(
        {
            "exact": Prepared({"вопрос": expected}),
            "bm25": Prepared(Searchable()),
            "embedding": Prepared(Searchable()),
            "rrf": Prepared((Searchable(), Searchable())),
            "graph": Prepared(Graph()),
        },
        [{"id": "one", "query": "вопрос", "expected_paths": [expected.context_path]}],
    )

    assert rankings[0]["expected_paths"] == [expected.context_path]
    assert rankings[0]["ranking"]["bm25"] == [expected.context_path]
