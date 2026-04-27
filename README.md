# url-fetcher

CLI Python para enriquecer listados de URLs con datos HTTP y SEO en paralelo.

## Estado

v0.3.0 - en desarrollo.

## Funcionalidad prevista

- ✅ Modo básico: status, content-type, redirects, response time.
- ✅ Concurrencia: peticiones en paralelo con asyncio + httpx.
- ✅ Inputs: TXT, CSV, JSON (XLSX pendiente).
- ⬜ Outputs: CSV / JSON.
- ⬜ Modo SEO: title, meta description, canonical, robots, h1s.

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

Pendiente: output a archivo, modo SEO, XLSX.

## Licencia

MIT.
