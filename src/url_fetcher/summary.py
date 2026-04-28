"""Generación de resúmenes estadísticos del rastreo."""

from collections import Counter
from pathlib import Path

from url_fetcher.models import UrlResult
from url_fetcher.url_cleaner import CleanResult


def build_status_summary(results: list[UrlResult]) -> dict[str, int]:
    """Cuenta por status code, ordenado por ocurrencias DESC.

    URLs con `status_code is None` (errores de red, DNS, etc.) van a "Error".
    """
    counter: Counter[str] = Counter()
    for r in results:
        if r.status_code is None:
            counter["Error"] += 1
        else:
            counter[str(r.status_code)] += 1
    return dict(counter.most_common())


def build_content_type_summary(results: list[UrlResult]) -> dict[str, int]:
    """Cuenta por content type principal (sin parámetros), ignorando errores.

    "text/html; charset=utf-8" se normaliza a "text/html".
    URLs con error no contribuyen — no llegaron a recibir un content-type.
    """
    counter: Counter[str] = Counter()
    for r in results:
        if r.error is not None:
            continue
        ctype = r.content_type
        if not ctype:
            counter["(sin tipo)"] += 1
        else:
            counter[ctype.split(";")[0].strip()] += 1
    return dict(counter.most_common())


def format_summary(
    results: list[UrlResult],
    clean_result: CleanResult,
    elapsed_seconds: float,
    output_path: Path | None = None,
    show_breakdowns: bool = True,
) -> str:
    """Compone el bloque "--- Resumen ---" como un único string."""
    n = len(results)
    ok = sum(1 for r in results if r.error is None)
    errors = n - ok
    dupes = clean_result.duplicates_count
    invalid_count = len(clean_result.invalid)

    main_parts = [f"Procesadas: {n}"]
    if dupes > 0:
        main_parts.append(f"Duplicadas: {dupes}")
    if invalid_count > 0:
        main_parts.append(f"Inválidas: {invalid_count}")
    main_parts.extend(
        [
            f"OK: {ok}",
            f"Errores: {errors}",
            f"Tiempo total: {elapsed_seconds:.2f}s",
        ]
    )

    blocks: list[str] = ["--- Resumen ---", " | ".join(main_parts)]

    if invalid_count > 0:
        invalid_lines = ["", "URLs inválidas descartadas:"]
        for url in clean_result.invalid:
            invalid_lines.append(f'  · "{url}"')
        blocks.append("\n".join(invalid_lines))

    if show_breakdowns and n > 0:
        status_summary = build_status_summary(results)
        if status_summary:
            status_lines = ["", "Por status code:"]
            for code, count in status_summary.items():
                pct = (count / n) * 100
                status_lines.append(f"  {code}: {count} ({pct:.1f}%)")
            blocks.append("\n".join(status_lines))

        # Si todas las URLs son errores no tiene sentido el bloque de tipos.
        if errors < n:
            content_summary = build_content_type_summary(results)
            if content_summary:
                content_lines = ["", "Por content type:"]
                for ctype, count in content_summary.items():
                    pct = (count / n) * 100
                    content_lines.append(f"  {ctype}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(content_lines))

    if output_path is not None:
        blocks.append(f"\nOutput: {output_path}")

    return "\n".join(blocks)
