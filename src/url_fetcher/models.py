"""Dataclasses y tipos compartidos del proyecto."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UrlResult:
    """Resultado de procesar una URL en modo básico."""

    url: str
    final_url: Optional[str] = None
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    response_time_ms: Optional[int] = None
    redirect_url: Optional[str] = None
    redirect_count: int = 0
    error: Optional[str] = None
