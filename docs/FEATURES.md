# 🎯 Nuevas Funcionalidades - Vigilante Geotécnico

## 📋 Tabla de Contenidos

- [Selector de Archivos](#-selector-de-archivos)
- [Reportes Automáticos](#-reportes-automáticos)
- [Interfaz de Agentes Agno](#-interfaz-de-agentes-agno)
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

## 🤖 Interfaz de Agentes Agno

### Descripción
Página dedicada para interactuar con los agentes multi-nivel (Vigilante, Supervisor, Reportador) mediante chat en tiempo real, con inspección de herramientas y conversaciones.

### Características

✅ **Chat interactivo** con cada agente (Vigilante/Supervisor/Reportador)
✅ **Integración con AgentOS UI** nativa de Agno Framework
✅ **Inspección en tiempo real** de tool calls y decisiones
✅ **Persistencia** de conversaciones en SQLite
✅ **Navegación fluida** entre Dashboard y Agentes
✅ **Tema sincronizado** (dark/light) con el resto del sistema

### Acceso a la Interfaz

1. **Desde el Dashboard**: Clic en "🤖 Agentes" en el header
2. **URL directa**: http://localhost:8000/agents.html
3. **Agno UI nativa**: http://localhost:8000/agents (iframe integrado)

### Arquitectura de Agentes

| Agente | Rol | Horizonte Temporal | Señales Clave |
|--------|-----|-------------------|---------------|
| **👁️ Vigilante** | Monitoreo de corto plazo | 1-3h | `\|vel\|`, EMAs 1h/3h/12h, IV, Bollinger |
| **🔍 Supervisor** | Validación de medio plazo | 12-48h | EMAs 12h/24h/48h, contexto histórico |
| **📊 Reportador** | Síntesis y comunicación | Variable | Agregación de métricas, eventos destacados |

### Uso con Chat Interactivo

#### Ejemplo 1: Consultar al Vigilante

```
Usuario → Vigilante:
"Analiza el punto 5000 del archivo disp_example.csv usando tool_analyze_window.
¿Qué nivel recomiendas?"

Vigilante → [Ejecuta tool_analyze_window]
{
  "level": "ALERTA",
  "confidence": 0.87,
  "primary_trigger": "vel > umbral_alerta (1.8 > 1.2)",
  "metrics": {
    "vel_mm_hr": 1.8,
    "disp_mm": 12.5,
    "ema_1h": 12.3,
    "iv": 0.52
  },
  "justification": "La velocidad de 1.8 mm/hr supera el umbral adaptativo..."
}
```

#### Ejemplo 2: Validación con Supervisor

```
Usuario → Supervisor:
"El Vigilante emitió ALERTA para el punto 5000.
Valida con contexto de 12h usando tool_get_recent_events."

Supervisor → [Ejecuta tool_get_recent_events(hours=12)]
{
  "validation": "DEGRADADO",
  "final_level": "NORMAL",
  "vigilante_level": "ALERTA",
  "confidence": 0.82,
  "rationale": "Aunque el Vigilante detectó vel=1.8 mm/hr en ventana 1h,
  el análisis de contexto 12-48h muestra que las EMAs 24h y 48h permanecen estables..."
}
```

#### Ejemplo 3: Solicitar Reporte

```
Usuario → Reportador:
"Genera un reporte horario consolidando los últimos análisis del Vigilante y Supervisor."

Reportador → [Sintetiza información]
=== VIGILANTE GEOTÉCNICO - Reporte Horario ===
Período: 2025-10-29 13:00 a 2025-10-29 14:00
Estado: NORMAL

Métricas:
- Velocidad: 0.8 mm/hr (promedio), 1.2 mm/hr (P95)
- Desplazamiento: 10.5 a 11.2 mm (rango)
- Tendencia: ESTABLE

Análisis:
Vigilante detectó operación normal. Supervisor confirma estabilidad en ventana 12-48h.
No se requieren acciones inmediatas.
```

### Herramientas (Tools) Disponibles

Los agentes tienen acceso a las siguientes herramientas:

1. **`tool_load_geotechnical_data`** - Carga y preprocesa datos CSV
2. **`tool_compute_thresholds`** - Calcula umbrales adaptativos (MAD + percentiles)
3. **`tool_analyze_window`** - Analiza ventana temporal específica
4. **`tool_get_recent_events`** - Recupera eventos desde JSONL histórico
5. **`tool_send_alert`** (futuro) - Envío de alertas automáticas

### Selector de Agentes

La interfaz permite cambiar el contexto del agente activo:

- **Todos los agentes**: Vista general del equipo
- **Vigilante**: Análisis de corto plazo (1-3h)
- **Supervisor**: Validación de medio plazo (12-48h)
- **Reportador**: Generación de informes

### Persistencia y Memoria

- **Base de datos**: `vigilante_geotecnico.db` (SQLite)
- **Historial**: Todas las conversaciones se almacenan con contexto
- **add_history_to_context=True**: Los agentes recuerdan interacciones previas

### Ventajas de AgentOS UI

✅ **UI profesional lista para producción**
✅ **Sin desarrollo frontend adicional**
✅ **Inspección detallada de tool calls**
✅ **Streaming de respuestas en tiempo real**
✅ **Gestión de sesiones y usuarios**
✅ **Privacidad garantizada** (todo local, no envía datos externos)

### Integración con Dashboard

La navegación entre páginas está sincronizada:

| Página | URL | Descripción |
|--------|-----|-------------|
| **Dashboard** | http://localhost:8000 | Gráficos, estadísticas, eventos LLM |
| **Agentes** | http://localhost:8000/agents.html | Chat con agentes, inspección de tools |

Ambas páginas comparten:
- ✅ Tema dark/light sincronizado
- ✅ Estilos consistentes
- ✅ Navegación fluida con botones en header

### API de Agentes (Futuro)

En futuras versiones se habilitarán endpoints REST para interactuar con agentes programáticamente:

```bash
# Consultar a un agente específico
curl -X POST "http://localhost:8000/api/agents/vigilante/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analiza el último evento", "context": {...}}'

# Obtener historial de conversaciones
curl "http://localhost:8000/api/agents/vigilante/history?limit=10"

# Ejecutar análisis automático
curl -X POST "http://localhost:8000/api/agents/analyze" \
  -d '{"csv_path": "disp_example.csv", "point_idx": 5000}'
```

### Troubleshooting

#### La interfaz de agentes no carga

```bash
# Verificar que Agno esté instalado
pip install agno

# Verificar que agno_team.py exista
ls agno_team.py

# Revisar logs del servidor
python start_server.py --reload
# Buscar: "Agno AgentOS mounted at /agents"
```

#### Error "No se pudo montar agno_team"

Esto es normal si Agno no está instalado. La aplicación seguirá funcionando sin la interfaz de agentes.

```bash
# Instalar Agno
pip install agno

# Reiniciar servidor
python start_server.py --reload
```

#### Los agentes no responden

```bash
# Verificar API key de DeepSeek en .env
cat .env | grep DEEPSEEK_API_KEY

# Verificar conectividad
curl https://api.deepseek.com/v1/models

# Revisar base de datos
sqlite3 vigilante_geotecnico.db "SELECT * FROM messages LIMIT 5;"
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
