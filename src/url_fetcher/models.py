"""Dataclasses y tipos compartidos del proyecto."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UrlResult:
    """Resultado de procesar una URL. Campos básicos siempre, SEO opcionales."""

    url: str
    final_url: Optional[str] = None
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    response_time_ms: Optional[int] = None
    redirect_url: Optional[str] = None
    redirect_count: int = 0
    error: Optional[str] = None

    # Campos SEO (rellenos solo en --mode seo)
    status_index: Optional[str] = None  # "Indexable" | "No Indexable" | None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical: Optional[str] = None
    meta_robots: Optional[str] = None
    x_robots_tag: Optional[str] = None
    h1: Optional[str] = None
    h1_count: Optional[int] = None
    h1_all: Optional[str] = None
    lang: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    h2_count: Optional[int] = None
    word_count: Optional[int] = None
    size_kb: Optional[float] = None
    last_modified: Optional[str] = None
