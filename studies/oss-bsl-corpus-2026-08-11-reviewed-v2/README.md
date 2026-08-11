# Reviewed natural-language benchmark V2

Это неизменяемый артефакт локального прогона от 2026-08-11. Код прогона: `3374897332d7003d7c37812425df16d12a77d33b`; модель: `intfloat/multilingual-e5-small` revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 измерения, CPU.

## Состав и review

- 577 BSL-файлов, 156869 строк, 7342 procedure/function chunks из трёх public Apache-2.0 источников;
- 42 русских запроса просмотрены по исходному BSL-коду: 29 `reviewed`, 13 `excluded` как прямые name-level обёртки;
- `natural-language-queries-v2.json` — точный query source и причины исключения;
- `review-ledger.md` — читаемая сводка review;
- `natural-language-query-rankings.jsonl` — один JSON-объект на reviewed запрос: expected path и top-10 по exact-name, BM25, embeddings, RRF и graph-context.

`embedding-results.json` хранит агрегированные метрики, runtime, hashes и pin модели. `sources.json` и `corpus-manifest.json` сохраняют публичные source commits и file hashes. Графики производны только от результатов этого каталога.

## Результат reviewed V2

| Метод | Recall@5 | Recall@10 | MRR@10 | nDCG@10 | p95, мс |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.137931 | 0.206897 | 0.074904 | 0.105190 | 17.8359 |
| embeddings | 0.344828 | 0.379310 | 0.257800 | 0.287090 | 15.6467 |
| BM25 + embeddings через RRF | 0.275862 | 0.413793 | 0.144089 | 0.206671 | 28.8557 |

Это один локальный CPU-прогон на зафиксированном открытом корпусе, не CI benchmark и не проверка выполнения кода в платформе 1С.
