"""Extracción de campos SEO de HTML usando selectolax."""

from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

from selectolax.parser import HTMLParser


def _attr(node, name: str) -> Optional[str]:
    """Lee un atributo, hace strip y devuelve None si queda vacío."""
    if node is None:
        return None
    val = node.attributes.get(name)
    if val is None:
        return None
    val = val.strip()
    return val or None


def _text(node) -> Optional[str]:
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
        }

    tree = HTMLParser(html)

    title = _text(tree.css_first("title"))
    meta_description = _attr(tree.css_first("meta[name='description']"), "content")
    canonical = _attr(tree.css_first("link[rel='canonical']"), "href")
    meta_robots = _attr(tree.css_first("meta[name='robots']"), "content")
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


def compute_status_index(
    status_code: Optional[int],
    meta_robots: Optional[str],
    x_robots_tag: Optional[str],
    canonical: Optional[str],
    final_url: Optional[str],
) -> Optional[str]:
    """Devuelve "Indexable" / "No Indexable" / None según las 4 reglas estándar."""
    if status_code is None:
        return None
    if not (200 <= status_code < 300):
        return "No Indexable"
    for value in (meta_robots, x_robots_tag):
        if value:
            lowered = value.lower()
            if "noindex" in lowered or "none" in lowered:
                return "No Indexable"
    if canonical and final_url:
        # canonical puede ser relativo: lo resolvemos con final_url como base.
        absolute = urljoin(final_url, canonical)
        if _norm(absolute) != _norm(final_url):
            return "No Indexable"
    return "Indexable"
