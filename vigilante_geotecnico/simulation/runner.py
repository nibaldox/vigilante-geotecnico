"""
Runner de simulación geotécnica.

NOTA: Este archivo contiene la lógica principal de run_simulation().
Para la implementación completa, referirse a agente_geotecnico.py en el directorio raíz.
Este módulo importa y utiliza todos los componentes refactorizados.
"""

import json
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

from vigilante_geotecnico.analysis import (
    compute_thresholds_from_baseline,
    compute_thresholds_sliding,
    ema,
    summarize_window,
)
from vigilante_geotecnico.core.models import FixedRules
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.llm import build_prompt, call_deepseek, validate_justificacion_and_refs
from vigilante_geotecnico.output import print_structured_console

load_dotenv()


def run_simulation(
    csv_path: str,
    resample_rule: str,
    step_points: int,
    lookback_min: int,
    accum_rate_hours: float,
    accum_window_threshold_mm: float,
    baseline_fraction: float,
    sleep_seconds: float,
    llm_every: int,
    dry_run: bool,
    base_url: Optional[str],
    model: Optional[str],
    log_jsonl: Optional[str] = None,
    only_disagreements: bool = False,
    start_at: Optional[str] = None,
    v_alert: float = 1.0,
    v_alarm: float = 3.0,
    d_alert: float = 5.0,
    v_alarm_with_d1: float = 1.5,
    v_alarm_with_d2: float = 2.0,
    summary_json: Optional[str] = "resumen.json",
    summary_top_k: int = 10,
    emit_every_min: Optional[float] = None,
    just_length: int = 600,
) -> None:
    """Ejecuta la simulación de monitoreo geotécnico.

    NOTA: Esta es una versión simplificada que delega en los módulos refactorizados.
    Para la implementación completa con todo el flujo de procesamiento, logging de
    discrepancias, resumen final y estadísticas, ver agente_geotecnico.py original.

    Args:
        csv_path: Ruta al archivo CSV de entrada
        resample_rule: Regla de resampleo pandas
        step_points: Puntos por iteración
        lookback_min: Minutos de ventana para análisis
        accum_rate_hours: Horas para proyección de acumulación
        accum_window_threshold_mm: Umbral visual para ventana
        baseline_fraction: Fracción para baseline de umbrales
        sleep_seconds: Pausa entre iteraciones
        llm_every: Frecuencia de llamadas al LLM
        dry_run: Si True, no llama al LLM
        base_url: URL base de DeepSeek
        model: Modelo de DeepSeek
        log_jsonl: Ruta para logging JSON Lines
        only_disagreements: Solo log ar discrepancias
        start_at: Timestamp de inicio
        v_alert: Umbral fijo de velocidad alerta
        v_alarm: Umbral fijo de velocidad alarma
        d_alert: Umbral fijo de deformación alerta
        v_alarm_with_d1: Umbral combinado 1
        v_alarm_with_d2: Umbral combinado 2
        summary_json: Ruta para resumen JSON
        summary_top_k: Top K eventos para resumen
        emit_every_min: Emitir cada N minutos simulados
        just_length: Longitud objetivo para justificación LLM
    """
    # Cargar datos
    df = load_csv_with_custom_header(csv_path)
    if start_at:
        try:
            ts = pd.to_datetime(start_at)
            df = df[df["time"] >= ts].reset_index(drop=True)
        except Exception:
            pass

    _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df, resample_rule=resample_rule)
    cum_total = s_smooth

    # Calcular EMAs
    x_idx = s_smooth.index
    if len(x_idx) > 1:
        pts_per_min = max(1, int(pd.Timedelta("60s") / (x_idx[1] - x_idx[0])))
    else:
        pts_per_min = 1

    ema1h_pts = max(1, 60 * pts_per_min)
    ema3h_pts = max(1, 180 * pts_per_min)
    ema12h_pts = max(1, 720 * pts_per_min)
    ema12 = ema(s_smooth, ema1h_pts)
    ema48 = ema(s_smooth, ema3h_pts)
    ema96 = ema(s_smooth, ema12h_pts)

    # Umbrales iniciales
    thr = compute_thresholds_from_baseline(vel_mm_hr.abs(), baseline_fraction=baseline_fraction)
    print(f"Umbrales iniciales: ALERTA={thr.alerta:.3f} mm/hr | ALARMA={thr.alarma:.3f} mm/hr")

    points_per_minute = max(1, int(pd.Timedelta("60s") / (x_idx[1] - x_idx[0]))) if len(x_idx) > 1 else 30
    lookback_points = max(
        points_per_minute, int((lookback_min * 60) / ((x_idx[1] - x_idx[0]).total_seconds() if len(x_idx) > 1 else 120))
    )

    # Configuración de emisiones temporales
    emit_interval = None
    next_emit = None
    if emit_every_min is not None:
        try:
            emit_interval = pd.Timedelta(minutes=float(emit_every_min))
            next_emit = pd.to_datetime(start_at) if start_at else x_idx[0]
        except Exception:
            pass

    # API key
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key and not dry_run:
        print("ADVERTENCIA: DEEPSEEK_API_KEY no configurada. Se usará dry-run.")
        dry_run = True

    # Contadores
    level_counts: Dict[str, int] = {"NORMAL": 0, "ALERTA": 0, "ALARMA": 0}
    source_counts: Dict[str, int] = {"fixed": 0, "adaptive": 0}
    rule_counts: Dict[str, int] = defaultdict(int)
    alarm_events: List[Dict] = []
    alert_events: List[Dict] = []

    # Loop principal
    for i in range(1, len(x_idx)):
        if i % step_points != 0 and i < len(x_idx) - 1:
            continue

        # Umbrales deslizantes
        thr_sliding = compute_thresholds_sliding(vel_mm_hr.abs(), end_time=x_idx[i], window_hours=12.0)
        thr_effective = thr_sliding or thr
        thr_source = "sliding_12h" if thr_sliding is not None else "initial"

        # Resumen de ventana
        snapshot = summarize_window(
            x_idx=x_idx,
            s_smooth=s_smooth,
            vel_mm_hr=vel_mm_hr,
            cum_total=cum_total,
            ema12=ema12,
            ema48=ema48,
            ema96=ema96,
            thr=thr_effective,
            thr_source=thr_source,
            i=i,
            lookback_points=lookback_points,
            accum_period_hours=max(0.0, float(accum_rate_hours)),
            accum_window_threshold_mm=float(accum_window_threshold_mm),
            bb_k=float(os.getenv("BOLLINGER_K", "2.0")),
            fixed=FixedRules(
                v_alert=v_alert,
                v_alarm=v_alarm,
                d_alert=d_alert,
                v_alarm_with_d1=v_alarm_with_d1,
                v_alarm_with_d2=v_alarm_with_d2,
            ),
            history={
                "start_time": str(x_idx[0]) if len(x_idx) else None,
                "elapsed_hours": float((x_idx[i] - x_idx[0]).total_seconds() / 3600.0) if len(x_idx) else 0.0,
                "cum_total_min_mm": float(cum_total.min()) if len(cum_total) else 0.0,
                "cum_total_max_mm": float(cum_total.max()) if len(cum_total) else 0.0,
                "vel_abs_p95_mm_hr": float(vel_mm_hr.abs().quantile(0.95)) if len(vel_mm_hr.dropna()) else 0.0,
                "vel_abs_p99_mm_hr": float(vel_mm_hr.abs().quantile(0.99)) if len(vel_mm_hr.dropna()) else 0.0,
            },
        )

        if not snapshot:
            continue

        # Determinar si llamar al LLM
        should_call_llm = False
        llm_content: Optional[str] = None
        llm_json: Optional[Dict] = None
        disagreement = False

        if not dry_run:
            if emit_interval is not None and next_emit is not None:
                if x_idx[i] >= next_emit:
                    should_call_llm = True
            elif llm_every and (i // step_points) % max(1, llm_every) == 0:
                should_call_llm = True

        if should_call_llm:
            try:
                prompt = build_prompt(snapshot, just_len=just_length)
                llm_content = call_deepseek(
                    api_key=api_key,
                    prompt=prompt,
                    base_url=base_url,
                    model=model,
                    timeout_connect=float(os.getenv("LLM_TIMEOUT_CONNECT", "10")),
                    timeout_read=float(os.getenv("LLM_TIMEOUT_READ", "60")),
                    retries=int(os.getenv("LLM_RETRIES", "3")),
                    retry_backoff=float(os.getenv("LLM_RETRY_BACKOFF", "2.0")),
                )

                # Parse JSON response
                start = llm_content.find("{")
                end = llm_content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    llm_json = json.loads(llm_content[start : end + 1])
                    llm_level = str(llm_json.get("level", "")).upper()
                    if llm_level in {"NORMAL", "ALERTA", "ALARMA"}:
                        if llm_level != snapshot["current"]["state"]:
                            disagreement = True

                # Avanzar next_emit si se usa reloj simulado
                if emit_interval is not None and next_emit is not None:
                    while next_emit is not None and x_idx[i] >= next_emit:
                        next_emit = next_emit + emit_interval
            except Exception as e:
                print(f"Error LLM: {repr(e)}")

        # Logging JSONL (simplificado - ver original para versión completa)
        if log_jsonl and (not only_disagreements or disagreement):
            record = {
                "time": snapshot["current"]["time"],
                "current_state": snapshot["current"]["state"],
                "vel_mm_hr": snapshot["current"]["vel_mm_hr"],
                "disp_mm": snapshot["current"]["disp_mm"],
                "llm_json": llm_json,
            }
            with open(log_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Imprimir en consola
        print_structured_console(
            snapshot=snapshot,
            llm_content=llm_content,
            llm_json=llm_json,
            disagreement=disagreement,
            console_format=os.getenv("CONSOLE_FORMAT", "rich"),
            llm_error=None,
        )

        # Actualizar contadores
        lvl = str(snapshot["current"]["state"])
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
        dec = snapshot.get("decision", {})
        if dec.get("source"):
            source_counts[dec["source"]] = source_counts.get(dec["source"], 0) + 1
        if dec.get("rule"):
            rule_counts[str(dec["rule"])] += 1

        # Capturar eventos
        ev = {
            "time": snapshot["current"]["time"],
            "vel_mm_hr": float(snapshot["current"]["vel_mm_hr"]),
            "cum_disp_mm_total": float(snapshot["current"]["cum_disp_mm_total"]),
        }
        if lvl == "ALARMA":
            alarm_events.append(ev)
        elif lvl == "ALERTA":
            alert_events.append(ev)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    # Resumen final (simplificado - ver original para estadísticas completas)
    print("\n=== Resumen de simulación ===")
    print("Niveles:")
    for k in ["NORMAL", "ALERTA", "ALARMA"]:
        print(f"  - {k}: {level_counts.get(k, 0)}")
    print("Fuentes de decisión:")
    for k in ["fixed", "adaptive"]:
        print(f"  - {k}: {source_counts.get(k, 0)}")

    if summary_json:
        summary = {
            "meta": {"csv_path": csv_path, "start_at": start_at},
            "counts": {"levels": level_counts, "sources": source_counts, "rules": dict(rule_counts)},
            "events": {"alarms_count": len(alarm_events), "alerts_count": len(alert_events)},
        }
        with open(summary_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
