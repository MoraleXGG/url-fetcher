# url-fetcher

CLI Python para enriquecer listados de URLs con datos HTTP y SEO en paralelo.

## Estado

v0.6.0 - en desarrollo.

## Funcionalidad prevista

- ✅ Modo básico: status, content-type, redirects, response time.
- ✅ Concurrencia: peticiones en paralelo con asyncio + httpx.
- ✅ Inputs: TXT, CSV, JSON (XLSX pendiente).
- ✅ Limpieza de input: deduplicación y validación automática.
- ✅ Outputs: CSV con timestamp automático (JSON pendiente).
- ✅ Resumen estadístico por status_code y content_type.
- ✅ Modo SEO: title, meta description, canonical, robots, h1s, lang, og:*, status_index.

## Stack

Python 3.12 · httpx · selectolax · rich · openpyxl · gestionado con uv.

## Instalación

Pendiente de documentar.

## Uso

Una URL suelta:

    uv run url-fetcher https://example.com

Demo con varias URLs en paralelo:

    uv run url-fetcher --demo

Desde un archivo:

    uv run url-fetcher urls.txt
    uv run url-fetcher urls.csv
    uv run url-fetcher urls.json

Especificando la columna URL en CSV/JSON:

    uv run url-fetcher urls.csv --url-column href

Output a CSV (auto-genera nombre con timestamp en `output/`):

    uv run url-fetcher urls.csv

Output a CSV con nombre concreto:

    uv run url-fetcher urls.csv -o auditoria.csv

Para una URL única, output sigue siendo por consola por defecto:

    uv run url-fetcher https://example.com

A no ser que pidas archivo:

    uv run url-fetcher https://example.com -o resultado.csv

Modo SEO (parsea HTML, extrae title, meta description, canonical, h1, etc.):

    uv run url-fetcher urls.csv --mode seo

Modo básico (default, solo headers HTTP):

    uv run url-fetcher urls.csv

Limitaciones del modo SEO:
- Solo parsea HTML estático. No ejecuta JavaScript.
- Sites tipo SPA (React/Vue/Angular sin SSR) devolverán campos vacíos.
- Body se trunca a 2 MB (no se parsea, pero size_kb sí se rellena).

Pendiente: XLSX, JSON output.

## Licencia

MIT.
