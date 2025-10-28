"""Validación de respuestas del LLM."""

import re
from typing import Dict, List, Tuple


def validate_justificacion_and_refs(llm_obj: Dict, snapshot: Dict, just_len: int) -> Tuple[bool, List[str]]:
    """Valida que 'justificacion' cumpla longitud y mencione métricas/tendencias.

    Args:
        llm_obj: Objeto JSON retornado por el LLM
        snapshot: Snapshot de datos originales
        just_len: Longitud objetivo para el campo 'justificacion'

    Returns:
        Tupla (ok, warnings_list) donde ok indica si la validación pasó

    Example:
        >>> llm_obj = {
        ...     "justificacion": "La velocidad de 0.5 mm/h y deformación de 1.2 mm en las últimas 12h..."
        ... }
        >>> snapshot = {"suggested_metrics": {"vel": 0.5, "deform": 1.2}}
        >>> ok, warnings = validate_justificacion_and_refs(llm_obj, snapshot, 100)
        >>> ok
        True
    """
    warnings: List[str] = []

    if not isinstance(llm_obj, dict):
        return False, ["no_json_obj"]

    just = str(llm_obj.get("justificacion", ""))
    if not just:
        warnings.append("missing:justificacion")
        return False, warnings

    # longitud objetivo ±25%
    try:
        jl = int(just_len)
        low = int(max(0, jl * 0.75))
        high = int(jl * 1.25)
        if not (low <= len(just) <= high):
            warnings.append(f"len_out_of_range:{len(just)}")
    except Exception:
        warnings.append("bad:just_len_param")

    # buscar mención de métricas mediante los valores sugeridos si existen
    metric_ok = False
    try:
        sugg = snapshot.get("suggested_metrics") or {}
        for k in ("vel", "deform"):
            if k in sugg:
                sval = str(round(float(sugg[k]), 2))
                if sval in just:
                    metric_ok = True
                    break
    except Exception:
        pass

    # fallback: buscar palabras clave métricas
    if not metric_ok:
        for kw in ("vel", "velocidad", "deform", "deformaci", "mm/hr", "mm"):
            if kw in just.lower():
                metric_ok = True
                break

    if not metric_ok:
        warnings.append("no_metric_mentioned")

    # detección simple de mención de tendencia/horas (ej: '12h', 'horas', 'últimas')
    trend_ok = False
    if re.search(r"\d+\s*h\b", just) or re.search(r"ultim|últim|horas|hora|tend|trend", just.lower()):
        trend_ok = True

    if not trend_ok:
        warnings.append("no_trend_mentioned")

    ok = (
        "no_metric_mentioned" not in warnings
        and "no_trend_mentioned" not in warnings
        and "missing:justificacion" not in warnings
    )
    return ok, warnings
