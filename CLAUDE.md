# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Proyecto: url-fetcher

CLI Python async para auditorías SEO técnicas. Recibe listas de URLs (CSV/TXT/JSON/XLSX) y devuelve datos HTTP y SEO de cada una. Versión actual: 1.0.0.

## Comandos comunes

- `uv sync` — instalar dependencias y crear el entorno.
- `uv run url-fetcher --help` — ver todas las flags disponibles.
- `uv run url-fetcher --demo --mode seo` — smoke test estándar tras cada feature.
- `uv run ruff check .` — pasar el linter (obligatorio antes de cada commit).
- `uv run ruff format .` — formatear el código.

No hay suite de tests automatizada (no hay `pytest` en `dev-deps`). La verificación es manual: ejecutar con `--demo` y revisar el CSV/JSON generado en `output/`.

## Arquitectura / flujo de datos

`cli.py` orquesta el pipeline en este orden: `input_loader` → `url_cleaner` → `fetch_all` → `output_writer` + `summary`.

- **Concurrencia (`fetcher.py`)**: un único `httpx.AsyncClient` compartido + `asyncio.Semaphore(concurrency)` que limita peticiones en vuelo. `asyncio.gather` recoge resultados respetando el orden de entrada (clave para alinear input ↔ output).

- **Por URL (`fetch_url`)**: aplica reintentos solo en errores de red transitorios (`TimeoutException`, `NetworkError`, `RemoteProtocolError`) con backoff exponencial 1s/2s/4s… tope 30s. **NO** reintenta status codes 4xx/5xx (son respuestas válidas) ni errores SSL (no se arreglan reintentando).

- **Robots.txt**: si `--respect-robots`, `RobotsChecker` (con cache) corta antes de hacer la petición HTTP; las URLs bloqueadas se marcan sin red.

- **Modo SEO**: tras la respuesta, `parse_html` (selectolax) rellena los campos SEO; después `compute_indexability` decide `Indexable`/`Non-Indexable` combinando status, `meta_robots`, `X-Robots-Tag`, y comparando `canonical` vs `final_url`.

- **Output**: `output_writer` escribe CSV (`utf-8-sig`, separador configurable con `--sep`) o JSON (`ensure_ascii=False`). `summary.py` imprime los desgloses finales por status, content-type e indexability.

## Stack confirmado

- Python 3.12 con uv
- httpx con AsyncClient + asyncio.Semaphore para concurrencia controlada
- selectolax para parsing HTML (NO BeautifulSoup)
- argparse de stdlib para CLI
- rich.progress para barras de progreso
- openpyxl para XLSX
- ruff con line-length 100, reglas E, W, F, I, UP, B, C4, SIM

## Estructura del código

- src/url_fetcher/cli.py: argparse + orquestación del flujo 
- src/url_fetcher/input_loader.py: lectura TXT/CSV/JSON/XLSX
- src/url_fetcher/url_cleaner.py: deduplicación y validación
- src/url_fetcher/fetcher.py: núcleo asíncrono httpx + Semaphore
- src/url_fetcher/parser.py: extracción SEO con selectolax
- src/url_fetcher/robots.py: comprobación robots.txt con cache
- src/url_fetcher/output_writer.py: escritura CSV/JSON
- src/url_fetcher/summary.py: resumen estadístico final
- src/url_fetcher/models.py: dataclass UrlResult (24 campos)

## Convenciones del proyecto

- Conventional Commits siempre.
- Outputs en output/ (en gitignore, NO commitear).
- Datos reales fuera del repo en ~/auditorias-seo/inputs|outputs/.
- Encoding utf-8-sig en CSV (Windows español).
- ensure_ascii=False en JSON.
- Type hints modernos: str | None, no Optional[str].
- Versión en src/url_fetcher/__init__.py, leer dinámicamente para User-Agent.

## Cómo trabajamos

- Plan mode obligatorio para cambios no triviales.
- Pasar plan literal al usuario antes de ejecutar.
- Verificación manual tras cada commit.
- Smoke test después de cada feature: ejecutar con --demo y revisar output.
- Pasar ruff antes de cada commit.

## Conceptos del autor que NO domina (explícale antes de usarlos)

- Decoradores
- Clases / OOP completa
- Tests con pytest
- APIs autenticadas (OAuth)
- Logging estructurado
- mypy (type checking estricto)

## Próxima fase

Fase A del roadmap: extensiones del modo SEO. Hreflang, schema markup,
link counts, image audit, reading score, OpenGraph completo, redirect chains.
Quick wins, 6-8 commits.