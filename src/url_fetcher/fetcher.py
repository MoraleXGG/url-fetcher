"""Peticiones HTTP concurrentes con httpx + asyncio."""

import asyncio
import sys
import time
from contextlib import nullcontext
from typing import Optional

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from url_fetcher.models import UrlResult
from url_fetcher.parser import compute_indexability, parse_html
from url_fetcher.robots import RobotsChecker


_MAX_PARSE_BYTES = 2 * 1024 * 1024  # 2 MB: bodies más grandes no se parsean.


def _apply_seo_indexability(
    result: UrlResult,
    *,
    has_response: bool,
    blocked_by_robots: bool = False,
) -> None:
    """Calcula y asigna (indexability, indexability_status) cuando estamos en SEO."""
    result.indexability, result.indexability_status = compute_indexability(
        status_code=result.status_code,
        meta_robots=result.meta_robots,
        x_robots_tag=result.x_robots_tag,
        canonical=result.canonical,
        final_url=result.final_url,
        has_response=has_response,
        blocked_by_robots=blocked_by_robots,
    )


async def fetch_url(
    client: httpx.AsyncClient,
    url: str,
    mode: str = "basic",
    robots_checker: Optional[RobotsChecker] = None,
) -> UrlResult:
    """Hace una petición async y devuelve los datos del modo solicitado.

    Si `robots_checker` está presente y bloquea la URL, NO se hace petición
    HTTP: se devuelve un `UrlResult` marcado con `error="Blocked by robots.txt"`
    y, en modo SEO, con la indexability rellenada.
    """
    if robots_checker is not None:
        allowed = await robots_checker.is_allowed(url)
        if not allowed:
            result = UrlResult(url=url, error="Blocked by robots.txt")
            if mode == "seo":
                _apply_seo_indexability(
                    result, has_response=False, blocked_by_robots=True
                )
            return result

    try:
        # perf_counter: monotónico y de alta resolución, ideal para latencia.
        start = time.perf_counter()
        response = await client.get(url)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # response.history: respuestas intermedias (redirecciones).
        # Para `redirect_url` queremos el destino del primer salto, en absoluto:
        #   - Si hay >=2 entradas: history[1].url ya es absoluta.
        #   - Si solo hay 1 redirect: response.url es el destino del primer salto.
        history = response.history
        if history:
            redirect_url = (
                str(history[1].url) if len(history) >= 2 else str(response.url)
            )
        else:
            redirect_url = None

        result = UrlResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            response_time_ms=elapsed_ms,
            redirect_url=redirect_url,
            redirect_count=len(history),
        )

        if mode == "seo":
            result.x_robots_tag = response.headers.get("x-robots-tag")
            result.last_modified = response.headers.get("last-modified")
            result.size_kb = round(len(response.content) / 1024, 1)

            content_type = (result.content_type or "").lower()
            if "text/html" in content_type and len(response.content) <= _MAX_PARSE_BYTES:
                try:
                    parsed = parse_html(response.text)
                    result.title = parsed["title"]
                    result.meta_description = parsed["meta_description"]
                    result.canonical = parsed["canonical"]
                    result.meta_robots = parsed["meta_robots"]
                    result.h1 = parsed["h1"]
                    result.h1_count = parsed["h1_count"]
                    result.h1_all = parsed["h1_all"]
                    result.lang = parsed["lang"]
                    result.og_title = parsed["og_title"]
                    result.og_description = parsed["og_description"]
                    result.h2_count = parsed["h2_count"]
                    result.word_count = parsed["word_count"]
                except Exception as parse_exc:
                    # parsing roto != error de red; loguemos a stderr y seguimos.
                    print(
                        f"  [parse warning] {url}: {parse_exc}",
                        file=sys.stderr,
                    )

            _apply_seo_indexability(result, has_response=True)

        return result
    except httpx.HTTPError as exc:
        result = UrlResult(url=url, error=str(exc))
        if mode == "seo":
            _apply_seo_indexability(result, has_response=False)
        return result
    except Exception as exc:
        result = UrlResult(url=url, error=f"Unexpected: {exc}")
        if mode == "seo":
            _apply_seo_indexability(result, has_response=False)
        return result


async def fetch_all(
    urls: list[str],
    concurrency: int = 20,
    mode: str = "basic",
    timeout: int = 15,
    user_agent: str = "url-fetcher/0.9",
    max_redirects: int = 10,
    show_progress: bool = True,
    respect_robots: bool = False,
) -> list[UrlResult]:
    """Procesa una lista de URLs en paralelo y devuelve resultados en orden de entrada.

    Si `respect_robots`, antes de cada petición se consulta el robots.txt del
    dominio (con cache) y las URLs bloqueadas se marcan sin generar petición HTTP.

    Si `show_progress` y hay más de una URL, dibuja una barra `rich.Progress`
    en stderr (para no contaminar stdout cuando el resumen se redirige a un
    archivo). La barra es transient: desaparece al terminar.
    """
    # Semaphore: limita cuántas peticiones pueden estar en vuelo a la vez.
    # Sin él, asyncio.gather lanzaría todas las URLs simultáneamente y podríamos
    # saturar la red, agotar file descriptors o que el servidor nos baneara.
    semaphore = asyncio.Semaphore(concurrency)
    use_progress = show_progress and len(urls) > 1

    if use_progress:
        progress = Progress(
            TextColumn("[cyan]Procesando URLs[/cyan]"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=Console(stderr=True),
            transient=True,
        )
        progress_ctx = progress
    else:
        progress = None
        progress_ctx = nullcontext()

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": user_agent},
        max_redirects=max_redirects,
        follow_redirects=True,
    ) as client:
        robots_checker = (
            RobotsChecker(client, user_agent) if respect_robots else None
        )

        with progress_ctx:
            task_id = (
                progress.add_task("processing", total=len(urls))
                if progress is not None
                else None
            )

            async def _bounded_fetch(url: str) -> UrlResult:
                async with semaphore:
                    result = await fetch_url(
                        client, url, mode=mode, robots_checker=robots_checker
                    )
                    if progress is not None:
                        progress.advance(task_id)
                    return result

            # gather lanza todas las tareas en paralelo y recoge sus resultados
            # respetando el orden de la lista original — clave para que el output
            # se pueda alinear con el input.
            return await asyncio.gather(*(_bounded_fetch(u) for u in urls))
