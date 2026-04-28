# url-fetcher

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

CLI Python para enriquecer listados de URLs con datos HTTP y SEO de forma concurrente. Pensada para auditorías SEO técnicas, validación de sitemaps y análisis de enlaces.

## Características

- **Modo básico**: status code, redirects, content-type, response time.
- **Modo SEO**: title, meta description, canonical, robots, h1s, OG tags, indexability completa al estilo Screaming Frog.
- **Concurrente**: peticiones en paralelo con `asyncio` + `httpx`. Procesa cientos de URLs en segundos.
- **Inputs flexibles**: TXT, CSV, JSON, XLSX, URL única, o stdin.
- **Outputs**: CSV (default) o JSON, ambos con encoding correcto para acentos.
- **Limpieza automática**: deduplica y descarta URLs malformadas del input.
- **Robots.txt opcional**: marca URLs bloqueadas sin generar petición HTTP.
- **Resumen estadístico**: desgloses por status code, content type e indexability.
- **Configurable**: timeout, retries, user-agent, concurrencia y separador CSV via flags.
- **Reintentos con backoff**: solo en errores transitorios de red, nunca en status codes.

## Instalación

Requiere Python 3.12+ y `uv` instalado.

```powershell
# Clonar el repositorio
git clone https://github.com/MoraleXGG/url-fetcher.git
cd url-fetcher

# Instalar dependencias y crear entorno virtual
uv sync

# Verificar instalación
uv run url-fetcher --help
```

## Uso

### Casos básicos

Una URL suelta (resultado por consola):

```powershell
uv run url-fetcher https://example.com
```

Modo SEO con extracción HTML completa:

```powershell
uv run url-fetcher https://example.com --mode seo
```

Procesar un listado de URLs desde archivo (genera CSV):

```powershell
uv run url-fetcher urls.csv --mode seo
uv run url-fetcher urls.txt
uv run url-fetcher urls.json --mode seo
uv run url-fetcher datos.xlsx --mode seo
```

Output JSON en lugar de CSV:

```powershell
uv run url-fetcher urls.csv --mode seo --format json
uv run url-fetcher urls.csv --mode seo -o resultado.json
```

Demo con 10 URLs precargadas (para probar la herramienta):

```powershell
uv run url-fetcher --demo --mode seo
```

### Configuración avanzada

Emular Googlebot:

```powershell
uv run url-fetcher urls.csv --user-agent "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
```

Concurrencia alta para sitios grandes:

```powershell
uv run url-fetcher urls.csv --concurrency 100
```

Timeout y reintentos para sitios inestables:

```powershell
uv run url-fetcher urls.csv --timeout 30 --retries 3
```

Respetar robots.txt (URLs bloqueadas se marcan sin petición HTTP):

```powershell
uv run url-fetcher urls.csv --mode seo --respect-robots
```

Separador CSV alternativo (Excel español):

```powershell
uv run url-fetcher urls.csv -o auditoria.csv --sep ";"
```

CSV con columna URL no estándar:

```powershell
uv run url-fetcher urls.csv --url-column "Source URL"
```

## Columnas del output

### Modo básico

| Columna | Descripción |
|---|---|
| `url` | URL original (la que se pasó como input). |
| `final_url` | URL final tras seguir redirects. |
| `status_code` | Código HTTP (200, 301, 404, 500, etc.). |
| `content_type` | Tipo MIME devuelto por el servidor. |
| `response_time_ms` | Tiempo de respuesta en milisegundos. |
| `redirect_url` | Primer destino de la cadena de redirects, si hay. |
| `redirect_count` | Número de saltos en la cadena de redirects. |
| `error` | Mensaje de error de red (DNS, timeout, etc.). Vacío si la petición tuvo éxito. |

### Modo SEO (incluye todas las anteriores más):

| Columna | Descripción |
|---|---|
| `indexability` | `Indexable`, `Non-Indexable` o vacío. |
| `indexability_status` | Razón si es Non-Indexable: `Blocked by Robots.txt`, `Noindex`, `Canonicalised`, `Client Error`, `Server Error`, `Connection Error`, `Redirected`. |
| `title` | Contenido de `<title>`. |
| `meta_description` | Contenido de `<meta name="description">`. |
| `canonical` | URL declarada en `<link rel="canonical">`. |
| `meta_robots` | Contenido de `<meta name="robots">`. |
| `x_robots_tag` | Header HTTP `X-Robots-Tag`. |
| `h1` | Primer `<h1>` de la página. |
| `h1_count` | Número total de `<h1>`. |
| `h1_all` | Todos los `<h1>` concatenados con `\|` (si hay más de uno). |
| `lang` | Atributo `lang` de `<html>`. |
| `og_title` | Contenido de `<meta property="og:title">`. |
| `og_description` | Contenido de `<meta property="og:description">`. |
| `h2_count` | Número de `<h2>` en la página. |
| `word_count` | Conteo aproximado de palabras (sin scripts ni styles). |
| `size_kb` | Peso de la respuesta en KB. |
| `last_modified` | Header HTTP `Last-Modified`, si lo envía el servidor. |

## Resumen tras el rastreo

Al terminar, la herramienta imprime un resumen con:

- Línea principal: totales, duplicadas, inválidas, procesadas, tiempo.
- Bloque "Por status code".
- Bloque "Por content type".
- Bloque "Por indexability" (solo en modo SEO).
- Bloque "Por motivo de no indexación" (solo en modo SEO, si hay Non-Indexable).
- Línea con la ruta del archivo de output.

Ejemplo:

```
--- Resumen ---
Totales: 685 | Duplicadas: 189 | Procesadas: 496 | Tiempo: 5.01s

Por status code:
  200: 496 (100.0%)

Por content type:
  text/html: 364 (73.4%)
  image/jpeg: 74 (14.9%)
  image/png: 42 (8.5%)
  text/xml: 16 (3.2%)

Por indexability:
  Indexable: 495 (99.8%)
  Non-Indexable: 1 (0.2%)

Por motivo de no indexación:
  Canonicalised: 1 (0.2%)

Output: output\url-fetcher_2026-04-28_034016.csv
```

## Convenciones recomendadas

Para mantener separados los datos de las herramientas, se recomienda esta estructura:

```
~/
├── proyectos/
│   └── url-fetcher/        # código de la herramienta
└── auditorias-seo/         # tus datos de trabajo
    ├── inputs/             # CSVs/sitemaps de clientes
    └── outputs/            # resultados de auditorías
```

Esto permite borrar y reinstalar la herramienta sin perder tus auditorías.

## Concurrencia: cómo elegir el valor óptimo

La concurrencia (peticiones simultáneas) tiene un punto óptimo que depende del servidor que se audita:

- **Sitios pequeños (WordPress, hosting compartido)**: 10-20 (default). Subir más puede sobrecargar el servidor.
- **Sitios medios (CMS dedicados, ecommerce)**: 30-50.
- **Sitios grandes (Wikipedia, prensa)**: 100+.

Si la herramienta tarda más con concurrencia alta, el cuello de botella es el servidor: bájala. Para encontrar el óptimo, prueba con varios valores y mide el tiempo.

## Limitaciones conocidas

- **No ejecuta JavaScript**. Sites tipo SPA puro (React/Vue/Angular sin SSR) devolverán campos SEO vacíos. La mayoría de sites profesionales tienen SSR para SEO, así que esto no aplica al uso típico.
- **El `response_time_ms` es indicativo, no exacto**. Varía según red, carga del servidor y caché. Para benchmarks precisos, hacer varias mediciones y promediar.
- **Body máximo en modo SEO: 2 MB por defecto**. Páginas más grandes no se parsean (configurable con `--max-body-size`).
- **Detección de columna URL en CSV/XLSX**: si hay varias columnas con "url" en el nombre, hay que especificar con `--url-column`.

## Stack técnico

- Python 3.12+
- `httpx` (async HTTP)
- `selectolax` (parsing HTML rápido)
- `rich` (barras de progreso y output)
- `openpyxl` (lectura XLSX)
- `urllib.robotparser` (stdlib, evaluación robots.txt)
- Gestión: `uv`

## Licencia

MIT. Ver el archivo [LICENSE](LICENSE) para los detalles.
