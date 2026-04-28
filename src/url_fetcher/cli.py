"""Punto de entrada CLI de url-fetcher."""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from url_fetcher.fetcher import fetch_all
from url_fetcher.input_loader import load_urls
from url_fetcher.models import UrlResult
from url_fetcher.output_writer import generate_default_output_path, write_csv
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

UNSUPPORTED_OUTPUT_EXTS = {".json", ".xlsx"}


def _fmt(value: object) -> str:
    return "-" if value is None else str(value)


def _print_result(result: UrlResult) -> None:
    print(f"URL: {result.url}")
    if result.error is not None:
        print(f"Error: {result.error}")
        return
    print(f"Final URL: {_fmt(result.final_url)}")
    print(f"Status: {_fmt(result.status_code)}")
    print(f"Content-Type: {_fmt(result.content_type)}")
    print(f"Response time: {_fmt(result.response_time_ms)} ms")
    print(f"Redirect URL: {_fmt(result.redirect_url)}")
    print(f"Redirect count: {result.redirect_count}")


def _format_unsupported(fmt: str) -> str:
    return (
        f"Error: formato '{fmt}' no soportado todavía. "
        f"Soportados: csv. (json/xlsx vendrán en commits futuros)"
    )


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
    # Windows usa cp1252 para stdout por defecto y mata los acentos de los
    # mensajes en español. reconfigure() solo existe en TextIOWrapper, así
    # que lo envolvemos en try para no romper si stdout está redirigido.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
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
        default=None,
        help="Formato de salida (solo 'csv' por ahora)",
    )
    args = parser.parse_args()

    if args.format is not None and args.format.lower() != "csv":
        print(_format_unsupported(args.format))
        sys.exit(1)

    if args.output is not None:
        suffix = args.output.suffix.lower()
        if suffix in UNSUPPORTED_OUTPUT_EXTS:
            print(_format_unsupported(suffix.lstrip(".")))
            sys.exit(1)

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
    results = asyncio.run(fetch_all(clean.valid_unique))
    elapsed = time.perf_counter() - start

    if is_batch:
        # En batch no inundamos la consola con un resultado por URL; el CSV
        # es la fuente de verdad. Si el usuario no especificó -o, usamos el
        # path con timestamp en output/.
        output_path = args.output if args.output else generate_default_output_path("csv")
        write_csv(results, output_path)
    else:
        for i, result in enumerate(results):
            if i > 0:
                print()
            _print_result(result)
        print()
        if args.output is not None:
            write_csv(results, args.output)
            output_path = args.output
        else:
            output_path = None

    show_breakdowns = len(results) > 1
    print(format_summary(results, clean, elapsed, output_path, show_breakdowns))


if __name__ == "__main__":
    sys.exit(main())
