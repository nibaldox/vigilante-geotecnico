import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Basic logging configuration for the API module
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Vigilante Geotécnico - API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_PATH = Path("registros.jsonl")
STATIC_PATH = Path("web")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


@app.get("/api/events")
def get_events(limit: int = 200, file: Optional[str] = Query(None)):
    """Obtiene eventos desde un archivo JSONL específico."""
    log_file = Path(file) if file else LOG_PATH

    if not log_file.exists():
        return {"events": []}

    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    # tomar últimos N
    lines = lines[-limit:]
    events = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            disp = obj.get("disp_mm")
            if disp is None:
                disp = obj.get("cum_disp_mm_total")
            events.append(
                {
                    "time": obj.get("time"),
                    "disp_mm": disp,
                    "cum_disp_mm_total": obj.get("cum_disp_mm_total"),
                    "vel_mm_hr": obj.get("vel_mm_hr"),
                    "state": obj.get("current_state"),
                    "rationale": (obj.get("llm_json", {}) or {}).get("rationale") or obj.get("llm_rationale"),
                    "llm_level": obj.get("llm_level"),
                }
            )
        except Exception:
            continue
    return {"events": events}


@app.get("/api/files")
def list_files():
    """Lista archivos JSONL disponibles en el directorio actual."""
    files = [f.name for f in Path(".").glob("*.jsonl")]
    return {"files": sorted(files)}


@app.get("/")
def index():
    file = STATIC_PATH / "index.html"
    if file.exists():
        return FileResponse(str(file))
    return JSONResponse({"ok": True, "message": "API Viva"})


@app.get("/agents.html")
def agents_page():
    """Sirve la página de agentes."""
    file = STATIC_PATH / "agents.html"
    if file.exists():
        return FileResponse(str(file))
    return JSONResponse({"ok": False, "message": "Agents page not found"}, status_code=404)


# ============================================================================
# GENERACIÓN DE REPORTES
# ============================================================================


def generate_report(log_file: Path = LOG_PATH, hours: float = 12.0) -> dict:
    """Genera un reporte de las últimas N horas."""
    if not log_file.exists():
        return {"ok": False, "message": "Archivo no encontrado"}

    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    events = []

    for ln in lines:
        try:
            obj = json.loads(ln)
            events.append(obj)
        except Exception:
            continue

    if not events:
        return {"ok": False, "message": "Sin datos"}

    # Filtrar por tiempo
    now = datetime.now()
    cutoff = now.timestamp() - (hours * 3600)

    filtered = []
    for e in events:
        try:
            time_str = e.get("time", "")
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

            if dt.timestamp() >= cutoff:
                filtered.append(e)
        except Exception:
            continue

    if not filtered:
        return {"ok": False, "message": f"Sin datos en últimas {hours}h"}

    # Estadísticas
    states = {"NORMAL": 0, "ALERTA": 0, "ALARMA": 0}
    velocities = []
    displacements = []

    for e in filtered:
        state = e.get("current_state") or e.get("state") or "NORMAL"
        states[state] = states.get(state, 0) + 1

        vel = e.get("vel_mm_hr")
        if vel is not None:
            velocities.append(float(vel))

        disp = e.get("disp_mm") or e.get("cum_disp_mm_total")
        if disp is not None:
            displacements.append(float(disp))

    # Calcular estadísticas
    vel_mean = sum(velocities) / len(velocities) if velocities else 0
    vel_max = max(velocities) if velocities else 0
    vel_abs_sorted = sorted([abs(v) for v in velocities])
    vel_p95 = vel_abs_sorted[int(len(vel_abs_sorted) * 0.95)] if vel_abs_sorted else 0
    vel_p99 = vel_abs_sorted[int(len(vel_abs_sorted) * 0.99)] if vel_abs_sorted else 0

    disp_min = min(displacements) if displacements else 0
    disp_max = max(displacements) if displacements else 0
    disp_range = disp_max - disp_min

    # Eventos destacados (alarmas y alertas)
    highlights = []
    for e in filtered:
        state = e.get("current_state") or e.get("state")
        if state in ["ALERTA", "ALARMA"]:
            highlights.append({
                "time": e.get("time"),
                "state": state,
                "vel_mm_hr": e.get("vel_mm_hr"),
                "disp_mm": e.get("disp_mm") or e.get("cum_disp_mm_total"),
                "rationale": (e.get("llm_json", {}) or {}).get("rationale") or e.get("llm_rationale", ""),
            })

    # Construir reporte
    turno = "DÍA" if 6 <= now.hour < 18 else "NOCHE"
    start_time = filtered[0].get("time", "")
    end_time = filtered[-1].get("time", "")

    report = {
        "ok": True,
        "generated_at": now.isoformat(),
        "turno": turno,
        "period": {"start": start_time, "end": end_time, "hours": hours, "n_events": len(filtered)},
        "summary": {
            "states": states,
            "total_events": len(filtered),
            "normal_pct": round(100 * states.get("NORMAL", 0) / len(filtered), 1) if filtered else 0,
            "alerta_pct": round(100 * states.get("ALERTA", 0) / len(filtered), 1) if filtered else 0,
            "alarma_pct": round(100 * states.get("ALARMA", 0) / len(filtered), 1) if filtered else 0,
        },
        "metrics": {
            "velocity": {
                "mean_mm_hr": round(vel_mean, 3),
                "max_mm_hr": round(vel_max, 3),
                "p95_abs_mm_hr": round(vel_p95, 3),
                "p99_abs_mm_hr": round(vel_p99, 3),
            },
            "displacement": {
                "min_mm": round(disp_min, 3),
                "max_mm": round(disp_max, 3),
                "range_mm": round(disp_range, 3),
            },
        },
        "highlights": highlights[:20],  # Top 20 eventos
    }

    return report


def save_scheduled_report():
    """Genera y guarda reporte automático cada 12h."""
    try:
        logging.info("Generando reporte automático de 12h...")
        report = generate_report(LOG_PATH, hours=12.0)

        if report.get("ok"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = REPORTS_DIR / f"reporte_auto_{timestamp}.json"

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logging.info(f"✅ Reporte guardado: {filename}")

            # También generar versión markdown
            md_content = format_report_markdown(report)
            md_filename = REPORTS_DIR / f"reporte_auto_{timestamp}.md"
            md_filename.write_text(md_content, encoding="utf-8")

            logging.info(f"✅ Reporte MD guardado: {md_filename}")
        else:
            logging.warning(f"⚠️ No se pudo generar reporte: {report.get('message')}")

    except Exception as e:
        logging.exception(f"❌ Error generando reporte automático: {e}")


def format_report_markdown(report: dict) -> str:
    """Formatea el reporte en Markdown."""
    lines = []
    lines.append("# 📊 Reporte Automático - Vigilante Geotécnico\n")

    period = report.get("period", {})
    summary = report.get("summary", {})
    metrics = report.get("metrics", {})

    lines.append(f"**Generado**: {report.get('generated_at', '')}\n")
    lines.append(f"**Turno**: {report.get('turno', '')} ({period.get('hours', 0)}h)\n")
    lines.append(f"**Período**: {period.get('start', '')} a {period.get('end', '')}\n")
    lines.append(f"**Total eventos**: {period.get('n_events', 0)}\n")

    lines.append("\n## 📈 Distribución de Estados\n")
    states = summary.get("states", {})
    lines.append(f"- **NORMAL**: {states.get('NORMAL', 0)} ({summary.get('normal_pct', 0)}%)")
    lines.append(f"- **ALERTA**: {states.get('ALERTA', 0)} ({summary.get('alerta_pct', 0)}%)")
    lines.append(f"- **ALARMA**: {states.get('ALARMA', 0)} ({summary.get('alarma_pct', 0)}%)\n")

    lines.append("\n## ⚡ Métricas de Velocidad\n")
    vel = metrics.get("velocity", {})
    lines.append(f"- **Promedio**: {vel.get('mean_mm_hr', 0):.3f} mm/hr")
    lines.append(f"- **Máxima**: {vel.get('max_mm_hr', 0):.3f} mm/hr")
    lines.append(f"- **P95 (|vel|)**: {vel.get('p95_abs_mm_hr', 0):.3f} mm/hr")
    lines.append(f"- **P99 (|vel|)**: {vel.get('p99_abs_mm_hr', 0):.3f} mm/hr\n")

    lines.append("\n## 📏 Métricas de Desplazamiento\n")
    disp = metrics.get("displacement", {})
    lines.append(f"- **Mínimo**: {disp.get('min_mm', 0):.3f} mm")
    lines.append(f"- **Máximo**: {disp.get('max_mm', 0):.3f} mm")
    lines.append(f"- **Rango**: {disp.get('range_mm', 0):.3f} mm\n")

    highlights = report.get("highlights", [])
    if highlights:
        lines.append("\n## 🚨 Eventos Destacados (ALERTA/ALARMA)\n")
        for i, h in enumerate(highlights[:10], 1):
            lines.append(f"\n### {i}. {h.get('time', '')} - **{h.get('state', '')}**")
            lines.append(f"- **Velocidad**: {h.get('vel_mm_hr', 0):.3f} mm/hr")
            lines.append(f"- **Desplazamiento**: {h.get('disp_mm', 0):.3f} mm")
            if h.get("rationale"):
                lines.append(f"- **Análisis**: {h.get('rationale', '')[:200]}...")

    lines.append("\n---\n")
    lines.append("*Generado automáticamente por Vigilante Geotécnico*")

    return "\n".join(lines)


@app.get("/api/reports/generate")
def api_generate_report(hours: float = Query(12.0), file: Optional[str] = Query(None)):
    """Endpoint para generar reporte bajo demanda."""
    log_file = Path(file) if file else LOG_PATH
    report = generate_report(log_file, hours)

    if report.get("ok"):
        # Guardar reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = REPORTS_DIR / f"reporte_manual_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        report["saved_to"] = str(filename)

    return report


@app.get("/api/reports/list")
def list_reports():
    """Lista reportes generados."""
    reports = sorted(REPORTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    return {"reports": [{"file": r.name, "created": datetime.fromtimestamp(r.stat().st_mtime).isoformat()} for r in reports[:50]]}


@app.get("/api/reports/{filename}")
def get_report(filename: str):
    """Obtiene un reporte específico."""
    report_file = REPORTS_DIR / filename
    if not report_file.exists():
        return JSONResponse({"ok": False, "message": "Reporte no encontrado"}, status_code=404)

    return JSONResponse(json.loads(report_file.read_text(encoding="utf-8")))


# ============================================================================
# SCHEDULER DE REPORTES AUTOMÁTICOS
# ============================================================================

scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    """Inicia el scheduler de reportes automáticos."""
    # Reportes a las 6:30 AM y 6:30 PM todos los días
    scheduler.add_job(
        save_scheduled_report,
        trigger=CronTrigger(hour=6, minute=30),
        id="reporte_630am",
        name="Reporte automático 6:30 AM",
        replace_existing=True,
    )

    scheduler.add_job(
        save_scheduled_report,
        trigger=CronTrigger(hour=18, minute=30),
        id="reporte_1830pm",
        name="Reporte automático 6:30 PM",
        replace_existing=True,
    )

    scheduler.start()
    logging.info("✅ Scheduler iniciado - Reportes automáticos a las 6:30 AM y 6:30 PM")


@app.on_event("shutdown")
def shutdown_scheduler():
    """Detiene el scheduler al apagar la aplicación."""
    scheduler.shutdown()
    logging.info("🛑 Scheduler detenido")


# ============================================================================
# MONTAR AGNO TEAM
# ============================================================================

# Montar equipo Agno (si está disponible)
try:
    from fastapi import APIRouter

    from agno_team import app as agno_app

    router = APIRouter()
    app.mount("/agents", agno_app)
except Exception:
    # Registrar la excepción para facilitar debugging en despliegues
    logging.exception("No se pudo montar agno_team (agents UI will not be available)")
