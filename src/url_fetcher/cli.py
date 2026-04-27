"""Punto de entrada CLI de url-fetcher."""

import argparse

from url_fetcher.fetcher import fetch_url
from url_fetcher.models import UrlResult


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
        description="Enriquece una URL con datos HTTP del modo básico.",
    )
    parser.add_argument("url", help="URL a procesar")
    args = parser.parse_args()

    result = fetch_url(args.url)
    _print_result(result)
