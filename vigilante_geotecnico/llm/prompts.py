"""Construcción de prompts para el LLM."""

import json
from typing import Dict

import pandas as pd


def build_prompt(snapshot: Dict, just_len: int = 600) -> str:
    """Construye el prompt para el LLM con el snapshot de datos.

    Args:
        snapshot: Diccionario con el snapshot de métricas actuales
        just_len: Longitud objetivo para el campo 'justificacion' en caracteres

    Returns:
        String con el prompt completo para el LLM

    Example:
        >>> snapshot = {
        ...     "current": {"vel_mm_hr": 0.5, "disp_mm": 1.2},
        ...     "thresholds": {"alerta_mm_hr": 1.0, "alarma_mm_hr": 3.0}
        ... }
        >>> prompt = build_prompt(snapshot, just_len=400)
        >>> "Instrucciones" in prompt
        True
    """
    # Política refinada A–E
    policy = """
            Instrucciones (español):
            A) Snapshot esperado (nombres y unidades estandarizados):
            - vel_mm_h (mm/h), deform_mm (mm),
            - history{vel_series_mm_h, deform_series_mm, ts},
            - fixed_rules{v_alert, v_alarm, d_alert, v_alarm_with_d1, v_alarm_with_d2, use_abs},
            - thresholds{normal, alerta, alarma},  // adaptativas sobre |vel| salvo use_abs=false
            - persistence{win_h=12, metric="vel|deform|mixed", rule="applied_rule"},
            - meta{radar_id, site, bank, bench, report_window_min, quality_flags{spikes,low_snr,gap}, timezone="America/Santiago"}.

            B) Sanidad de datos:
            - Rechaza NaN/Inf. Si quality_flags.spikes=true aplica de-spike (Hampel o >5σ). Añade evidence="de-spike".
            - Marca: low_snr, gap_data (gap>10% de la ventana), time_misaligned si ts no es monótono.
            - Si falta un parámetro crítico de una regla, desactiva SOLO esa regla y añade evidence="missing_param:<nombre>".

            C) Reglas (orden, prioridad y determinismo):
            - Convenciones: por defecto evalúa |vel| y |deform|. Si use_abs=false, evalúa con signo LOS.
            - Prioridad: (1) Fijas combinadas (deform+vel) → (2) Fijas individuales (vel > deform) → (3) Adaptativas → (4) Persistencia (+1 nivel, máx. ALARMA).
            - Fijas:
                • ALARMA si deform_mm > d_alert y vel_mm_h > v_alarm_with_d2
                • ALARMA si deform_mm > d_alert y vel_mm_h > v_alarm
                • ALARMA si vel_mm_h > v_alarm
                • ALERTA si deform_mm > d_alert
                • ALERTA si vel_mm_h > v_alert
            - Adaptativas (si no disparan fijas) sobre |vel| salvo use_abs=false:
                • ALARMA si vel_mm_h ≥ thresholds.alarma
                • ALERTA si vel_mm_h ≥ thresholds.alerta
                • NORMAL si vel_mm_h < thresholds.normal
                • En zona gris, elige el umbral más conservador (nivel más alto).
            - Persistencia (win_h por defecto = 12 h):
                • Eleva +1 nivel si la regla elegida se cumple ≥60% del tiempo dentro de win_h con cobertura ≥70%. Añade evidence="pers_12h".

            D) Evidence (catálogo cerrado, SIN números):
            - v>v_alert, v>v_alarm, d>d_alert, |v|>thr_alerta, |v|>thr_alarma, d↑, v↑,
                pers_12h, de-spike, missing_param, low_snr, gap_data, hist_peak.

            E) Salida JSON estricta (sin texto extra, única):
            {
                "level": "NORMAL|ALERTA|ALARMA",
                "rationale": "≤180 chars; estado + tendencia + umbral/persistencia.",
                "justificacion": "400–800 chars; incluye números redondeados (2 decimales).",
                "confidence_0_1": 0.0,
                "actions": ["...", "...", "..."],
                "evidence": ["...","..."],
                "metrics": {
                "vel": 0.00,
                "deform": 0.00,
                "umbral_disparado": "v_alarm|v_alert|d_alert|v_alarm_with_d1|v_alarm_with_d2|thr_alerta|thr_alarma|none",
                "persistencia_h": 12
                }
            }

            F) Redacción:
            - "rationale" ≤180: nivel, tendencia (↑/↓/↔) y si hubo persistencia.
            - "justificacion" 400–800: 1) Contexto (vel X mm/h, deform Y mm). 2) Comparación/umbral. 3) Tendencia últimas Z h.
                4) Persistencia y calidad (cobertura, low_snr/gap). 5) Cierre conservador.

            G) Acciones (máx. 3): imperativas y verificables. Evitar acciones si evidence contiene missing_param crítico.

            H) Confianza (inicia en 0.60):
            - +0.15 si se disparó una regla fija.
            - +0.10 si pers_12h aplicada.
            - −0.20 si low_snr.
            - −0.15 si gap_data>10%.
            - Clip [0.0, 1.0]. Determinista.

            I) Autochequeo:
            - Un único JSON válido; límites de longitud; evidence del catálogo; precedencia fijas>adaptativas>persistencia;
                unidades homogéneas (mm, mm/h); aplica abs() según use_abs; misma entrada ⇒ misma salida.

            J) Métricas sugeridas:
            - Usa "suggested_metrics" SOLO para rellenar "metrics" (redondeo 2 decimales). No deciden nivel si difieren de los datos validados.

            K) Tiempos y auditoría:
            - Normaliza a meta.timezone (por defecto America/Santiago) y conserva UTC internamente. report_window_min guía el rango de cálculo.
            """

    # Añadir nota con la longitud objetivo (por si el usuario configuró --just-length)
    note = f"\nNota: la 'justificacion' debe tener aproximadamente {just_len} caracteres (±25%).\n"

    # Incluir explícitamente los datos disponibles para forzar al LLM a referenciarlos.
    datos = json.dumps(snapshot, ensure_ascii=False, default=str)
    return (
        policy
        + note
        + "\nDatos disponibles (usar todos):\n"
        + datos
        + "\n\nContexto:\n"
        + pd.Series(snapshot).to_json()
        + "\n"
    )
