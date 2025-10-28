# 🎯 Nuevas Funcionalidades - Vigilante Geotécnico

## 📋 Tabla de Contenidos

- [Selector de Archivos](#-selector-de-archivos)
- [Reportes Automáticos](#-reportes-automáticos)
- [Servidor Integrado](#-servidor-integrado)
- [API REST Completa](#-api-rest-completa)

---

## 📁 Selector de Archivos

### Descripción
La interfaz web ahora permite seleccionar dinámicamente el archivo JSONL desde el cual cargar los datos, sin necesidad de reiniciar el servidor.

### Características

✅ **Dropdown dinámico** con todos los archivos `.jsonl` disponibles
✅ **Actualización automática** del gráfico al cambiar de archivo
✅ **Persistencia** de selección (se recuerda en localStorage)
✅ **Compatible** con todas las versiones (Original/Modular/Agno)

### Uso en la Interfaz Web

1. Abre http://localhost:8000
2. En el header, verás "Fuente: [dropdown]"
3. Selecciona el archivo deseado
4. El gráfico se actualizará automáticamente

### Uso desde API

```bash
# Obtener lista de archivos disponibles
curl http://localhost:8000/api/files

# Response:
{
  "files": [
    "registros.jsonl",
    "registros_agno.jsonl",
    "registros_turno_dia.jsonl"
  ]
}

# Obtener eventos de un archivo específico
curl "http://localhost:8000/api/events?file=registros_agno.jsonl&limit=100"
```

### Ejemplo con JavaScript

```javascript
// Obtener archivos disponibles
const res = await fetch('/api/files');
const data = await res.json();
console.log(data.files); // ['registros.jsonl', ...]

// Cargar eventos de un archivo específico
const events = await fetch('/api/events?file=registros_agno.jsonl&limit=500');
const eventsData = await events.json();
console.log(eventsData.events);
```

---

## 📊 Reportes Automáticos

### Descripción
El sistema genera reportes automáticos cada 12 horas (6:30 AM y 6:30 PM) con estadísticas detalladas del período.

### Horarios Configurados

| Hora | Descripción | Turno |
|------|-------------|-------|
| **6:30 AM** | Reporte de turno noche (18:30-6:30) | NOCHE |
| **6:30 PM** | Reporte de turno día (6:30-18:30) | DÍA |

### Contenido del Reporte

Cada reporte incluye:

#### 📈 Distribución de Estados
- NORMAL, ALERTA, ALARMA (cantidad y porcentaje)

#### ⚡ Métricas de Velocidad
- Promedio (mm/hr)
- Máxima (mm/hr)
- Percentil 95 de |velocidad|
- Percentil 99 de |velocidad|

#### 📏 Métricas de Desplazamiento
- Mínimo (mm)
- Máximo (mm)
- Rango total (mm)

#### 🚨 Eventos Destacados
- Top 20 eventos de ALERTA y ALARMA
- Timestamp, velocidad, desplazamiento, análisis LLM

### Formatos Generados

1. **JSON** (programático)
   - `reports/reporte_auto_YYYYMMDD_HHMMSS.json`

2. **Markdown** (legible)
   - `reports/reporte_auto_YYYYMMDD_HHMMSS.md`

### Ejemplo de Reporte (Markdown)

```markdown
# 📊 Reporte Automático - Vigilante Geotécnico

**Generado**: 2025-10-28T18:30:00
**Turno**: DÍA (12h)
**Período**: 2025-10-28 06:30:00 a 2025-10-28 18:30:00
**Total eventos**: 360

## 📈 Distribución de Estados

- **NORMAL**: 320 (88.9%)
- **ALERTA**: 35 (9.7%)
- **ALARMA**: 5 (1.4%)

## ⚡ Métricas de Velocidad

- **Promedio**: 0.523 mm/hr
- **Máxima**: 4.210 mm/hr
- **P95 (|vel|)**: 2.150 mm/hr
- **P99 (|vel|)**: 3.890 mm/hr

## 📏 Métricas de Desplazamiento

- **Mínimo**: 10.250 mm
- **Máximo**: 15.380 mm
- **Rango**: 5.130 mm

## 🚨 Eventos Destacados (ALERTA/ALARMA)

### 1. 2025-10-28 14:35:00 - **ALARMA**
- **Velocidad**: 4.210 mm/hr
- **Desplazamiento**: 15.380 mm
- **Análisis**: Velocidad sostenida por encima de 3 mm/hr con acumulado 12h > 15mm...
```

### API para Reportes

#### Generar reporte bajo demanda

```bash
# Reporte de últimas 12 horas (default)
curl "http://localhost:8000/api/reports/generate"

# Reporte de últimas 24 horas
curl "http://localhost:8000/api/reports/generate?hours=24"

# Reporte de archivo específico
curl "http://localhost:8000/api/reports/generate?hours=12&file=registros_agno.jsonl"
```

#### Listar reportes generados

```bash
curl "http://localhost:8000/api/reports/list"

# Response:
{
  "reports": [
    {
      "file": "reporte_auto_20251028_183000.json",
      "created": "2025-10-28T18:30:00"
    },
    {
      "file": "reporte_auto_20251028_063000.json",
      "created": "2025-10-28T06:30:00"
    }
  ]
}
```

#### Obtener reporte específico

```bash
curl "http://localhost:8000/api/reports/reporte_auto_20251028_183000.json"
```

### Personalizar Horarios

Edita `backend_app.py`:

```python
# Cambiar a 8:00 AM y 8:00 PM
scheduler.add_job(
    save_scheduled_report,
    trigger=CronTrigger(hour=8, minute=0),  # 8:00 AM
    id="reporte_8am",
)

scheduler.add_job(
    save_scheduled_report,
    trigger=CronTrigger(hour=20, minute=0),  # 8:00 PM
    id="reporte_8pm",
)
```

---

## 🚀 Servidor Integrado

### Descripción
Script unificado para iniciar todo el sistema con un solo comando.

### Uso Básico

```bash
# Inicio simple
python start_server.py

# Con auto-reload (desarrollo)
python start_server.py --reload

# Puerto personalizado
python start_server.py --port 9000

# Sin abrir navegador
python start_server.py --no-browser
```

### Características Incluidas

Cuando ejecutas `start_server.py`, obtienes:

✅ Backend FastAPI (puerto 8000)
✅ Frontend web interactivo
✅ Selector de archivos JSONL
✅ Reportes automáticos (6:30 AM/PM)
✅ Agno AgentOS (si está instalado)
✅ Navegador abierto automáticamente
✅ Verificación de dependencias

### Output del Servidor

```
================================================================================
🏔️  VIGILANTE GEOTÉCNICO - Servidor Completo
================================================================================

📡 Iniciando servidor en puerto 8000...
🌐 Frontend: http://localhost:8000
📚 API Docs: http://localhost:8000/docs
🤖 Agno Agents: http://localhost:8000/agents
📊 Reportes: http://localhost:8000/api/reports/list

--------------------------------------------------------------------------------
⏰ Reportes automáticos: 6:30 AM y 6:30 PM
📁 Directorio de reportes: ./reports/
--------------------------------------------------------------------------------

🔄 Modo reload activado (auto-recarga en cambios)
🚀 Ejecutando: uvicorn backend_app:app --host 0.0.0.0 --port 8000 --reload

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     ✅ Scheduler iniciado - Reportes automáticos a las 6:30 AM y 6:30 PM
```

---

## 🌐 API REST Completa

### Endpoints Disponibles

#### 📊 Eventos

```http
GET /api/events
```

**Query params:**
- `limit` (int): Número máximo de eventos (default: 200)
- `file` (str): Archivo JSONL específico (default: registros.jsonl)

**Response:**
```json
{
  "events": [
    {
      "time": "2025-10-28 14:35:00",
      "disp_mm": 15.38,
      "cum_disp_mm_total": 15.38,
      "vel_mm_hr": 4.21,
      "state": "ALARMA",
      "rationale": "Velocidad sostenida...",
      "llm_level": "ALARMA"
    }
  ]
}
```

#### 📁 Archivos

```http
GET /api/files
```

**Response:**
```json
{
  "files": [
    "registros.jsonl",
    "registros_agno.jsonl"
  ]
}
```

#### 📊 Generar Reporte

```http
GET /api/reports/generate
```

**Query params:**
- `hours` (float): Horas hacia atrás (default: 12.0)
- `file` (str): Archivo JSONL específico

**Response:**
```json
{
  "ok": true,
  "generated_at": "2025-10-28T18:30:00",
  "turno": "DÍA",
  "period": {
    "start": "2025-10-28 06:30:00",
    "end": "2025-10-28 18:30:00",
    "hours": 12,
    "n_events": 360
  },
  "summary": {
    "states": {"NORMAL": 320, "ALERTA": 35, "ALARMA": 5},
    "total_events": 360,
    "normal_pct": 88.9,
    "alerta_pct": 9.7,
    "alarma_pct": 1.4
  },
  "metrics": {
    "velocity": {
      "mean_mm_hr": 0.523,
      "max_mm_hr": 4.210,
      "p95_abs_mm_hr": 2.150,
      "p99_abs_mm_hr": 3.890
    },
    "displacement": {
      "min_mm": 10.250,
      "max_mm": 15.380,
      "range_mm": 5.130
    }
  },
  "highlights": [...]
}
```

#### 📋 Listar Reportes

```http
GET /api/reports/list
```

**Response:**
```json
{
  "reports": [
    {
      "file": "reporte_auto_20251028_183000.json",
      "created": "2025-10-28T18:30:00"
    }
  ]
}
```

#### 📄 Obtener Reporte

```http
GET /api/reports/{filename}
```

**Response:** JSON del reporte completo

---

## 🎨 Mejoras en la Interfaz Web

### Selector de Archivos
- Dropdown estilizado con tema dark/light
- Actualización automática sin reload
- Persistencia en localStorage

### Controles de Zoom
- Zoom In (+)
- Zoom Out (−)
- Reset Zoom (⌂)
- Fit to Data (⚡)

### Modos de Tema
- Dark mode (default)
- Light mode (toggle con botón)
- Persistencia de preferencia

### Responsive Design
- Desktop (>1024px)
- Tablet (768-1024px)
- Mobile (480-768px)
- Small mobile (<480px)

---

## 📦 Instalación de Dependencias

```bash
pip install -r requirements.txt
```

**Nueva dependencia agregada:**
- `APScheduler` - Para reportes automáticos programados

---

## 🔧 Configuración Avanzada

### Variables de Entorno

Crea un archivo `.env`:

```bash
# API Key de DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxx

# Configuración de reportes (opcional)
REPORTS_DIR=reports
REPORT_HOURS=12

# Configuración de scheduler (opcional)
REPORT_HOUR_AM=6
REPORT_MINUTE_AM=30
REPORT_HOUR_PM=18
REPORT_MINUTE_PM=30
```

---

## 📖 Ejemplos Completos

### Flujo Completo de Uso

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar API key
echo "DEEPSEEK_API_KEY=sk-xxxxx" > .env

# 3. Ejecutar análisis y generar datos
python agente_geotecnico.py --csv disp_example.csv --log-jsonl registros.jsonl

# 4. Iniciar servidor
python start_server.py --reload

# 5. Abrir navegador en http://localhost:8000
#    - Seleccionar archivo JSONL
#    - Ver gráficos interactivos
#    - Esperar reportes automáticos (6:30 AM/PM)

# 6. Generar reporte manual
curl "http://localhost:8000/api/reports/generate?hours=24"

# 7. Listar reportes
curl "http://localhost:8000/api/reports/list"
```

### Integración con Python

```python
import requests

# Generar reporte
response = requests.get("http://localhost:8000/api/reports/generate", params={
    "hours": 12,
    "file": "registros.jsonl"
})

report = response.json()

if report["ok"]:
    print(f"Turno: {report['turno']}")
    print(f"Eventos totales: {report['period']['n_events']}")
    print(f"Alarmas: {report['summary']['states']['ALARMA']}")
    print(f"Velocidad máxima: {report['metrics']['velocity']['max_mm_hr']} mm/hr")
```

---

## 🆘 Troubleshooting

### El scheduler no inicia

```bash
# Verificar que APScheduler esté instalado
pip install APScheduler

# Ver logs del servidor
python start_server.py --reload
# Buscar: "✅ Scheduler iniciado"
```

### No se generan reportes

```bash
# Verificar permisos del directorio
mkdir -p reports
chmod 755 reports

# Generar reporte manual para probar
curl "http://localhost:8000/api/reports/generate"
```

### Selector de archivos vacío

```bash
# Verificar que existan archivos .jsonl
ls *.jsonl

# Si no hay archivos, generar uno:
python agente_geotecnico.py --csv disp_example.csv --log-jsonl registros.jsonl --dry-run
```

---

## 📝 Notas Finales

- Los reportes se guardan en `./reports/` (se crea automáticamente)
- Los reportes antiguos **no se eliminan automáticamente** (limpieza manual)
- El scheduler **NO** ejecuta reportes al inicio, solo en horarios configurados
- Para testing, usa el endpoint `/api/reports/generate` manualmente

---

**Última actualización**: 2025-10-28
**Versión**: 1.1.0
