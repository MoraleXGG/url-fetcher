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


def build_indexability_summary(results: list[UrlResult]) -> dict[str, int]:
    """Cuenta por indexability. Bucket "(no evaluado)" cuando es None.

    Aplicable solo a modo SEO; en modo básico todos serían "(no evaluado)".
    """
    counter: Counter[str] = Counter()
    for r in results:
        if r.indexability in ("Indexable", "Non-Indexable"):
            counter[r.indexability] += 1
        else:
            counter["(no evaluado)"] += 1
    return dict(counter.most_common())


def build_indexability_status_summary(results: list[UrlResult]) -> dict[str, int]:
    """Cuenta por indexability_status, solo para URLs Non-Indexable."""
    counter: Counter[str] = Counter()
    for r in results:
        if r.indexability != "Non-Indexable":
            continue
        reason = r.indexability_status or "(razón desconocida)"
        counter[reason] += 1
    return dict(counter.most_common())


def build_hreflang_summary(
    results: list[UrlResult],
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Devuelve (presence, state, issue_types).

    - presence: con/sin hreflang.
    - state: OK / Con issues / Sin hreflang.
    - issue_types: agrupa issues por prefijo antes de ":". Cuenta URLs afectadas,
      no ocurrencias (una URL con 3 issues suma 1 en cada tipo, no 3).
    """
    presence: Counter[str] = Counter()
    state: Counter[str] = Counter()
    issue_types: Counter[str] = Counter()

    for r in results:
        has_hreflang = bool(r.hreflang_values)
        if has_hreflang:
            presence["Con hreflang"] += 1
        else:
            presence["Sin hreflang"] += 1

        if not has_hreflang:
            state["Sin hreflang"] += 1
            continue

        if r.hreflang_issues:
            state["Con issues"] += 1
            seen_types: set[str] = set()
            for issue in r.hreflang_issues.split("; "):
                kind = issue.split(":", 1)[0]
                if kind:
                    seen_types.add(kind)
            for kind in seen_types:
                issue_types[kind] += 1
        else:
            state["OK"] += 1

    return dict(presence.most_common()), dict(state.most_common()), dict(issue_types.most_common())


def format_summary(
    results: list[UrlResult],
    clean_result: CleanResult,
    elapsed_seconds: float,
    output_path: Path | None = None,
    show_breakdowns: bool = True,
    mode: str = "basic",
) -> str:
    """Compone el bloque "--- Resumen ---" como un único string."""
    n = len(results)
    dupes = clean_result.duplicates_count
    invalid_count = len(clean_result.invalid)
    totals = dupes + invalid_count + n

    main_parts = [f"Totales: {totals}"]
    if dupes > 0:
        main_parts.append(f"Duplicadas: {dupes}")
    if invalid_count > 0:
        main_parts.append(f"Inválidas: {invalid_count}")
    main_parts.append(f"Procesadas: {n}")
    main_parts.append(f"Tiempo: {elapsed_seconds:.2f}s")

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
        if any(r.error is None for r in results):
            content_summary = build_content_type_summary(results)
            if content_summary:
                content_lines = ["", "Por content type:"]
                for ctype, count in content_summary.items():
                    pct = (count / n) * 100
                    content_lines.append(f"  {ctype}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(content_lines))

        if mode == "seo":
            indexability_summary = build_indexability_summary(results)
            if indexability_summary:
                idx_lines = ["", "Por indexability:"]
                for label, count in indexability_summary.items():
                    pct = (count / n) * 100
                    idx_lines.append(f"  {label}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(idx_lines))

            reason_summary = build_indexability_status_summary(results)
            if reason_summary:
                reason_lines = ["", "Por motivo de no indexación:"]
                for label, count in reason_summary.items():
                    pct = (count / n) * 100
                    reason_lines.append(f"  {label}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(reason_lines))

            presence, state, issue_types = build_hreflang_summary(results)
            if presence:
                presence_lines = ["", "Por hreflang:"]
                for label, count in presence.items():
                    pct = (count / n) * 100
                    presence_lines.append(f"  {label}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(presence_lines))

            if state:
                state_lines = ["", "Por estado de hreflang:"]
                for label, count in state.items():
                    pct = (count / n) * 100
                    state_lines.append(f"  {label}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(state_lines))

            if issue_types:
                issue_lines = ["", "Por tipo de issue:"]
                for label, count in issue_types.items():
                    pct = (count / n) * 100
                    issue_lines.append(f"  {label}: {count} ({pct:.1f}%)")
                blocks.append("\n".join(issue_lines))

    if output_path is not None:
        blocks.append(f"\nOutput: {output_path}")

    return "\n".join(blocks)
