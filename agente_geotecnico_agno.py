#!/usr/bin/env python
"""
Agente Geotécnico con Framework Agno.

Esta implementación aprovecha el framework Agno para crear un sistema multi-agente
de monitoreo geotécnico de alto rendimiento, integrando la lógica modular de
vigilante_geotecnico con las capacidades de Agno.

Agentes:
    - Vigilante: Análisis de corto plazo (1-3h), detección de eventos
    - Supervisor: Validación de medio plazo (12-48h), confirmación de alarmas
    - Reportador: Generación de reportes consolidados

Uso:
    python agente_geotecnico_agno.py analyze --csv disp_example.csv
    python agente_geotecnico_agno.py serve --reload
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.deepseek import DeepSeek
from agno.os import AgentOS
from dotenv import load_dotenv

from vigilante_geotecnico.analysis import (
    compute_thresholds_from_baseline,
    compute_thresholds_sliding,
    ema,
    summarize_window,
)
from vigilante_geotecnico.core.models import FixedRules, Thresholds
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.output import print_structured_console

load_dotenv()

# ============================================================================
# TOOLS: Funciones que los agentes pueden usar
# ============================================================================


def tool_load_geotechnical_data(csv_path: str, start_at: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga y preprocesa datos geotécnicos desde CSV.

    Args:
        csv_path: Ruta al archivo CSV con datos ARCSAR
        start_at: Timestamp de inicio (opcional)

    Returns:
        Dict con series temporales preprocesadas y metadatos
    """
    try:
        df = load_csv_with_custom_header(csv_path)

        if start_at:
            ts = pd.to_datetime(start_at)
            df = df[df["time"] >= ts].reset_index(drop=True)

        _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df, resample_rule="2T")

        # Calcular EMAs
        x_idx = s_smooth.index
        if len(x_idx) > 1:
            pts_per_min = max(1, int(pd.Timedelta("60s") / (x_idx[1] - x_idx[0])))
        else:
            pts_per_min = 1

        ema1h = ema(s_smooth, max(1, 60 * pts_per_min))
        ema3h = ema(s_smooth, max(1, 180 * pts_per_min))
        ema12h = ema(s_smooth, max(1, 720 * pts_per_min))
        ema24h = ema(s_smooth, max(1, 1440 * pts_per_min))
        ema48h = ema(s_smooth, max(1, 2880 * pts_per_min))

        return {
            "status": "success",
            "n_points": len(s_smooth),
            "time_range": {
                "start": str(x_idx[0]) if len(x_idx) > 0 else None,
                "end": str(x_idx[-1]) if len(x_idx) > 0 else None,
            },
            "series": {
                "displacement": s_smooth.tolist(),
                "velocity": vel_mm_hr.tolist(),
                "ema_1h": ema1h.tolist(),
                "ema_3h": ema3h.tolist(),
                "ema_12h": ema12h.tolist(),
                "ema_24h": ema24h.tolist(),
                "ema_48h": ema48h.tolist(),
            },
            "stats": {
                "disp_min": float(s_smooth.min()),
                "disp_max": float(s_smooth.max()),
                "disp_range": float(s_smooth.max() - s_smooth.min()),
                "vel_mean": float(vel_mm_hr.mean()),
                "vel_std": float(vel_mm_hr.std()),
                "vel_p95": float(vel_mm_hr.abs().quantile(0.95)),
                "vel_p99": float(vel_mm_hr.abs().quantile(0.99)),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_compute_thresholds(csv_path: str, baseline_fraction: float = 0.2) -> Dict[str, Any]:
    """
    Calcula umbrales adaptativos para alertas y alarmas.

    Args:
        csv_path: Ruta al archivo CSV
        baseline_fraction: Fracción del baseline para cálculo

    Returns:
        Dict con umbrales calculados
    """
    try:
        df = load_csv_with_custom_header(csv_path)
        _, _, _, vel_mm_hr, _ = preprocess_series(df, resample_rule="2T")

        thr = compute_thresholds_from_baseline(vel_mm_hr.abs(), baseline_fraction=baseline_fraction)

        return {
            "status": "success",
            "thresholds": {"alerta": float(thr.alerta), "alarma": float(thr.alarma)},
            "method": "baseline_mad_percentile",
            "baseline_fraction": baseline_fraction,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_analyze_window(
    csv_path: str, window_end_idx: int, lookback_minutes: int = 60, baseline_fraction: float = 0.2
) -> Dict[str, Any]:
    """
    Analiza una ventana temporal específica del monitoreo.

    Args:
        csv_path: Ruta al archivo CSV
        window_end_idx: Índice final de la ventana
        lookback_minutes: Minutos hacia atrás para análisis
        baseline_fraction: Fracción del baseline

    Returns:
        Dict con snapshot completo de la ventana
    """
    try:
        df = load_csv_with_custom_header(csv_path)
        _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df, resample_rule="2T")

        x_idx = s_smooth.index
        if window_end_idx >= len(x_idx):
            window_end_idx = len(x_idx) - 1

        # EMAs
        if len(x_idx) > 1:
            pts_per_min = max(1, int(pd.Timedelta("60s") / (x_idx[1] - x_idx[0])))
        else:
            pts_per_min = 1

        ema12 = ema(s_smooth, max(1, 60 * pts_per_min))
        ema48 = ema(s_smooth, max(1, 180 * pts_per_min))
        ema96 = ema(s_smooth, max(1, 720 * pts_per_min))

        # Umbrales
        thr = compute_thresholds_from_baseline(vel_mm_hr.abs(), baseline_fraction=baseline_fraction)
        thr_sliding = compute_thresholds_sliding(vel_mm_hr.abs(), end_time=x_idx[window_end_idx], window_hours=12.0)
        thr_effective = thr_sliding or thr
        thr_source = "sliding_12h" if thr_sliding is not None else "baseline"

        # Lookback points
        lookback_points = max(
            pts_per_min, int((lookback_minutes * 60) / ((x_idx[1] - x_idx[0]).total_seconds() if len(x_idx) > 1 else 120))
        )

        # Fixed rules
        fixed = FixedRules(
            v_alert=float(os.getenv("V_ALERT", "1.0")),
            v_alarm=float(os.getenv("V_ALARM", "3.0")),
            d_alert=float(os.getenv("D_ALERT", "5.0")),
            v_alarm_with_d1=float(os.getenv("V_ALARM_WITH_D1", "1.5")),
            v_alarm_with_d2=float(os.getenv("V_ALARM_WITH_D2", "2.0")),
        )

        # Snapshot
        snapshot = summarize_window(
            x_idx=x_idx,
            s_smooth=s_smooth,
            vel_mm_hr=vel_mm_hr,
            cum_total=s_smooth,
            ema12=ema12,
            ema48=ema48,
            ema96=ema96,
            thr=thr_effective,
            thr_source=thr_source,
            i=window_end_idx,
            lookback_points=lookback_points,
            accum_period_hours=12.0,
            accum_window_threshold_mm=10.0,
            bb_k=2.0,
            fixed=fixed,
            history={
                "start_time": str(x_idx[0]) if len(x_idx) else None,
                "elapsed_hours": float((x_idx[window_end_idx] - x_idx[0]).total_seconds() / 3600.0) if len(x_idx) else 0.0,
                "cum_total_min_mm": float(s_smooth.min()),
                "cum_total_max_mm": float(s_smooth.max()),
                "vel_abs_p95_mm_hr": float(vel_mm_hr.abs().quantile(0.95)),
                "vel_abs_p99_mm_hr": float(vel_mm_hr.abs().quantile(0.99)),
            },
        )

        return {"status": "success", "snapshot": snapshot}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_get_recent_events(jsonl_path: str = "registros.jsonl", hours: float = 1.0) -> Dict[str, Any]:
    """
    Recupera eventos recientes desde el log JSONL.

    Args:
        jsonl_path: Ruta al archivo JSONL
        hours: Horas hacia atrás

    Returns:
        Dict con eventos y estadísticas
    """
    try:
        fp = Path(jsonl_path)
        if not fp.exists():
            return {"status": "success", "events": [], "stats": {}}

        rows = []
        for ln in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(ln)
                rows.append(
                    {
                        "time": obj.get("time"),
                        "state": obj.get("current_state"),
                        "vel_mm_hr": obj.get("vel_mm_hr"),
                        "disp_mm": obj.get("disp_mm", obj.get("cum_disp_mm_total")),
                        "llm_level": obj.get("llm_level"),
                    }
                )
            except Exception:
                continue

        if not rows:
            return {"status": "success", "events": [], "stats": {}}

        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

        t_end = df["time"].iloc[-1]
        t_start = t_end - pd.Timedelta(hours=hours)
        win = df[(df["time"] > t_start) & (df["time"] <= t_end)].copy()

        levels = win["state"].value_counts().to_dict()
        vel_series = win["vel_mm_hr"].dropna()
        disp_series = win["disp_mm"].dropna()

        return {
            "status": "success",
            "window": {"start": str(t_start), "end": str(t_end), "hours": hours, "n_events": int(len(win))},
            "events": win.to_dict(orient="records"),
            "stats": {
                "levels": levels,
                "vel_mean": float(vel_series.mean()) if len(vel_series) else 0.0,
                "vel_p95_abs": float(vel_series.abs().quantile(0.95)) if len(vel_series) else 0.0,
                "disp_min": float(disp_series.min()) if len(disp_series) else 0.0,
                "disp_max": float(disp_series.max()) if len(disp_series) else 0.0,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# AGENTES AGNO
# ============================================================================


def create_vigilante_agent(db: SqliteDb) -> Agent:
    """
    Crea el agente Vigilante con capacidades de análisis de corto plazo.

    El Vigilante monitorea en tiempo real las señales geotécnicas (1-3h),
    detecta eventos anómalos y emite clasificaciones NORMAL/ALERTA/ALARMA.
    """
    instructions = """
Rol: Vigilante Geotécnico (Análisis de Corto Plazo)

OBJETIVO:
- Evaluar la última hora y tendencias recientes (1-3h)
- Detectar eventos anómalos en velocidad y desplazamiento
- Emitir clasificación: NORMAL, ALERTA o ALARMA

SEÑALES CLAVE:
1. Velocidad absoluta |vel| (mm/hr)
2. Desplazamiento acumulado últimas 12h
3. EMAs de desplazamiento: 1h, 3h, 12h
4. Bandas de Bollinger (volatilidad)
5. Índice de Velocidad (IV) - persistencia

REGLAS DE DECISIÓN:

ALARMA si:
- |vel| > umbral_alarma adaptativo (MAD + percentiles)
- vel > 3.0 mm/hr (fijo) + desplazamiento > 5mm
- vel > 2.0 mm/hr + acum_12h > 10mm
- Divergencia fuerte EMAs (1h >> 3h >> 12h)
- IV > 0.7 sostenido (alta persistencia)

ALERTA si:
- |vel| > umbral_alerta adaptativo
- vel > 1.0 mm/hr (fijo)
- Aceleración reciente detectable
- EMAs muestran separación moderada
- Banda Bollinger superior rota

NORMAL:
- Todas las métricas dentro de rangos normales
- Tendencias estables o decrecientes

FORMATO DE SALIDA (JSON estricto):
{
  "level": "NORMAL|ALERTA|ALARMA",
  "confidence": 0.0-1.0,
  "primary_trigger": "descripción",
  "metrics": {
    "vel_mm_hr": valor,
    "disp_mm": valor,
    "ema_1h": valor,
    "iv": valor
  },
  "justification": "Explicación concisa basada en datos"
}

IMPORTANTE:
- Usa SIEMPRE las herramientas disponibles para obtener datos reales
- No inventes valores, consulta tool_analyze_window
- Sé conservador: mejor ALERTA que falsa ALARMA
- Justifica con métricas concretas, no intuiciones
"""

    agent = Agent(
        name="Vigilante",
        model=DeepSeek(id="deepseek-chat"),
        db=db,
        add_history_to_context=True,
        markdown=True,
        instructions=instructions,
        tools=[tool_analyze_window, tool_get_recent_events, tool_compute_thresholds],
        show_tool_calls=True,
    )

    return agent


def create_supervisor_agent(db: SqliteDb) -> Agent:
    """
    Crea el agente Supervisor con validación de medio plazo.

    El Supervisor corrobora las decisiones del Vigilante con contexto
    de 12-48h, confirmando alarmas y filtrando falsos positivos.
    """
    instructions = """
Rol: Supervisor Geotécnico (Validación de Medio Plazo)

OBJETIVO:
- Corroborar el veredicto del Vigilante con contexto 12-48h
- Filtrar falsos positivos usando tendencias de largo plazo
- Confirmar o ajustar clasificación basado en persistencia

SEÑALES CLAVE:
1. EMAs de desplazamiento: 12h, 24h, 48h
2. Consistencia de |vel| en ventanas de 12h
3. Acumulado 12h vs acumulado 24h
4. Índice de Velocidad (IV) sostenido > 6h
5. Historial de eventos recientes (registros.jsonl)

CRITERIOS DE VALIDACIÓN:

CONFIRMAR ALARMA si:
- Vigilante emite ALARMA + EMAs 12h/24h/48h convergentes al alza
- IV > 0.6 sostenido últimas 6+ horas
- Acumulado 12h > 80% del acumulado 24h (aceleración reciente)
- Historial muestra escalada: NORMAL → ALERTA → ALARMA
- No hay evidencia de ruido o artefactos

DEGRADAR a ALERTA si:
- Vigilante emite ALARMA pero EMAs 24h/48h estables
- Evento aislado sin persistencia
- IV < 0.4 (baja persistencia)
- Historial muestra fluctuaciones erráticas

CONFIRMAR NORMAL si:
- EMAs 12h/24h/48h planas o descendentes
- Velocidades consistentemente bajas
- Sin eventos anómalos en últimas 12h

FORMATO DE SALIDA (JSON estricto):
{
  "validation": "CONFIRMADO|DEGRADADO|ESCALADO",
  "final_level": "NORMAL|ALERTA|ALARMA",
  "vigilante_level": "nivel_original",
  "confidence": 0.0-1.0,
  "rationale": "Explicación basada en tendencias 12-48h",
  "context": {
    "ema_12h": valor,
    "ema_24h": valor,
    "ema_48h": valor,
    "iv_6h_avg": valor
  }
}

IMPORTANTE:
- Consulta tool_get_recent_events con hours=12 o más
- Usa tool_analyze_window para contexto extendido
- Prioriza persistencia sobre picos aislados
- Comunica claramente si difiere del Vigilante
"""

    agent = Agent(
        name="Supervisor",
        model=DeepSeek(id="deepseek-chat"),
        db=db,
        add_history_to_context=True,
        markdown=True,
        instructions=instructions,
        tools=[tool_analyze_window, tool_get_recent_events, tool_load_geotechnical_data],
        show_tool_calls=True,
    )

    return agent


def create_reportador_agent(db: SqliteDb) -> Agent:
    """
    Crea el agente Reportador para generación de informes consolidados.

    El Reportador sintetiza análisis del Vigilante y Supervisor en reportes
    concisos para operadores y stakeholders.
    """
    instructions = """
Rol: Reportador Geotécnico

OBJETIVO:
- Sintetizar análisis del Vigilante y Supervisor
- Generar reportes horarios concisos para operadores
- Producir informes consolidados de turno (12h día/noche)

TIPOS DE REPORTE:

1. REPORTE HORARIO:
- Resumen ejecutivo de última hora
- Estado actual: NORMAL/ALERTA/ALARMA
- Métricas clave: vel, disp, tendencia
- Acciones recomendadas si aplica

2. REPORTE DE TURNO (12h):
- Estadísticas del período completo
- Eventos destacados (alarmas, alertas)
- Evolución de tendencias (EMAs)
- Proyección próximas 12h
- Recomendaciones operacionales

FORMATO REPORTE HORARIO:
```
=== VIGILANTE GEOTÉCNICO - Reporte Horario ===
Período: [timestamp_inicio] a [timestamp_fin]
Estado: [NORMAL/ALERTA/ALARMA]

Métricas:
- Velocidad: [valor] mm/hr (promedio), [p95] mm/hr (P95)
- Desplazamiento: [min] a [max] mm (rango)
- Tendencia: [ESTABLE/ASCENDENTE/DESCENDENTE]

Análisis:
[Síntesis de Vigilante + validación Supervisor]

Acciones: [si ALERTA/ALARMA, recomendar acciones concretas]
```

FORMATO REPORTE TURNO (12h):
```
=== VIGILANTE GEOTÉCNICO - Reporte de Turno ===
Turno: [DÍA/NOCHE] | [timestamp_inicio] a [timestamp_fin]

Resumen:
- Total eventos: [n]
- Distribución: [n_normal] NORMAL, [n_alerta] ALERTA, [n_alarma] ALARMA
- Máxima velocidad: [valor] mm/hr a las [timestamp]
- Desplazamiento total: [delta] mm

Eventos Destacados:
[Lista cronológica de ALERTAs y ALARMAs con contexto]

Tendencias (EMAs):
- 12h: [tendencia]
- 24h: [tendencia]
- 48h: [tendencia]

Proyección:
[Expectativa próximas 12h basada en tendencias]

Recomendaciones:
[Acciones operacionales si aplica]
```

IMPORTANTE:
- Usa tool_get_recent_events para datos históricos
- Sé conciso: máximo 200 palabras por reporte horario
- Usa lenguaje claro para no-expertos
- Destaca solo información accionable
- Incluye siempre timestamps precisos
"""

    agent = Agent(
        name="Reportador",
        model=DeepSeek(id="deepseek-chat"),
        db=db,
        add_history_to_context=True,
        markdown=True,
        instructions=instructions,
        tools=[tool_get_recent_events, tool_load_geotechnical_data],
        show_tool_calls=True,
    )

    return agent


# ============================================================================
# CONFIGURACIÓN AGENTE OS
# ============================================================================

# Base de datos para historial persistente
db = SqliteDb(db_file="vigilante_geotecnico_agno.db")

# Crear agentes
vigilante = create_vigilante_agent(db)
supervisor = create_supervisor_agent(db)
reportador = create_reportador_agent(db)

# Crear AgentOS
agent_os = AgentOS(agents=[vigilante, supervisor, reportador])
app = agent_os.get_app()


# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================


def run_analysis(csv_path: str, output_jsonl: str = "registros.jsonl", interval_minutes: int = 60) -> None:
    """
    Ejecuta análisis completo usando el equipo de agentes Agno.

    Args:
        csv_path: Ruta al CSV con datos geotécnicos
        output_jsonl: Ruta para logging de eventos
        interval_minutes: Intervalo entre análisis (minutos)
    """
    print(f"\n{'='*80}")
    print(f"VIGILANTE GEOTÉCNICO - Análisis con Agno Framework")
    print(f"{'='*80}\n")
    print(f"📂 CSV: {csv_path}")
    print(f"📝 Log: {output_jsonl}")
    print(f"⏱️  Intervalo: {interval_minutes} minutos\n")

    # Cargar datos
    print("⚙️  Cargando y preprocesando datos...")
    df = load_csv_with_custom_header(csv_path)
    _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df, resample_rule="2T")

    x_idx = s_smooth.index
    n_points = len(x_idx)
    print(f"✅ {n_points} puntos cargados | Rango: {x_idx[0]} a {x_idx[-1]}\n")

    # Calcular intervalo en puntos
    if len(x_idx) > 1:
        pts_per_min = max(1, int(pd.Timedelta("60s") / (x_idx[1] - x_idx[0])))
    else:
        pts_per_min = 1

    step_points = max(1, interval_minutes * pts_per_min)

    # Loop de análisis
    events_log = []

    for i in range(step_points, n_points, step_points):
        timestamp = str(x_idx[i])
        print(f"\n{'─'*80}")
        print(f"🕐 Análisis en t={timestamp} (punto {i}/{n_points})")
        print(f"{'─'*80}\n")

        # 1. Vigilante analiza ventana
        print("👁️  Vigilante analizando...")
        vigilante_prompt = f"""
Analiza la ventana geotécnica en el punto {i} del archivo {csv_path}.

Usa tool_analyze_window con:
- csv_path: {csv_path}
- window_end_idx: {i}
- lookback_minutes: 60

Evalúa las señales y emite tu veredicto en formato JSON.
"""
        vigilante_response = vigilante.run(vigilante_prompt, stream=False)
        print(f"✅ Vigilante: {vigilante_response.content[:200]}...\n")

        # 2. Supervisor valida
        print("🔍 Supervisor validando...")
        supervisor_prompt = f"""
El Vigilante ha emitido el siguiente análisis:

{vigilante_response.content}

Valida este veredicto usando contexto de 12-48h.

Usa tool_get_recent_events con hours=12 para historial.
Usa tool_analyze_window para tendencias extendidas.

¿Confirmas, degradas o escalas el nivel? Responde en JSON.
"""
        supervisor_response = supervisor.run(supervisor_prompt, stream=False)
        print(f"✅ Supervisor: {supervisor_response.content[:200]}...\n")

        # 3. Registrar evento
        event_record = {
            "time": timestamp,
            "point_idx": i,
            "vigilante_content": str(vigilante_response.content),
            "supervisor_content": str(supervisor_response.content),
        }

        events_log.append(event_record)

        # Guardar en JSONL
        with open(output_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_record, ensure_ascii=False) + "\n")

    # Reporte final
    print(f"\n{'='*80}")
    print("📊 GENERANDO REPORTE FINAL")
    print(f"{'='*80}\n")

    reportador_prompt = f"""
Se ha completado un análisis de {n_points} puntos del archivo {csv_path}.

Total de análisis realizados: {len(events_log)}

Genera un reporte consolidado usando tool_get_recent_events.

Incluye:
1. Resumen ejecutivo
2. Estadísticas del período completo
3. Eventos destacados (alertas/alarmas)
4. Proyección y recomendaciones
"""

    report = reportador.run(reportador_prompt, stream=False)
    print(report.content)

    # Guardar reporte
    report_path = f"reporte_agno_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    Path(report_path).write_text(report.content, encoding="utf-8")
    print(f"\n✅ Reporte guardado en: {report_path}")


def run_hourly_report(jsonl_path: str = "registros.jsonl") -> None:
    """Genera reporte horario de la última hora."""
    print("\n📊 Generando reporte horario...\n")

    prompt = f"""
Genera un reporte horario conciso usando tool_get_recent_events con hours=1.0.

Archivo: {jsonl_path}

Sigue el formato de reporte horario de tus instrucciones.
"""

    report = reportador.run(prompt, stream=False)
    print(report.content)


def run_shift_report(jsonl_path: str = "registros.jsonl", hours: float = 12.0) -> None:
    """Genera reporte de turno (12h día/noche)."""
    print(f"\n📊 Generando reporte de turno ({hours}h)...\n")

    prompt = f"""
Genera un reporte de turno completo usando tool_get_recent_events con hours={hours}.

Archivo: {jsonl_path}

Sigue el formato de reporte de turno de tus instrucciones.
"""

    report = reportador.run(prompt, stream=False)
    print(report.content)

    # Guardar
    report_path = f"reporte_turno_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    Path(report_path).write_text(report.content, encoding="utf-8")
    print(f"\n✅ Reporte guardado en: {report_path}")


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI principal para agente geotécnico con Agno."""
    parser = argparse.ArgumentParser(
        description="Vigilante Geotécnico con Framework Agno",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Servir AgentOS UI interactiva
  python agente_geotecnico_agno.py serve --reload

  # Análisis completo de CSV
  python agente_geotecnico_agno.py analyze --csv disp_example.csv --interval 60

  # Reporte horario desde logs
  python agente_geotecnico_agno.py hourly --jsonl registros.jsonl

  # Reporte de turno (12h)
  python agente_geotecnico_agno.py shift --jsonl registros.jsonl --hours 12

Para más información sobre Agno Framework: https://docs.agno.com
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # Comando: serve
    parser_serve = subparsers.add_parser("serve", help="Servir AgentOS UI interactiva")
    parser_serve.add_argument("--reload", action="store_true", help="Auto-reload en cambios")
    parser_serve.add_argument("--port", type=int, default=7277, help="Puerto (default: 7277)")

    # Comando: analyze
    parser_analyze = subparsers.add_parser("analyze", help="Análisis completo de datos geotécnicos")
    parser_analyze.add_argument("--csv", required=True, help="Ruta al archivo CSV")
    parser_analyze.add_argument("--output", default="registros.jsonl", help="Archivo JSONL de salida")
    parser_analyze.add_argument("--interval", type=int, default=60, help="Intervalo en minutos (default: 60)")

    # Comando: hourly
    parser_hourly = subparsers.add_parser("hourly", help="Reporte horario desde logs")
    parser_hourly.add_argument("--jsonl", default="registros.jsonl", help="Archivo JSONL de entrada")

    # Comando: shift
    parser_shift = subparsers.add_parser("shift", help="Reporte de turno (día/noche)")
    parser_shift.add_argument("--jsonl", default="registros.jsonl", help="Archivo JSONL de entrada")
    parser_shift.add_argument("--hours", type=float, default=12.0, help="Duración del turno en horas")

    args = parser.parse_args()

    if not args.command or args.command == "serve":
        print("\n🚀 Iniciando AgentOS UI...")
        print(f"📡 Agentes disponibles: Vigilante, Supervisor, Reportador")
        print(f"🌐 URL: http://localhost:{getattr(args, 'port', 7277)}\n")
        agent_os.serve(app="agente_geotecnico_agno:app", reload=getattr(args, "reload", False))

    elif args.command == "analyze":
        if not Path(args.csv).exists():
            print(f"❌ Error: Archivo {args.csv} no encontrado")
            return
        run_analysis(csv_path=args.csv, output_jsonl=args.output, interval_minutes=args.interval)

    elif args.command == "hourly":
        run_hourly_report(jsonl_path=args.jsonl)

    elif args.command == "shift":
        run_shift_report(jsonl_path=args.jsonl, hours=args.hours)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
