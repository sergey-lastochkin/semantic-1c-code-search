# Semantic 1C Code Search

English · [Русский](README.md)

[![CI](https://github.com/sergey-lastochkin/semantic-1c-code-search/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sergey-lastochkin/semantic-1c-code-search/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/sergey-lastochkin/semantic-1c-code-search)](https://github.com/sergey-lastochkin/semantic-1c-code-search/releases/latest)

**Offline search across exported 1C:Enterprise (BSL) code.** Point the CLI at a
configuration export, ask with words or a procedure name, and get the module,
procedure and line range. No running 1C platform is required and no code leaves
the machine.

![Searching 577 open-source BSL files from the terminal](assets/cli-demo.gif)

<sub>A real CLI recording on the open benchmark corpus. How to re-record:
[scripts/demo](scripts/demo/README.md).</sub>

## Problem

A typical 1C configuration contains tens of thousands of procedures. The
Designer's search and `grep` return every matching line without ranking. This
tool splits modules into procedures and functions, ranks whole procedures by
their name, parameters, variables, comments and strings, and returns a short
list with module paths and line numbers. The optional `hybrid` mode adds a local
multilingual embedding model for plain-language questions.

## Who it is for

- 1C developers who inherit an unfamiliar configuration.
- Leads and auditors who need every place related to payments, exchange or a
  specific register before estimating a change.
- Teams that cannot send source code to external AI services.

## Two-minute start

Windows PowerShell, prebuilt wheel:

```powershell
git clone --depth 1 https://github.com/sergey-lastochkin/semantic-1c-code-search.git
cd semantic-1c-code-search
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "https://github.com/sergey-lastochkin/semantic-1c-code-search/releases/download/v0.1.1/1c_semantic_code_search-0.1.1-py3-none-any.whl"
.\.venv\Scripts\code-search.exe search examples "СформироватьНазначениеПлатежа"
```

macOS and Linux, from source:

```bash
git clone https://github.com/sergey-lastochkin/semantic-1c-code-search.git
cd semantic-1c-code-search
python3.11 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/code-search search examples "СформироватьНазначениеПлатежа"
```

On your own export: `code-search search /path/to/config-export "таймаут соединения" --k 5`
(add `--json` for scripts).

## Example output

```text
$ code-search search corpus 'таймаут соединения' --k 3
1. Таймаут  [Connector/src/ru/CommonModules/КоннекторHTTP/Ext/Module:2035-2047]
   Функция Таймаут(ДополнительныеПараметры)

2. УстановитьТаймаут  [yaxunit/tests/src/CommonModules/Обр_ЮТHTTPСоединение_МО/Module:175-187]
   Процедура УстановитьТаймаут() Экспорт

3. КонструкторПоУмолчанию  [yaxunit/tests/src/CommonModules/Обр_ЮТHTTPСоединение_МО/Module:187-264]
   Процедура КонструкторПоУмолчанию() Экспорт
```

Also available: a static call graph (`code-search graph --format mermaid|dot|json`),
a saved index (`code-search index`), a local FastAPI interface and in-memory,
Qdrant local, FAISS and pgvector adapters.

## Benchmark

577 BSL files from three Apache-2.0 projects (Connector, YAxUnit, xUnitFor1C):
156,869 lines, 7,342 procedures and functions. Commit SHAs and per-file SHA-256
are in the [corpus manifest](studies/oss-bsl-corpus-2026-08-10/corpus-manifest.json).

| Query set | BM25 | Embeddings | RRF |
| --- | ---: | ---: | ---: |
| 90 deterministic checks (names, calls, metadata), Recall@5 | **0.856** | 0.640 | 0.830 |
| 29 reviewed Russian questions, Recall@5 | 0.138 | **0.345** | 0.276 |
| Same 29 questions, Recall@10 | 0.207 | 0.379 | **0.414** |

BM25 is strong on names; embeddings are 2.5× better on plain-language questions,
but the right procedure still lands in the top 5 only about a third of the time.
29 questions is a small set — treat it as a signal, not a final score.
[Methodology](docs/benchmark.md).

## Limitations

- The parser is static and heuristic; it does not replace the 1C compiler.
- Dynamic calls, preprocessor branches and extensions are only partly visible
  ([parser limits](docs/parser-limits.md)).
- BM25 matches whole lowercase words, without stemming or identifier splitting.
- The benchmark uses open libraries, not a commercial configuration.
- Python 3.11+ is required; there is no standalone executable yet.

## Author

Sergey Lastochkin — 1C and Python integrations and automation.
Telegram: [@metaanswer](https://t.me/metaanswer). License: [Apache 2.0](LICENSE).
