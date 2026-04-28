"""Extracción de campos SEO de HTML usando selectolax."""

import re
from urllib.parse import urljoin, urlparse, urlunparse

from selectolax.parser import HTMLParser

# Permisivo BCP47: 2-3 letras de idioma + cualquier número de subtags alfanuméricas
# (p.ej. `zh-Hant-TW`, `es-419`, `pt-BR`). `x-default` se trata como excepción.
_HREFLANG_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


def _attr(node, name: str) -> str | None:
    """Lee un atributo, hace strip y devuelve None si queda vacío."""
    if node is None:
        return None
    val = node.attributes.get(name)
    if val is None:
        return None
    val = val.strip()
    return val or None


def _text(node) -> str | None:
    if node is None:
        return None
    val = node.text(strip=True)
    return val or None


def parse_html(html: str) -> dict:
    """Devuelve los 12 campos SEO derivables del cuerpo HTML.

    word_count es una aproximación: contamos `text.split()` tras eliminar
    `script` y `style`. No filtramos plantillas ni espacios markup.

    Si el HTML está vacío devuelve contadores None (no hay árbol que mirar).
    Si el HTML tiene contenido pero no contiene los elementos buscados,
    devuelve los campos string a None y los contadores a 0.
    """
    if not html:
        return {
            "title": None,
            "meta_description": None,
            "canonical": None,
            "meta_robots": None,
            "h1": None,
            "h1_count": None,
            "h1_all": None,
            "lang": None,
            "og_title": None,
            "og_description": None,
            "h2_count": None,
            "word_count": None,
            "hreflang_count": None,
            "hreflang_pairs": [],
        }

    tree = HTMLParser(html)

    title = _text(tree.css_first("title"))
    meta_description = _attr(tree.css_first("meta[name='description']"), "content")
    canonical = _attr(tree.css_first("link[rel='canonical']"), "href")
    meta_robots = _attr(tree.css_first("meta[name='robots']"), "content")

    hreflang_links = tree.css("head link[rel='alternate'][hreflang]")
    hreflang_pairs: list[tuple[str, str]] = []
    for n in hreflang_links:
        h = _attr(n, "hreflang")
        href = _attr(n, "href")
        if h and href:
            hreflang_pairs.append((h, href))
    lang = _attr(tree.css_first("html"), "lang")
    og_title = _attr(tree.css_first("meta[property='og:title']"), "content")
    og_description = _attr(tree.css_first("meta[property='og:description']"), "content")

    h1_nodes = tree.css("h1")
    h1_count = len(h1_nodes)
    h1_texts = [n.text(strip=True) for n in h1_nodes]
    h1_texts = [t for t in h1_texts if t]
    h1 = h1_texts[0] if h1_texts else None
    h1_all = " | ".join(h1_texts) if len(h1_texts) > 1 else None

    h2_count = len(tree.css("h2"))

    # word_count: strip_tags muta el árbol, lo hacemos AL FINAL para no
    # afectar a los selectores anteriores.
    tree.strip_tags(["script", "style"])
    body = tree.body
    text = body.text(separator=" ") if body is not None else tree.text()
    word_count = len(text.split())

    return {
        "title": title,
        "meta_description": meta_description,
        "canonical": canonical,
        "meta_robots": meta_robots,
        "h1": h1,
        "h1_count": h1_count,
        "h1_all": h1_all,
        "lang": lang,
        "og_title": og_title,
        "og_description": og_description,
        "h2_count": h2_count,
        "word_count": word_count,
        "hreflang_count": len(hreflang_pairs),
        "hreflang_pairs": hreflang_pairs,
    }


def _norm(url: str) -> str:
    parsed = urlparse(url.strip())
    # path "" se trata como "/" para que `https://x.com` y `https://x.com/`
    # no se cuenten como canonical distinto.
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )


def _resolve_and_norm(base: str, ref: str) -> str:
    """Resuelve `ref` relativo contra `base` (urljoin) y normaliza con `_norm`."""
    return _norm(urljoin(base, ref))


def validate_hreflang(
    pairs: list[tuple[str, str]],
    final_url: str | None,
) -> str:
    """Devuelve issues separados por '; '. Vacío si no hay issues o no hay hreflangs.

    Tipos de issue (en este orden en la cadena resultante):
      - invalid_code:CODE — código que no es `x-default` ni cumple BCP47 permisivo.
      - missing_x_default — hay >=2 códigos distintos y ninguno es `x-default`.
      - missing_self_reference — `final_url` no aparece como href en ningún par.
      - duplicate_hreflang:CODE — el mismo código apunta a >=2 URLs distintas.
    """
    if not pairs:
        return ""

    issues: list[str] = []

    for code, _ in pairs:
        if code == "x-default":
            continue
        if not _HREFLANG_RE.match(code):
            issues.append(f"invalid_code:{code}")

    distinct_codes = {code for code, _ in pairs}
    if len(distinct_codes) >= 2 and "x-default" not in distinct_codes:
        issues.append("missing_x_default")

    if final_url is not None:
        normalized_final = _norm(final_url)
        hrefs_normalized = {_resolve_and_norm(final_url, href) for _, href in pairs}
        if normalized_final not in hrefs_normalized:
            issues.append("missing_self_reference")

    # Para detectar duplicados ambiguos: agrupamos por código y contamos URLs
    # normalizadas distintas. Solo es "duplicado" si apuntan a destinos distintos.
    by_code: dict[str, set[str]] = {}
    base_for_norm = final_url or ""
    for code, href in pairs:
        if code == "x-default":
            continue
        norm_href = _resolve_and_norm(base_for_norm, href) if base_for_norm else href
        by_code.setdefault(code, set()).add(norm_href)
    for code, urls in by_code.items():
        if len(urls) >= 2:
            issues.append(f"duplicate_hreflang:{code}")

    return "; ".join(issues)


def compute_indexability(
    status_code: int | None,
    meta_robots: str | None,
    x_robots_tag: str | None,
    canonical: str | None,
    final_url: str | None,
    has_response: bool,
    blocked_by_robots: bool = False,
) -> tuple[str | None, str | None]:
    """Devuelve `(indexability, indexability_status)` estilo Screaming Frog.

    Razones de "Non-Indexable" priorizadas (la primera que case gana):
        1. blocked_by_robots → "Blocked by Robots.txt"
        2. not has_response → "Connection Error"
        3. 4xx → "Client Error"
        4. 5xx → "Server Error"
        5. 3xx (raro: por defecto seguimos redirects) → "Redirected"
        6. meta_robots o x_robots_tag con "noindex"/"none" → "Noindex"
        7. canonical apunta a otra URL → "Canonicalised"

    Nota: `blocked_by_robots` se evalúa antes que `has_response` aunque ambos
    impliquen ausencia de respuesta. Cuando el usuario activa `--respect-robots`
    y bloqueamos la URL, la razón concreta es "Blocked by Robots.txt", no
    "Connection Error".
    """
    if blocked_by_robots:
        return ("Non-Indexable", "Blocked by Robots.txt")
    if not has_response or status_code is None:
        return ("Non-Indexable", "Connection Error")
    if 400 <= status_code < 500:
        return ("Non-Indexable", "Client Error")
    if 500 <= status_code < 600:
        return ("Non-Indexable", "Server Error")
    if 300 <= status_code < 400:
        return ("Non-Indexable", "Redirected")
    for value in (meta_robots, x_robots_tag):
        if value:
            lowered = value.lower()
            if "noindex" in lowered or "none" in lowered:
                return ("Non-Indexable", "Noindex")
    # canonical puede ser relativo: lo resolvemos con final_url como base.
    if (
        canonical
        and final_url
        and _resolve_and_norm(final_url, canonical) != _norm(final_url)
    ):
        return ("Non-Indexable", "Canonicalised")
    return ("Indexable", None)
