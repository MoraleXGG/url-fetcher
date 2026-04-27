"""Carga URLs desde archivos CSV, JSON o TXT."""

import csv
import json
from pathlib import Path

# Nombres de columna URL que se buscan automáticamente, en orden de preferencia.
DEFAULT_URL_COLUMNS = ["url", "loc", "link", "address", "href"]


def load_urls(path: Path, url_column: str | None = None) -> list[str]:
    """Carga URLs despachando por extensión (.txt/.csv/.json).

    Lanza:
        FileNotFoundError: si `path` no existe.
        ValueError: si la extensión no es soportada o no se puede detectar la columna.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _load_txt(path)
    if suffix == ".csv":
        return _load_csv(path, url_column)
    if suffix == ".json":
        return _load_json(path, url_column)
    raise ValueError(
        f"Formato no soportado: '{suffix}'. Soportados: .txt, .csv, .json"
    )


def _load_txt(path: Path) -> list[str]:
    """Una URL por línea. Ignora líneas vacías y comentarios (#)."""
    out: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Saltar vacías y comentarios — facilita anotar listas de auditoría.
            if not stripped or stripped.startswith("#"):
                continue
            out.append(stripped)
    return out


def _resolve_column(fieldnames: list[str], url_column: str | None) -> str:
    """Devuelve el nombre real de la columna URL o lanza ValueError descriptivo.

    Compara case-insensitive para tolerar cabeceras tipo "URL", "Url", "url".
    """
    lower_map = {f.lower(): f for f in fieldnames}
    if url_column is not None:
        real = lower_map.get(url_column.lower())
        if real is None:
            raise ValueError(
                f"La columna '{url_column}' no existe. "
                f"Columnas disponibles: {fieldnames}"
            )
        return real
    for candidate in DEFAULT_URL_COLUMNS:
        if candidate in lower_map:
            return lower_map[candidate]
    raise ValueError(
        f"No se detectó columna URL. Columnas disponibles: {fieldnames}. "
        f"Usa --url-column para indicar cuál."
    )


def _load_csv(path: Path, url_column: str | None) -> list[str]:
    """Lee CSV con DictReader. Detecta o usa la columna indicada."""
    # utf-8-sig: silencia el BOM que dejan Excel y otros editores en Windows
    # (si lo hay) sin afectar a archivos que no lo tengan.
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV sin cabecera: {path}")
        column = _resolve_column(list(reader.fieldnames), url_column)
        return [row[column].strip() for row in reader if row.get(column, "").strip()]


def _load_json(path: Path, url_column: str | None) -> list[str]:
    """Soporta array de strings o array de objetos con campo URL detectable."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("El JSON debe ser una lista de strings o de objetos.")
    if not data:
        return []
    first = data[0]
    if isinstance(first, str):
        return [item for item in data if isinstance(item, str)]
    if isinstance(first, dict):
        column = _resolve_column(list(first.keys()), url_column)
        return [
            item[column]
            for item in data
            if isinstance(item, dict) and column in item
        ]
    raise ValueError(
        f"Tipo de elemento JSON no soportado: {type(first).__name__}"
    )
