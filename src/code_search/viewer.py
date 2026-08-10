"""A small read-only viewer for a locally checked-out BSL corpus."""

from __future__ import annotations

from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .models import Chunk
from .retrieval import BM25Index


def create_viewer(chunks: list[Chunk], file_count: int) -> FastAPI:
    """Expose a browser page backed by actual BM25 results from ``chunks``."""
    app = FastAPI(title="BSL corpus viewer", docs_url=None, redoc_url=None)
    index = BM25Index(chunks)

    @app.get("/", response_class=HTMLResponse)
    def page(q: str = "HTTP запрос", k: int = 5) -> str:
        limit = min(max(k, 1), 10)
        rows = index.ranked(q, limit)
        results = "".join(
            f"""
            <article>
              <div class=rank>#{position} · BM25 {score:.4f}</div>
              <h2>{escape(chunk.procedure_name or "Модуль")}</h2>
              <p class=path>{escape(chunk.context_path)}</p>
              <p class=lines>строки {chunk.line_start}–{chunk.line_end}</p>
              <pre>{escape(_preview(chunk.text))}</pre>
            </article>"""
            for position, (score, chunk) in enumerate(rows, 1)
        ) or "<p class=empty>Совпадений нет.</p>"
        return f"""<!doctype html>
<html lang=\"ru\"><meta charset=\"utf-8\"><title>Поиск по BSL-корпусу</title>
<style>
body {{ margin: 0; background: #f6f8fa; color: #1f2328; font: 18px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 48px 36px 64px; }}
h1 {{ margin: 0 0 8px; font-size: 34px; }} .meta {{ color: #57606a; margin: 0 0 30px; }}
form {{ display: flex; gap: 12px; margin-bottom: 30px; }} input {{ flex: 1; min-width: 0; font: inherit; padding: 12px 14px; border: 1px solid #8c959f; border-radius: 6px; }}
button {{ background: #0969da; border: 0; border-radius: 6px; color: white; font: inherit; padding: 12px 20px; }}
article {{ background: white; border: 1px solid #d0d7de; border-radius: 8px; padding: 18px 22px; margin: 14px 0; }}
h2 {{ margin: 5px 0; font-size: 22px; }} .rank {{ color: #0969da; font-weight: 650; }} .path {{ color: #0550ae; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; margin: 6px 0; }} .lines {{ color: #57606a; margin: 4px 0; }}
pre {{ margin: 12px 0 0; padding: 12px; background: #f6f8fa; border-radius: 6px; overflow: hidden; white-space: pre-wrap; font: 14px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; }}
</style><body><main>
<h1>Поиск по BSL-корпусу</h1>
<p class=meta>Локальный read-only просмотр · BM25 · {file_count} BSL-файлов · {len(chunks)} процедур и функций</p>
<form method=get><input aria-label=\"Поисковый запрос\" name=q value=\"{escape(q, quote=True)}\"><button>Искать</button></form>
<section aria-label=\"Результаты поиска\">{results}</section>
</main></body></html>"""

    return app


def _preview(text: str, limit: int = 360) -> str:
    compact = "\n".join(line.rstrip() for line in text.splitlines()[:12]).strip()
    return compact[:limit] + ("…" if len(compact) > limit else "")
