# url-fetcher

CLI Python para enriquecer listados de URLs con datos HTTP y SEO en paralelo.

## Estado

v0.9.0 - en desarrollo.

## Funcionalidad prevista

- ✅ Modo básico: status, content-type, redirects, response time.
- ✅ Concurrencia: peticiones en paralelo con asyncio + httpx.
- ✅ Inputs: TXT, CSV, JSON, XLSX.
- ✅ Limpieza de input: deduplicación y validación automática.
- ✅ Outputs: CSV y JSON con timestamp.
- ✅ Resumen estadístico por status_code y content_type.
- ✅ Modo SEO: title, meta description, canonical, robots, h1s, lang, og:*, status_index.
- ✅ Barra de progreso con tiempo estimado durante el rastreo.
- ✅ Comprobación de robots.txt con cache por dominio.
- ✅ Indexability completa estilo Screaming Frog (Indexable, Non-Indexable, motivo).

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

Input desde Excel:

    uv run url-fetcher datos.xlsx --mode seo

Output en JSON:

    uv run url-fetcher urls.csv --mode seo --format json
    uv run url-fetcher urls.csv --mode seo -o resultado.json

Respetar robots.txt (URLs bloqueadas se marcan sin generar petición):

    uv run url-fetcher urls.csv --mode seo --respect-robots

Limitaciones del modo SEO:
- Solo parsea HTML estático. No ejecuta JavaScript.
- Sites tipo SPA (React/Vue/Angular sin SSR) devolverán campos vacíos.
- Body se trunca a 2 MB (no se parsea, pero size_kb sí se rellena).

Pendiente: XLSX, JSON output.

## Licencia

MIT.
