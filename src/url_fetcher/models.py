"""Dataclasses y tipos compartidos del proyecto."""

from dataclasses import dataclass, field


@dataclass
class UrlResult:
    """Resultado de procesar una URL. Campos básicos siempre, SEO opcionales."""

    url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    response_time_ms: int | None = None
    redirect_url: str | None = None
    redirect_count: int = 0
    error: str | None = None

    # Campos SEO (rellenos solo en --mode seo)
    indexability: str | None = None  # "Indexable" | "Non-Indexable" | None
    indexability_status: str | None = None  # razón de no indexación (en inglés)
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    meta_robots: str | None = None
    x_robots_tag: str | None = None
    h1: str | None = None
    h1_count: int | None = None
    h1_all: str | None = None
    lang: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    h2_count: int | None = None
    word_count: int | None = None
    size_kb: float | None = None
    last_modified: str | None = None
    hreflang_count: int | None = None
    hreflang_values: list[str] = field(default_factory=list)
    hreflang_issues: str | None = None
