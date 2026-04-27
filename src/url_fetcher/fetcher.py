"""Peticiones HTTP concurrentes con httpx + asyncio."""

import time

import httpx

from url_fetcher.models import UrlResult


def fetch_url(
    url: str,
    timeout: int = 15,
    user_agent: str = "url-fetcher/0.1",
    max_redirects: int = 10,
) -> UrlResult:
    """Realiza una petición HTTP síncrona y devuelve los datos del modo básico."""
    try:
        # perf_counter es monotónico y de alta resolución; ideal para medir latencia.
        # max_redirects es parámetro del Client, no de get(): por eso construimos uno.
        start = time.perf_counter()
        with httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            max_redirects=max_redirects,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # response.history lista las respuestas intermedias (las redirecciones).
        # Si está vacío, no hubo redirects. El primer salto es la URL absoluta a la
        # que apunta la respuesta inicial: usamos history[1].url cuando hay >=2
        # entradas (siempre absoluta) y caemos a response.url cuando solo hubo un
        # salto (en ese caso la URL final ya es el destino del primer salto).
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
