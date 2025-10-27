import os
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb  # type: ignore
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Configuración de roles y EMAs
ROLE_EMA_HOURS = {
    'vigilante': [1, 3, 12],
    'supervisor': [12, 24, 48],
    'reportador': [1, 3, 12, 24, 48],
}

# Instrucciones para cada agente
def _vigilante_instructions() -> str:
    return (
        "Rol: Vigilante (corto plazo).\n"
        "Objetivo: evaluar última hora y tendencia reciente, emitir nivel NORMAL/ALERTA/ALARMA.\n"
        "Señales: |vel|, acumulado 12h, EMAs disp 1/3/12h, bandas, IV.\n"
        "Usa reglas fijas/adaptativas y persistencia; salida en JSON estricto."
    )

def _supervisor_instructions() -> str:
    return (
        "Rol: Supervisor (validación).\n"
        "Objetivo: corroborar el veredicto del Vigilante con contexto 12–48h.\n"
        "Señales: EMAs disp 12/24/48h, consistencia con acumulado 12h y |vel|, IV sostenida."
    )

def _reportador_instructions() -> str:
    return (
        "Rol: Reportador.\n"
        "Objetivo: redactar mensaje horario conciso y consolidar informe de 12h (día/noche)."
    )

# Configurar base de datos para historial de conversaciones
db = SqliteDb(db_file="vigilante_geotecnico.db")

# Crear agentes con DeepSeek y base de datos para historial
vigilante = Agent(
    name="Vigilante",
    model=DeepSeek(id="deepseek-chat"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=_vigilante_instructions(),
)

supervisor = Agent(
    name="Supervisor",
    model=DeepSeek(id="deepseek-chat"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=_supervisor_instructions(),
)

reportador = Agent(
    name="Reportador",
    model=DeepSeek(id="deepseek-chat"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=_reportador_instructions(),
)

# Crear AgentOS
agent_os = AgentOS(agents=[vigilante, supervisor, reportador])
app = agent_os.get_app()

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Equipo Agno (Vigilante/Supervisor/Reportador)")
    sub = p.add_subparsers(dest="cmd", required=False)

    s_serve = sub.add_parser("serve", help="Servir AgentOS UI")
    s_serve.add_argument("--reload", action="store_true", help="Auto-reload")

    s_hourly = sub.add_parser("hourly", help="Resumen horario desde registros.jsonl")
    s_hourly.add_argument("--jsonl", default="registros.jsonl", help="Ruta JSONL")
    s_hourly.add_argument("--at", default=None, help="Corte (YYYY-mm-dd HH:MM), por defecto último evento")

    s_shift = sub.add_parser("report12h", help="Informe de 12h (día/noche) desde registros.jsonl")
    s_shift.add_argument("--jsonl", default="registros.jsonl", help="Ruta JSONL")
    s_shift.add_argument("--end", default=None, help="Fin (YYYY-mm-dd HH:MM), por defecto último evento")
    s_shift.add_argument("--hours", type=float, default=12.0, help="Duración del turno (h)")
    s_shift.add_argument("--out", default="resumen_turno.json", help="Salida JSON")

    args = p.parse_args()

    def _load_events(path: str) -> pd.DataFrame:
        fp = Path(path)
        if not fp.exists():
            return pd.DataFrame()
        rows = []
        for ln in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(ln)
                rows.append({
                    'time': obj.get('time'),
                    'state': obj.get('current_state'),
                    'vel_mm_hr': obj.get('vel_mm_hr'),
                    'disp_mm': obj.get('disp_mm', obj.get('cum_disp_mm_total')),
                    'llm_level': obj.get('llm_level'),
                })
            except Exception:
                continue
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
        return df

    if not args.cmd or args.cmd == "serve":
        agent_os.serve(app="agno_team:app", reload=bool(getattr(args, 'reload', False)))
    elif args.cmd == "hourly":
        df = _load_events(args.jsonl)
        if df.empty:
            print(json.dumps({'ok': False, 'message': 'sin datos'}, ensure_ascii=False))
        else:
            t_end = pd.to_datetime(args.at) if args.at else df['time'].iloc[-1]
            t_start = t_end - pd.Timedelta(hours=1)
            win = df[(df['time'] > t_start) & (df['time'] <= t_end)].copy()
            levels = win['state'].value_counts().to_dict()
            out = {
                'window': {'start': str(t_start), 'end': str(t_end), 'n': int(len(win))},
                'levels': levels,
                'vel': {
                    'mean': float(win['vel_mm_hr'].dropna().mean()) if len(win) else 0.0,
                    'p95_abs': float(win['vel_mm_hr'].abs().quantile(0.95)) if len(win.dropna(subset=['vel_mm_hr'])) else 0.0,
                },
                'disp': {
                    'min': float(win['disp_mm'].min()) if len(win.dropna(subset=['disp_mm'])) else 0.0,
                    'max': float(win['disp_mm'].max()) if len(win.dropna(subset=['disp_mm'])) else 0.0,
                }
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.cmd == "report12h":
        df = _load_events(args.jsonl)
        if df.empty:
            print(json.dumps({'ok': False, 'message': 'sin datos'}, ensure_ascii=False))
        else:
            t_end = pd.to_datetime(args.end) if args.end else df['time'].iloc[-1]
            t_start = t_end - pd.Timedelta(hours=float(args.hours))
            win = df[(df['time'] > t_start) & (df['time'] <= t_end)].copy()
            levels = win['state'].value_counts().to_dict()
            vel_series = win['vel_mm_hr'].dropna()
            disp_series = win['disp_mm'].dropna()
            summary = {
                'shift': {'start': str(t_start), 'end': str(t_end), 'hours': float(args.hours), 'n': int(len(win))},
                'levels': levels,
                'vel': {
                    'mean': float(vel_series.mean()) if len(vel_series) else 0.0,
                    'p95_abs': float(vel_series.abs().quantile(0.95)) if len(vel_series) else 0.0,
                    'p99_abs': float(vel_series.abs().quantile(0.99)) if len(vel_series) else 0.0,
                    'max_abs': float(vel_series.abs().max()) if len(vel_series) else 0.0,
                },
                'disp': {
                    'min': float(disp_series.min()) if len(disp_series) else 0.0,
                    'max': float(disp_series.max()) if len(disp_series) else 0.0,
                },
            }
            Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'ok': True, 'out': args.out}, ensure_ascii=False))


