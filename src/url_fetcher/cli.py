"""Punto de entrada CLI de url-fetcher."""

import argparse
import asyncio
import sys
import time

from url_fetcher.fetcher import fetch_all
from url_fetcher.models import UrlResult


DEMO_URLS = [
    "https://example.com",
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="url-fetcher",
        description="Enriquece URLs con datos HTTP del modo básico.",
    )
    parser.add_argument("url", nargs="?", help="URL a procesar")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Procesa una lista hardcodeada de URLs en paralelo",
    )
    args = parser.parse_args()

    if not args.url and not args.demo:
        parser.error("se requiere una URL posicional o la flag --demo")

    if args.demo:
        start = time.perf_counter()
        results = asyncio.run(fetch_all(DEMO_URLS))
        elapsed = time.perf_counter() - start

        for i, result in enumerate(results):
            if i > 0:
                print()
            _print_result(result)

        ok = sum(1 for r in results if r.error is None)
        errors = len(results) - ok
        print()
        print("--- Resumen ---")
        print(
            f"Procesadas: {len(results)} | OK: {ok} | "
            f"Errores: {errors} | Tiempo total: {elapsed:.2f}s"
        )
        return

    results = asyncio.run(fetch_all([args.url], concurrency=1))
    _print_result(results[0])


if __name__ == "__main__":
    sys.exit(main())
