from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import json

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


@app.get("/api/events")
def get_events(limit: int = 200):
    if not LOG_PATH.exists():
        return {"events": []}
    lines = LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    # tomar últimos N
    lines = lines[-limit:]
    events = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            disp = obj.get("disp_mm")
            if disp is None:
                disp = obj.get("cum_disp_mm_total")
            events.append({
                "time": obj.get("time"),
                "disp_mm": disp,
                "cum_disp_mm_total": obj.get("cum_disp_mm_total"),
                "vel_mm_hr": obj.get("vel_mm_hr"),
                "state": obj.get("current_state"),
                "rationale": (obj.get("llm_json", {}) or {}).get("rationale") or obj.get("llm_rationale"),
                "llm_level": obj.get("llm_level"),
            })
        except Exception:
            continue
    return {"events": events}


@app.get("/")
def index():
    file = STATIC_PATH / "index.html"
    if file.exists():
        return FileResponse(str(file))
    return JSONResponse({"ok": True, "message": "API Viva"})


# Montar equipo Agno (si está disponible)
try:
    from agno_team import app as agno_app
    from fastapi import APIRouter
    router = APIRouter()
    app.mount("/agents", agno_app)
except Exception:
    pass

