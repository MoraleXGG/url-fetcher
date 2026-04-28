"""Comprobación de robots.txt con cache por dominio."""

import asyncio
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsChecker:
    """Evalúa si una URL está permitida por robots.txt usando cache por dominio.

    Política permisiva: si robots.txt no existe, devuelve un error o no se puede
    leer, asumimos permitido. La alternativa estricta (cualquier fallo = bloqueo)
    rompe demasiadas auditorías reales con sites mal configurados.

    `RobotFileParser.can_fetch(useragent, url)` evalúa el `User-Agent` que le
    pasamos: un mismo robots.txt puede permitir o bloquear según UA, así que el
    UA del checker debe coincidir con el del fetcher.
    """

    def __init__(self, client: httpx.AsyncClient, user_agent: str):
        self._client = client
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}
        # Lock: varias coroutines pueden pedir robots.txt del mismo dominio a la
        # vez; sin esto descargaríamos el mismo archivo N veces y podríamos meter
        # entradas duplicadas o inconsistentes en el cache.
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str) -> bool:
        """True si la URL está permitida (o si no podemos evaluarla con certeza)."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True  # URL malformada: no podemos evaluar

        domain_key = f"{parsed.scheme}://{parsed.netloc}"

        async with self._lock:
            if domain_key not in self._cache:
                self._cache[domain_key] = await self._fetch_robots(domain_key)

        return self._cache[domain_key].can_fetch(self._user_agent, url)

    async def _fetch_robots(self, domain_key: str) -> RobotFileParser:
        """Descarga y parsea robots.txt; en error devuelve parser permisivo."""
        rp = RobotFileParser()
        robots_url = f"{domain_key}/robots.txt"
        try:
            response = await self._client.get(robots_url, timeout=10)
            if response.status_code == 200:
                # Filtrar líneas vacías para evitar que el parser de stdlib
                # interprete una línea en blanco como fin de bloque de reglas.
                # Patrón común en WordPress y muchos sites.
                lines = [line for line in response.text.splitlines() if line.strip()]
                rp.parse(lines)
            else:
                # 404, 403, redirects raros, etc.: asumir permitido.
                rp.parse([])
        except Exception:
            # Errores de red al pedir robots.txt: asumir permitido.
            rp.parse([])
        return rp
