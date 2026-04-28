"""Escritura de resultados a archivos CSV (y futuros formatos)."""

import csv
import json
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

from url_fetcher.models import UrlResult


def generate_default_output_path(extension: str = "csv") -> Path:
    """Devuelve `output/url-fetcher_YYYY-MM-DD_HHMMSS.<ext>`, creando la carpeta."""
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return output_dir / f"url-fetcher_{stamp}.{extension}"


def write_csv(results: list[UrlResult], path: Path) -> None:
    """Escribe los resultados a CSV con una columna por campo de UrlResult.

    - utf-8-sig: Excel en español detecta el BOM y muestra los acentos sin
      tener que cambiar el encoding manualmente al abrir el archivo.
    - asdict + fields: respetamos el orden de declaración del dataclass como
      cabecera, sin repetirlo a mano (un cambio en `models.py` se refleja aquí).
    - None → cadena vacía: si dejamos el None pasar, csv escribe el literal
      "None" en la celda y los analistas piensan que es un valor real.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [f.name for f in fields(UrlResult)]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            for key, value in row.items():
                if value is None:
                    row[key] = ""
            writer.writerow(row)


def write_json(results: list[UrlResult], path: Path) -> None:
    """Escribe los resultados a JSON (array de objetos).

    - utf-8 sin BOM: el JSON estándar no lo lleva.
    - ensure_ascii=False: preserva acentos legibles en lugar de escapes \\uXXXX.
    - indent=2: legible en editor sin volverse demasiado verboso.
    - None se serializa como null por defecto, sin convertir a "" como en CSV.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(result) for result in results]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
