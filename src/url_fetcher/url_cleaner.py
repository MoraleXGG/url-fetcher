"""Validación, normalización y deduplicación de URLs de entrada."""

from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse


@dataclass
class CleanResult:
    """Resultado de limpiar una lista de URLs."""

    valid_unique: list[str] = field(default_factory=list)
    duplicates_count: int = 0
    invalid: list[str] = field(default_factory=list)

    @property
    def total_input(self) -> int:
        return len(self.valid_unique) + self.duplicates_count + len(self.invalid)


def _dedup_key(url: str) -> str:
    """Clave canónica para detectar duplicados.

    El host es case-insensitive en HTTP, así que lo bajamos a minúsculas.
    El fragment (#...) nunca se envía al servidor, por lo que dos URLs que solo
    difieren en el fragment apuntan al mismo recurso desde nuestro punto de vista.
    Path/query mantienen su case porque los servidores los tratan case-sensitive.
    """
    parsed = urlparse(url)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            "",  # fragment descartado a propósito
        )
    )


def clean_urls(raw_urls: list[str]) -> CleanResult:
    """Trim, validación (http/https + host + sin espacios internos) y dedup.

    Conserva el orden de primera aparición. Para `invalid` guarda la string
    original (sin trim) para que el reporte al usuario sea informativo.
    Las cadenas vacías post-trim se ignoran silenciosamente: un .txt con
    líneas en blanco no debería ensuciar el informe.
    """
    result = CleanResult()
    seen: set[str] = set()

    for raw in raw_urls:
        trimmed = raw.strip() if isinstance(raw, str) else ""
        if not trimmed:
            continue

        # Espacios dentro de la URL → malformada. urlparse no lanza nada y un
        # navegador la codificaría, pero aquí preferimos descartar explícitamente
        # para que el usuario vea el problema en el reporte.
        if " " in trimmed:
            result.invalid.append(raw)
            continue

        parsed = urlparse(trimmed)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            result.invalid.append(raw)
            continue

        key = _dedup_key(trimmed)
        if key in seen:
            result.duplicates_count += 1
            continue
        seen.add(key)
        # valid_unique recibe la versión post-trim pero respetando case del
        # host original — útil cuando el usuario quiere ver en el output lo
        # que pidió, no una forma normalizada.
        result.valid_unique.append(trimmed)

    return result
