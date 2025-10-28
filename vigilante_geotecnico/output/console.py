"""Funciones para renderizar salida en consola (rich/plain/json)."""

import json
from typing import Dict, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _RICH_AVAILABLE = True
except Exception:
    _RICH_AVAILABLE = False


def print_structured_console(
    snapshot: Dict,
    llm_content: Optional[str],
    llm_json: Optional[Dict],
    disagreement: bool,
    console_format: str,
    llm_error: Optional[str],
) -> None:
    """Renderiza salida por consola en formato rich/plain/json.

    Args:
        snapshot: Diccionario con métricas actuales y ventana
        llm_content: Respuesta cruda del LLM (opcional)
        llm_json: Respuesta parseada del LLM (opcional)
        disagreement: Si hay desacuerdo entre LLM y reglas
        console_format: Formato de salida ("rich", "plain", "json")
        llm_error: Error del LLM si ocurrió (opcional)

    Example:
        >>> snapshot = {
        ...     "current": {"time": "2025-01-01 12:00", "state": "NORMAL",
        ...                 "disp_mm": 1.2, "vel_mm_hr": 0.5},
        ...     "thresholds": {"alerta_mm_hr": 1.0, "alarma_mm_hr": 3.0},
        ...     "window": {"duration_hours": 12, "n_points": 100}
        ... }
        >>> print_structured_console(snapshot, None, None, False, "json", None)  # doctest: +SKIP
    """
    summary = {
        "time": snapshot["current"]["time"],
        "state": snapshot["current"]["state"],
        "metrics": {
            "disp_mm": round(float(snapshot["current"]["disp_mm"]), 3),
            "delta_mm": round(float(snapshot["current"].get("delta_mm", 0)), 3),
            "cum_window_mm": round(float(snapshot["current"].get("cum_disp_mm_window", 0)), 3),
            "vel_mm_hr": round(float(snapshot["current"]["vel_mm_hr"]), 3),
            "accum_rate_mm_hr": round(float(snapshot["current"].get("accum_rate_mm_hr", 0)), 3),
            "accum_mm_per_period": round(float(snapshot["current"].get("accum_mm_per_period", 0)), 3),
            "period_hours": snapshot["current"].get("accum_period_hours", 24),
        },
        "thresholds": snapshot["thresholds"],
        "window": {
            "duration_hours": round(float(snapshot["window"]["duration_hours"]), 3),
            "n_points": snapshot["window"]["n_points"],
            "cum_min_mm": round(float(snapshot["window"]["cum_min_mm"]), 3),
            "cum_max_mm": round(float(snapshot["window"]["cum_max_mm"]), 3),
            "sign_change_window": bool(snapshot["window"]["sign_change_window"]),
            "accum_window_threshold_mm": round(float(snapshot["window"]["accum_window_threshold_mm"]), 3),
        },
        "llm": {
            "json": llm_json,
            "raw": (llm_content[:500] + "…") if (llm_content and len(llm_content) > 500) else llm_content,
            "disagreement": disagreement or False,
            "error": llm_error,
        },
    }

    if console_format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if console_format == "rich" and _RICH_AVAILABLE:
        _print_rich_console(snapshot, summary)
        return

    # Plain fallback
    _print_plain_console(snapshot, summary)


def _print_rich_console(snapshot: Dict, summary: Dict) -> None:
    """Imprime en formato rich con colores y tablas."""
    console = Console()

    # Encabezado con color por estado
    state = summary["state"]
    state_style = {
        "NORMAL": "bold green",
        "ALERTA": "bold yellow",
        "ALARMA": "bold red",
    }.get(state, "bold")
    title = f"SNAPSHOT @ {summary['time']}"
    console.rule(title)
    console.print(Panel(f"Estado: [ {state} ]", title="Situación", style=state_style))

    # Tabla de métricas con etiquetas amigables
    labels = {
        "disp_mm": "Lectura acumulada (mm)",
        "delta_mm": "Desplazamiento último paso (mm)",
        "cum_window_mm": "Acumulado en ventana (mm)",
        "vel_mm_hr": "Velocidad (mm/hr)",
        "accum_rate_mm_hr": "Tasa de acumulación (mm/hr)",
        "accum_mm_per_period": f"Proyección {summary['metrics']['period_hours']} h (mm)",
        "period_hours": "Periodo (h)",
    }
    t = Table(show_header=True, header_style="bold")
    t.add_column("Métrica")
    t.add_column("Valor")
    thr_alerta = float(summary["thresholds"]["alerta_mm_hr"])
    thr_alarma = float(summary["thresholds"]["alarma_mm_hr"])

    for key in ["disp_mm", "delta_mm", "cum_window_mm", "vel_mm_hr", "accum_rate_mm_hr", "accum_mm_per_period"]:
        if key not in summary["metrics"]:
            continue
        value = summary["metrics"][key]
        value_str = str(value)
        if key == "vel_mm_hr":
            try:
                v = float(value)
                av = abs(v)
                if av > thr_alarma:
                    value_str = f"[bold red]{value_str}[/]"
                elif av > thr_alerta:
                    value_str = f"[bold yellow]{value_str}[/]"
                else:
                    value_str = f"[bold green]{value_str}[/]"
            except Exception:
                pass
        t.add_row(labels.get(key, key), value_str)

    th = Table(show_header=True, header_style="bold")
    th.add_column("Umbral")
    th.add_column("mm/hr")
    th.add_row("Alerta", str(round(float(summary["thresholds"]["alerta_mm_hr"]), 3)))
    th.add_row("Alarma", str(round(float(summary["thresholds"]["alarma_mm_hr"]), 3)))
    th.add_row("Fuente", str(summary["thresholds"].get("source", "N/A")))

    # Regla aplicada
    dec = snapshot.get("decision", {})
    dec_src = dec.get("source", "N/A")
    dec_rule = dec.get("rule", "N/A")
    console.print(Panel(f"Decisión: {dec_src} | Regla: {dec_rule}", title="Clasificación"))

    console.print(Panel(t, title="Métricas actuales"))

    # Ventana: extremos y cruce por cero
    w = snapshot["window"]
    thr_acc = float(w.get("accum_window_threshold_mm", 0.0))
    color_acc = None
    try:
        aw = abs(float(summary["metrics"]["cum_window_mm"]))
        if thr_acc > 0:
            if aw > 2.0 * thr_acc:
                color_acc = "bold red"
            elif aw > thr_acc:
                color_acc = "bold yellow"
    except Exception:
        pass
    info = (
        f"Ventana: {w['duration_hours']:.2f} h, puntos={w['n_points']}\n"
        f"Min acumulado: {w['cum_min_mm']:.3f} mm @ {w['t_cum_min']}\n"
        f"Max acumulado: {w['cum_max_mm']:.3f} mm @ {w['t_cum_max']}\n"
        f"Cruce por 0 en ventana: {'Sí' if w['sign_change_window'] else 'No'}\n"
        f"Umbral acumulado ventana: {thr_acc:.3f} mm"
    )
    console.print(Panel(info, title="Ventana (extremos)", style=color_acc or ""))
    console.print(Panel(th, title="Umbrales"))

    # LLM info
    llm_title = "LLM (acuerdo ✔)" if not summary["llm"]["disagreement"] else "LLM (desacuerdo ✖)"
    if summary["llm"]["error"]:
        console.print(Panel(f"Error: {summary['llm']['error']}", title=llm_title, style="bold red"))
    elif summary["llm"]["json"]:
        lj = summary["llm"]["json"]
        lt = Table(show_header=True, header_style="bold")
        lt.add_column("Campo")
        lt.add_column("Valor")
        lt.add_row("Nivel sugerido", str(lj.get("level")))
        lt.add_row("Confianza (0-1)", str(lj.get("confidence_0_1")))
        actions = lj.get("actions") or []
        lt.add_row("Acciones", "; ".join(map(str, actions)))
        rationale = lj.get("rationale")
        console.print(Panel(lt, title=llm_title))
        if rationale:
            console.print(Panel(str(rationale), title="Justificación"))
    else:
        console.print(Panel(str(summary["llm"]["raw"] or ""), title=llm_title))


def _print_plain_console(snapshot: Dict, summary: Dict) -> None:
    """Imprime en formato plain text sin colores."""
    print(f"\n=== {summary['time']} ===")
    print(f"Estado: {summary['state']}")
    print("Métricas:")
    print(f"  - Lectura acumulada (mm): {summary['metrics']['disp_mm']}")
    print(f"  - Desplazamiento último paso (mm): {summary['metrics']['delta_mm']}")
    print(f"  - Acumulado en ventana (mm): {summary['metrics']['cum_window_mm']}")
    print(f"  - Velocidad (mm/hr): {summary['metrics']['vel_mm_hr']}")
    print(f"  - Tasa de acumulación (mm/hr): {summary['metrics']['accum_rate_mm_hr']}")
    print(f"  - Proyección {summary['metrics']['period_hours']} h (mm): {summary['metrics']['accum_mm_per_period']}")

    # Ventana: extremos y cruce por cero
    w = snapshot["window"]
    print(f"Ventana: {w['duration_hours']:.2f} h, puntos={w['n_points']}")
    print(f"  - Min acumulado: {round(float(w['cum_min_mm']), 3)} mm @ {w['t_cum_min']}")
    print(f"  - Max acumulado: {round(float(w['cum_max_mm']), 3)} mm @ {w['t_cum_max']}")
    print(f"  - Cruce por 0 en ventana: {'Sí' if w['sign_change_window'] else 'No'}")
    print(f"  - Umbral acumulado ventana (mm): {w['accum_window_threshold_mm']}")

    print("Umbrales:")
    print(f"  - Alerta (mm/hr): {round(float(summary['thresholds']['alerta_mm_hr']), 3)}")
    print(f"  - Alarma (mm/hr): {round(float(summary['thresholds']['alarma_mm_hr']), 3)}")
    print(f"  - Fuente: {summary['thresholds'].get('source', 'N/A')}")

    dec = snapshot.get("decision", {})
    print(f"Clasificación: source={dec.get('source', 'N/A')} rule={dec.get('rule', 'N/A')}")

    if summary["llm"]["error"]:
        print(f"LLM error: {summary['llm']['error']}")
    elif summary["llm"]["json"]:
        lj = summary["llm"]["json"]
        print("LLM:")
        print(f"  - Nivel sugerido: {lj.get('level')}")
        print(f"  - Confianza (0-1): {lj.get('confidence_0_1')}")
        print(f"  - Acciones: {', '.join(map(str, (lj.get('actions') or [])))}")
        if lj.get("rationale"):
            print(f"  - Justificación: {lj.get('rationale')}")
        print(f"  - Acuerdo LLM vs regla: {not summary['llm']['disagreement']}")
    else:
        print(f"LLM: {summary['llm']['raw']}")
