"""Peticiones HTTP concurrentes con httpx + asyncio."""

import asyncio
import time

import httpx

from url_fetcher.models import UrlResult


async def fetch_url(client: httpx.AsyncClient, url: str) -> UrlResult:
    """Hace una petición async usando un cliente compartido y devuelve el resultado.

    El cliente se inyecta desde fuera para reutilizar el pool de conexiones TCP
    entre todas las URLs del batch — es la principal ganancia de rendimiento al
    procesar muchas URLs (sobre todo si comparten host).
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

        return UrlResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            response_time_ms=elapsed_ms,
            redirect_url=redirect_url,
            redirect_count=len(history),
        )
    except httpx.HTTPError as exc:
        return UrlResult(url=url, error=str(exc))
    except Exception as exc:
        return UrlResult(url=url, error=f"Unexpected: {exc}")


async def fetch_all(
    urls: list[str],
    concurrency: int = 20,
    timeout: int = 15,
    user_agent: str = "url-fetcher/0.3",
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
                return await fetch_url(client, url)

        # gather lanza todas las tareas en paralelo y recoge sus resultados
        # respetando el orden de la lista original — clave para que el output
        # se pueda alinear con el input.
        return await asyncio.gather(*(_bounded_fetch(u) for u in urls))
