"""Punto de entrada CLI de url-fetcher."""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from url_fetcher.fetcher import fetch_all
from url_fetcher.input_loader import load_urls
from url_fetcher.models import UrlResult
from url_fetcher.output_writer import (
    generate_default_output_path,
    write_csv,
    write_json,
)
from url_fetcher.summary import format_summary
from url_fetcher.url_cleaner import clean_urls


DEMO_URLS = [
    "https://tipsanalistas.com",
    "https://www.google.com",
    "https://github.com",
    "https://httpbin.org/status/200",
    "https://httpbin.org/status/404",
    "https://httpbin.org/status/500",
    "https://httpbin.org/redirect/2",
    "https://httpbin.org/delay/1",
    "https://no-existe-este-dominio-12345.com",
    "https://www.wikipedia.org",
]

_OUTPUT_EXT_TO_FORMAT = {".csv": "csv", ".json": "json"}
# Extensiones que indican un formato de salida que NO soportamos todavía.
_UNSUPPORTED_OUTPUT_EXTS = {".xlsx", ".xlsm"}


def _fmt(value: object) -> str:
    return "-" if value is None else str(value)


def _print_result(result: UrlResult) -> None:
    print(f"URL: {result.url}")
    if result.error is not None:
        print(f"Error: {result.error}")
        # En modo SEO calculamos indexability incluso para errores de red o
        # bloqueos por robots; si está rellenada, la imprimimos junto al error.
        if result.indexability is not None:
            print(f"Indexability: {_fmt(result.indexability)}")
            print(f"Indexability status: {_fmt(result.indexability_status)}")
        return
    print(f"Final URL: {_fmt(result.final_url)}")
    print(f"Status: {_fmt(result.status_code)}")
    print(f"Content-Type: {_fmt(result.content_type)}")
    print(f"Response time: {_fmt(result.response_time_ms)} ms")
    print(f"Redirect URL: {_fmt(result.redirect_url)}")
    print(f"Redirect count: {result.redirect_count}")

    # indexability solo se rellena en modo SEO; lo usamos como indicador de
    # que merece la pena imprimir el resto de campos SEO.
    if result.indexability is None and result.size_kb is None:
        return
    print(f"Indexability: {_fmt(result.indexability)}")
    print(f"Indexability status: {_fmt(result.indexability_status)}")
    print(f"Title: {_fmt(result.title)}")
    print(f"Meta description: {_fmt(result.meta_description)}")
    print(f"Canonical: {_fmt(result.canonical)}")
    print(f"Meta robots: {_fmt(result.meta_robots)}")
    print(f"X-Robots-Tag: {_fmt(result.x_robots_tag)}")
    print(f"H1: {_fmt(result.h1)}")
    print(f"H1 count: {_fmt(result.h1_count)}")
    print(f"H2 count: {_fmt(result.h2_count)}")
    print(f"Lang: {_fmt(result.lang)}")
    print(f"OG title: {_fmt(result.og_title)}")
    print(f"OG description: {_fmt(result.og_description)}")
    print(f"Word count: {_fmt(result.word_count)}")
    print(f"Size: {_fmt(result.size_kb)} KB")
    print(f"Last-Modified: {_fmt(result.last_modified)}")


def _resolve_output_format(format_arg: str | None, output_path: Path | None) -> str:
    """Decide el formato de salida coherente entre --format y la extensión de -o.

    - Si la extensión no es soportada para output (xlsx) → error y exit 1.
    - Si --format se pasa y choca con la extensión inferida → error y exit 1.
    - Si solo hay extensión: la usamos.
    - Si no hay nada: csv (default).
    """
    inferred: str | None = None
    if output_path is not None:
        suffix = output_path.suffix.lower()
        if suffix in _UNSUPPORTED_OUTPUT_EXTS:
            print(
                f"Error: formato '{suffix.lstrip('.')}' no soportado para output. "
                f"Soportados: csv, json.",
                file=sys.stderr,
            )
            sys.exit(1)
        inferred = _OUTPUT_EXT_TO_FORMAT.get(suffix)

    if format_arg is None:
        return inferred or "csv"

    if inferred is not None and inferred != format_arg:
        print(
            f"Error: --format '{format_arg}' no coincide con la extensión "
            f"'{output_path.suffix}' de --output. Usa una sola opción coherente.",
            file=sys.stderr,
        )
        sys.exit(1)

    return format_arg


def _write_output(results: list[UrlResult], path: Path, output_format: str) -> None:
    if output_format == "csv":
        write_csv(results, path)
    elif output_format == "json":
        write_json(results, path)


def _resolve_input(value: str, url_column: str | None) -> list[str]:
    """Convierte el argumento posicional en una lista de URLs.

    Hace exit(1) con mensaje claro (sin traceback) ante errores de E/S o de
    formato — la CLI nunca debería volcar un stack trace al usuario.
    """
    if value.startswith(("http://", "https://")):
        return [value]
    path = Path(value)
    if not path.exists():
        print(f"Error: '{value}' no es una URL válida ni un archivo existente")
        sys.exit(1)
    try:
        return load_urls(path, url_column=url_column)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)


def main() -> None:
    # Windows usa cp1252 para stdout/stderr por defecto y mata los acentos de
    # los mensajes en español. reconfigure() solo existe en TextIOWrapper, así
    # que lo envolvemos en try para no romper si están redirigidos.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    parser = argparse.ArgumentParser(
        prog="url-fetcher",
        description="Enriquece URLs con datos HTTP del modo básico.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        metavar="URL_OR_FILE",
        help="URL a procesar o ruta a archivo .txt/.csv/.json con URLs",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Procesa una lista hardcodeada de URLs en paralelo",
    )
    parser.add_argument(
        "--url-column",
        default=None,
        help="Nombre de la columna URL en CSV/JSON (auto-detect si se omite)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Ruta del archivo de salida (CSV). Default: output/url-fetcher_<ts>.csv para batch",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default=None,
        help="Formato de salida: csv (default) o json. Sobrescribe la extensión de -o.",
    )
    parser.add_argument(
        "--mode",
        choices=["basic", "seo"],
        default="basic",
        help="Modo de extracción: basic (solo headers) o seo (parsea HTML)",
    )
    parser.add_argument(
        "--respect-robots",
        action="store_true",
        help="Comprobar robots.txt antes de pedir cada URL; las bloqueadas se marcan sin generar petición HTTP",
    )
    args = parser.parse_args()

    output_format = _resolve_output_format(args.format, args.output)

    if not args.url and not args.demo:
        parser.error("se requiere una URL posicional o la flag --demo")

    if args.demo:
        raw_urls = DEMO_URLS
        is_batch = True
    else:
        # Antes de cargar, sabemos que es batch si el argumento NO es URL: el
        # _resolve_input ya validará que el archivo existe.
        is_batch = not args.url.startswith(("http://", "https://"))
        raw_urls = _resolve_input(args.url, args.url_column)
        if not raw_urls:
            print(f"No se encontraron URLs en {args.url}")
            sys.exit(1)

    clean = clean_urls(raw_urls)
    if not clean.valid_unique:
        print("Error: ninguna URL válida en el input.")
        sys.exit(1)

    start = time.perf_counter()
    results = asyncio.run(
        fetch_all(
            clean.valid_unique,
            mode=args.mode,
            show_progress=True,
            respect_robots=args.respect_robots,
        )
    )
    elapsed = time.perf_counter() - start

    if is_batch:
        # En batch no inundamos la consola con un resultado por URL; el archivo
        # es la fuente de verdad. Sin -o, usamos un path con timestamp en output/
        # con la extensión que corresponda al formato.
        output_path = (
            args.output
            if args.output
            else generate_default_output_path(output_format)
        )
        _write_output(results, output_path, output_format)
    else:
        for i, result in enumerate(results):
            if i > 0:
                print()
            _print_result(result)
        print()
        if args.output is not None:
            _write_output(results, args.output, output_format)
            output_path = args.output
        else:
            output_path = None

    show_breakdowns = len(results) > 1
    print(
        format_summary(
            results, clean, elapsed, output_path, show_breakdowns, mode=args.mode
        )
    )


if __name__ == "__main__":
    sys.exit(main())
