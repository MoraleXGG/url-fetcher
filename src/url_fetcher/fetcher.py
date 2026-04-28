"""Peticiones HTTP concurrentes con httpx + asyncio."""

import asyncio
import sys
import time

import httpx

from url_fetcher.models import UrlResult
from url_fetcher.parser import compute_status_index, parse_html


_MAX_PARSE_BYTES = 2 * 1024 * 1024  # 2 MB: bodies más grandes no se parsean.


async def fetch_url(
    client: httpx.AsyncClient, url: str, mode: str = "basic"
) -> UrlResult:
    """Hace una petición async y devuelve los datos del modo solicitado.

    El cliente se inyecta desde fuera para reutilizar el pool de conexiones TCP
    entre todas las URLs del batch.

    En modo `seo`, además de los campos básicos, rellena cabeceras SEO
    (x-robots-tag, last-modified, size_kb), parsea el HTML si content-type es
    text/html y body <= 2 MB, y calcula `status_index`.
    """
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

            result.status_index = compute_status_index(
                result.status_code,
                result.meta_robots,
                result.x_robots_tag,
                result.canonical,
                result.final_url,
            )

        return result
    except httpx.HTTPError as exc:
        return UrlResult(url=url, error=str(exc))
    except Exception as exc:
        return UrlResult(url=url, error=f"Unexpected: {exc}")


async def fetch_all(
    urls: list[str],
    concurrency: int = 20,
    mode: str = "basic",
    timeout: int = 15,
    user_agent: str = "url-fetcher/0.6.1",
    max_redirects: int = 10,
) -> list[UrlResult]:
    """Procesa una lista de URLs en paralelo y devuelve resultados en orden de entrada."""
    # Semaphore: limita cuántas peticiones pueden estar en vuelo a la vez.
    # Sin él, asyncio.gather lanzaría todas las URLs simultáneamente y podríamos
    # saturar la red, agotar file descriptors o que el servidor nos baneara.
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": user_agent},
        max_redirects=max_redirects,
        follow_redirects=True,
    ) as client:

        async def _bounded_fetch(url: str) -> UrlResult:
            async with semaphore:
                return await fetch_url(client, url, mode=mode)

        # gather lanza todas las tareas en paralelo y recoge sus resultados
        # respetando el orden de la lista original — clave para que el output
        # se pueda alinear con el input.
        return await asyncio.gather(*(_bounded_fetch(u) for u in urls))
