# Contributing

Thank you for improving search across 1C/BSL code.

## Development setup

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run the deterministic checks before opening a pull request:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src scripts tests
.venv/bin/python -m compileall -q src scripts tests
```

## Good contributions

- A small exported BSL fixture that reproduces a missed search result.
- Parser improvements with a focused regression test.
- Retrieval evaluation questions with an explicit target procedure and source.
- Documentation that makes installation or local use easier.

Do not submit proprietary configurations, credentials, personal data, or code
that you are not allowed to redistribute. Synthetic fixtures are preferred.

## Reporting retrieval quality

Include the query, expected procedure, retrieval engine, project revision, and
a minimal redistributable fixture. A failed query is useful evidence; please do
not tune benchmarks by silently removing difficult cases.
