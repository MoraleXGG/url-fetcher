# url-fetcher

CLI Python para enriquecer listados de URLs con datos HTTP y SEO en paralelo.

## Estado

v0.2.0 - en desarrollo.

## Funcionalidad prevista

- ✅ Modo básico: status, content-type, redirects, response time.
- ✅ Concurrencia: peticiones en paralelo con asyncio + httpx.
- ⬜ Inputs: CSV / JSON / XLSX / TXT / stdin.
- ⬜ Outputs: CSV / JSON.
- ⬜ Modo SEO: title, meta description, canonical, robots, h1s.

## Stack

Python 3.12 · httpx · selectolax · rich · openpyxl · gestionado con uv.

## Instalación

Pendiente de documentar.

## Uso

Una sola URL:

    uv run url-fetcher https://example.com

Demo con varias URLs en paralelo:

    uv run url-fetcher --demo

Pendiente de documentar el resto cuando esté implementado.

## Licencia

MIT.
