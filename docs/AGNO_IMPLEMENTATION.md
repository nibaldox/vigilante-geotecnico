# Implementación con Agno Framework

## 📚 Tabla de Contenidos

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Agentes](#agentes)
- [Herramientas (Tools)](#herramientas-tools)
- [Instalación](#instalación)
- [Uso](#uso)
- [Ejemplos](#ejemplos)
- [Comparación con Implementación Original](#comparación-con-implementación-original)
- [Ventajas de Agno](#ventajas-de-agno)

---

## Introducción

Esta implementación aprovecha el **framework Agno** para crear un sistema multi-agente de monitoreo geotécnico de alto rendimiento. Agno es un framework moderno para construcción de agentes con:

- **529× más rápido** que Langgraph
- **2μs** de creación por agente
- **3.75 KiB** de memoria por agente
- Soporte nativo para tools, memoria y multi-agentes
- Runtime FastAPI integrado (AgentOS)

### ¿Por qué Agno?

| Característica | Implementación Original | Con Agno Framework |
|----------------|-------------------------|-------------------|
| **Arquitectura** | Monolítica | Multi-agente distribuido |
| **Performance** | API calls secuenciales | Agentes paralelos (2μs) |
| **Escalabilidad** | Limitada | Altamente escalable |
| **Memoria** | Sin contexto persistente | SQLite con historial |
| **Tools** | Funciones ad-hoc | Tools integrados nativamente |
| **UI** | Solo CLI/web custom | AgentOS UI out-of-the-box |
| **Colaboración** | Análisis único | 3 agentes especializados |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOS Runtime                          │
│  (FastAPI + SQLite + UI Web)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│Vigilante │    │Supervisor│    │Reportador│
│(1-3h)    │───▶│(12-48h)  │───▶│(Informes)│
└──────────┘    └──────────┘    └──────────┘
      │               │               │
      └───────────────┴───────────────┘
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
    ┌──────────────┐    ┌──────────────┐
    │ Tools (5)    │    │ vigilante_   │
    │              │    │ geotecnico/  │
    │ - analyze    │    │ (módulos)    │
    │ - thresholds │    │              │
    │ - events     │    │ - data       │
    │ - load_data  │    │ - analysis   │
    │ - window     │    │ - llm        │
    └──────────────┘    └──────────────┘
```

### Flujo de Trabajo

1. **Datos** → vigilante_geotecnico carga y preprocesa CSV
2. **Vigilante** → Analiza ventana (1-3h), clasifica NORMAL/ALERTA/ALARMA
3. **Supervisor** → Valida con contexto (12-48h), confirma/degrada
4. **Reportador** → Sintetiza en reportes para operadores
5. **Persistencia** → SQLite guarda historial completo de conversaciones

---

## Agentes

### 1. 👁️ Vigilante (Análisis de Corto Plazo)

**Responsabilidad:** Monitoreo en tiempo real (1-3h)

**Señales clave:**
- Velocidad absoluta `|vel|` (mm/hr)
- Desplazamiento acumulado 12h
- EMAs: 1h, 3h, 12h
- Bandas de Bollinger (volatilidad)
- Índice de Velocidad (IV) - persistencia

**Reglas de decisión:**

| Nivel | Condiciones |
|-------|-------------|
| **ALARMA** | `vel > 3.0 mm/hr` + `disp > 5mm` ó `vel > 2.0 mm/hr` + `acum_12h > 10mm` ó Divergencia EMAs fuerte ó `IV > 0.7` |
| **ALERTA** | `vel > 1.0 mm/hr` ó Aceleración detectable ó EMAs separación moderada ó Banda Bollinger rota |
| **NORMAL** | Todas las métricas dentro de rangos normales |

**Tools disponibles:**
- `tool_analyze_window` - Analiza ventana temporal
- `tool_get_recent_events` - Eventos recientes
- `tool_compute_thresholds` - Umbrales adaptativos

**Output JSON:**
```json
{
  "level": "ALARMA",
  "confidence": 0.92,
  "primary_trigger": "vel > 3.5 mm/hr + acum_12h > 12mm",
  "metrics": {
    "vel_mm_hr": 3.5,
    "disp_mm": 15.2,
    "ema_1h": 14.8,
    "iv": 0.73
  },
  "justification": "Velocidad sostenida por encima de 3 mm/hr en última hora..."
}
```

---

### 2. 🔍 Supervisor (Validación de Medio Plazo)

**Responsabilidad:** Corroborar decisiones con contexto 12-48h

**Señales clave:**
- EMAs: 12h, 24h, 48h
- Consistencia de `|vel|` en ventanas 12h
- Acumulado 12h vs 24h
- IV sostenido > 6h
- Historial de eventos (registros.jsonl)

**Criterios de validación:**

| Acción | Condiciones |
|--------|-------------|
| **CONFIRMAR** | EMAs convergentes al alza + `IV > 0.6` sostenido + Escalada histórica |
| **DEGRADAR** | EMAs 24h/48h estables + Evento aislado + `IV < 0.4` |
| **ESCALAR** | Tendencia no detectada por Vigilante pero evidente en 12-48h |

**Tools disponibles:**
- `tool_analyze_window` - Contexto extendido
- `tool_get_recent_events` (hours=12+) - Historial
- `tool_load_geotechnical_data` - Series completas

**Output JSON:**
```json
{
  "validation": "CONFIRMADO",
  "final_level": "ALARMA",
  "vigilante_level": "ALARMA",
  "confidence": 0.88,
  "rationale": "EMAs 12h/24h/48h muestran convergencia alcista sostenida...",
  "context": {
    "ema_12h": 14.5,
    "ema_24h": 13.2,
    "ema_48h": 11.8,
    "iv_6h_avg": 0.65
  }
}
```

---

### 3. 📊 Reportador (Generación de Informes)

**Responsabilidad:** Síntesis y comunicación

**Tipos de reporte:**

1. **Horario** (cada hora)
   - Resumen ejecutivo última hora
   - Estado actual
   - Métricas clave
   - Acciones recomendadas

2. **Turno** (12h día/noche)
   - Estadísticas período completo
   - Eventos destacados
   - Evolución tendencias
   - Proyección próximas 12h

**Tools disponibles:**
- `tool_get_recent_events` - Datos históricos
- `tool_load_geotechnical_data` - Series para análisis

**Formato reporte horario:**
```
=== VIGILANTE GEOTÉCNICO - Reporte Horario ===
Período: 2025-10-28 10:00 a 2025-10-28 11:00
Estado: ALERTA

Métricas:
- Velocidad: 1.8 mm/hr (promedio), 2.3 mm/hr (P95)
- Desplazamiento: 10.5 a 12.2 mm (rango)
- Tendencia: ASCENDENTE

Análisis:
Vigilante detectó aceleración en última hora (1.8→2.3 mm/hr).
Supervisor confirma con EMAs 12h ascendentes. Persistencia moderada (IV=0.52).

Acciones: Monitorear próxima hora. Revisar causas externas si persiste.
```

---

## Herramientas (Tools)

Agno permite que los agentes usen tools (funciones Python) de forma nativa. Cada tool está decorado para que Agno lo detecte automáticamente.

### 1. `tool_load_geotechnical_data`

**Propósito:** Cargar y preprocesar datos geotécnicos desde CSV

**Parámetros:**
- `csv_path` (str): Ruta al archivo CSV
- `start_at` (Optional[str]): Timestamp de inicio

**Retorna:**
```python
{
  "status": "success",
  "n_points": 15000,
  "time_range": {"start": "2025-01-01 00:00", "end": "2025-01-31 23:59"},
  "series": {
    "displacement": [...],
    "velocity": [...],
    "ema_1h": [...],
    "ema_3h": [...],
    "ema_12h": [...],
    "ema_24h": [...],
    "ema_48h": [...]
  },
  "stats": {
    "disp_min": 0.0,
    "disp_max": 50.2,
    "vel_mean": 0.5,
    "vel_p95": 2.1,
    "vel_p99": 3.5
  }
}
```

### 2. `tool_compute_thresholds`

**Propósito:** Calcular umbrales adaptativos MAD + percentiles

**Parámetros:**
- `csv_path` (str): Ruta al CSV
- `baseline_fraction` (float): Fracción del baseline (default: 0.2)

**Retorna:**
```python
{
  "status": "success",
  "thresholds": {
    "alerta": 1.2,
    "alarma": 2.8
  },
  "method": "baseline_mad_percentile",
  "baseline_fraction": 0.2
}
```

### 3. `tool_analyze_window`

**Propósito:** Analizar ventana temporal específica

**Parámetros:**
- `csv_path` (str): Ruta al CSV
- `window_end_idx` (int): Índice final de ventana
- `lookback_minutes` (int): Minutos hacia atrás (default: 60)
- `baseline_fraction` (float): Fracción baseline (default: 0.2)

**Retorna:**
```python
{
  "status": "success",
  "snapshot": {
    "current": {
      "time": "2025-01-15 14:30",
      "state": "ALERTA",
      "vel_mm_hr": 1.8,
      "disp_mm": 12.5,
      "cum_disp_mm_total": 35.2
    },
    "window": {
      "start": "2025-01-15 13:30",
      "end": "2025-01-15 14:30",
      "n_points": 30,
      "vel_mean": 1.5,
      "disp_delta": 1.7
    },
    "indicators": {
      "ema_1h": 12.3,
      "ema_3h": 11.8,
      "ema_12h": 10.5,
      "bollinger_upper": 13.5,
      "bollinger_lower": 9.5,
      "iv": 0.52
    },
    "decision": {
      "source": "adaptive",
      "rule": "vel_above_alert_threshold",
      "thresholds": {"alerta": 1.2, "alarma": 2.8}
    }
  }
}
```

### 4. `tool_get_recent_events`

**Propósito:** Recuperar eventos recientes desde log JSONL

**Parámetros:**
- `jsonl_path` (str): Ruta al JSONL (default: "registros.jsonl")
- `hours` (float): Horas hacia atrás (default: 1.0)

**Retorna:**
```python
{
  "status": "success",
  "window": {
    "start": "2025-01-15 13:30",
    "end": "2025-01-15 14:30",
    "hours": 1.0,
    "n_events": 15
  },
  "events": [
    {
      "time": "2025-01-15 14:30",
      "state": "ALERTA",
      "vel_mm_hr": 1.8,
      "disp_mm": 12.5,
      "llm_level": "ALERTA"
    },
    ...
  ],
  "stats": {
    "levels": {"NORMAL": 8, "ALERTA": 7, "ALARMA": 0},
    "vel_mean": 1.2,
    "vel_p95_abs": 2.1,
    "disp_min": 10.5,
    "disp_max": 12.5
  }
}
```

---

## Instalación

### 1. Requisitos previos

```bash
# Python 3.9+
python --version

# Instalar dependencias base del proyecto
pip install -r requirements.txt
```

### 2. Instalar Agno Framework

```bash
pip install agno
```

### 3. Configurar API Keys

Crear archivo `.env`:

```bash
# DeepSeek API (usado por agentes Agno)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# Opcional: URLs personalizadas
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Umbrales geotécnicos (opcionales)
V_ALERT=1.0
V_ALARM=3.0
D_ALERT=5.0
```

### 4. Verificar instalación

```bash
python agente_geotecnico_agno.py --help
```

---

## Uso

### 1. 🌐 Servir AgentOS UI (Recomendado)

La forma más interactiva de usar los agentes:

```bash
python agente_geotecnico_agno.py serve --reload
```

Abre en navegador: **http://localhost:7277**

La UI permite:
- Chat directo con cada agente
- Ver historial de conversaciones
- Inspeccionar tool calls en tiempo real
- Cambiar entre agentes

**Ejemplo de chat:**

```
Usuario → Vigilante:
"Analiza el punto 5000 del archivo disp_example.csv. ¿Qué nivel recomiendas?"

Vigilante → [Usa tool_analyze_window]
"Análisis completo... ALERTA. Velocidad 1.8 mm/hr > umbral 1.2 mm/hr..."

Usuario → Supervisor:
"Valida el veredicto del Vigilante usando contexto 12h"

Supervisor → [Usa tool_get_recent_events]
"Validación: CONFIRMADO. EMAs 12h/24h muestran tendencia ascendente..."
```

---

### 2. 📊 Análisis Completo desde CLI

Analizar archivo CSV completo con intervalos:

```bash
python agente_geotecnico_agno.py analyze \
  --csv disp_example.csv \
  --output registros_agno.jsonl \
  --interval 60
```

**Parámetros:**
- `--csv`: Archivo CSV de entrada (requerido)
- `--output`: JSONL de salida para eventos (default: registros.jsonl)
- `--interval`: Minutos entre análisis (default: 60)

**Output:**
```
================================================================================
VIGILANTE GEOTÉCNICO - Análisis con Agno Framework
================================================================================

📂 CSV: disp_example.csv
📝 Log: registros_agno.jsonl
⏱️  Intervalo: 60 minutos

⚙️  Cargando y preprocesando datos...
✅ 15000 puntos cargados | Rango: 2025-01-01 00:00 a 2025-01-31 23:59

────────────────────────────────────────────────────────────────────────────────
🕐 Análisis en t=2025-01-01 01:00 (punto 30/15000)
────────────────────────────────────────────────────────────────────────────────

👁️  Vigilante analizando...
✅ Vigilante: {"level": "NORMAL", "confidence": 0.95, "metrics": {...}}

🔍 Supervisor validando...
✅ Supervisor: {"validation": "CONFIRMADO", "final_level": "NORMAL", ...}

[... continúa cada 60 minutos ...]

================================================================================
📊 GENERANDO REPORTE FINAL
================================================================================

=== VIGILANTE GEOTÉCNICO - Reporte de Análisis Completo ===
Período: 2025-01-01 00:00 a 2025-01-31 23:59
Total análisis: 744

Distribución de niveles:
- NORMAL: 680 (91.4%)
- ALERTA: 52 (7.0%)
- ALARMA: 12 (1.6%)

Eventos destacados:
- 2025-01-15 14:30: ALARMA (vel=3.8 mm/hr, acum_12h=15mm)
- 2025-01-22 08:15: ALARMA (vel=4.2 mm/hr, IV=0.82)
[...]

✅ Reporte guardado en: reporte_agno_20251028_143025.txt
```

---

### 3. 📝 Reporte Horario

Generar reporte de la última hora desde logs:

```bash
python agente_geotecnico_agno.py hourly --jsonl registros_agno.jsonl
```

**Output:**
```
📊 Generando reporte horario...

=== VIGILANTE GEOTÉCNICO - Reporte Horario ===
Período: 2025-10-28 13:30 a 2025-10-28 14:30
Estado: ALERTA

Métricas:
- Velocidad: 1.8 mm/hr (promedio), 2.3 mm/hr (P95)
- Desplazamiento: 10.5 a 12.2 mm (rango)
- Tendencia: ASCENDENTE

Análisis:
Vigilante detectó aceleración en última hora. Supervisor confirma
con EMAs 12h ascendentes. Persistencia moderada (IV=0.52).

Acciones: Monitorear próxima hora. Revisar causas externas si persiste.
```

---

### 4. 📋 Reporte de Turno (12h)

Generar reporte consolidado de turno (día/noche):

```bash
python agente_geotecnico_agno.py shift \
  --jsonl registros_agno.jsonl \
  --hours 12
```

**Output:**
```
📊 Generando reporte de turno (12h)...

=== VIGILANTE GEOTÉCNICO - Reporte de Turno ===
Turno: DÍA | 2025-10-28 06:00 a 2025-10-28 18:00

Resumen:
- Total eventos: 360
- Distribución: 320 NORMAL, 35 ALERTA, 5 ALARMA
- Máxima velocidad: 4.2 mm/hr a las 14:35
- Desplazamiento total: 8.5 mm

Eventos Destacados:
1. 14:35 - ALARMA: Velocidad máxima 4.2 mm/hr, acum_12h=18mm
2. 14:50 - ALARMA: Persistencia IV=0.85, EMAs divergentes
3. 16:20 - ALERTA: Recuperación parcial, vel=1.5 mm/hr
4. 17:45 - NORMAL: Vuelta a estabilidad

Tendencias (EMAs):
- 12h: Ascendente (10.5 → 13.2 mm)
- 24h: Estable-ascendente (9.8 → 11.5 mm)
- 48h: Estable (9.5 mm)

Proyección:
Si tendencia actual persiste, esperar ALERTA sostenida próximas 6h.
Posible nueva ALARMA si vel > 3 mm/hr.

Recomendaciones:
- Intensificar monitoreo en próximo turno
- Verificar condiciones meteorológicas
- Revisar equipamiento de medición en zona crítica

✅ Reporte guardado en: reporte_turno_20251028_180005.txt
```

---

## Ejemplos

### Ejemplo 1: Chat Interactivo con Vigilante

```python
from agente_geotecnico_agno import vigilante

# Análisis directo
response = vigilante.run("""
Analiza el punto 5000 del archivo disp_example.csv usando tool_analyze_window.
Necesito clasificación NORMAL/ALERTA/ALARMA con justificación.
""")

print(response.content)
```

**Output:**
```json
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
  "justification": "La velocidad de 1.8 mm/hr supera el umbral adaptativo de alerta (1.2 mm/hr). Las EMAs 1h/3h/12h muestran separación moderada (12.3/11.8/10.5 mm), indicando aceleración reciente. El índice de velocidad (IV=0.52) sugiere persistencia moderada. Sin embargo, no se alcanzan condiciones de ALARMA (vel < 3.0 mm/hr). Recomiendo monitoreo continuo."
}
```

---

### Ejemplo 2: Validación con Supervisor

```python
from agente_geotecnico_agno import vigilante, supervisor

# 1. Vigilante analiza
vigilante_result = vigilante.run("Analiza punto 5000 de disp_example.csv")

# 2. Supervisor valida
supervisor_prompt = f"""
El Vigilante emitió:
{vigilante_result.content}

Valida este veredicto usando contexto 12-48h con tool_get_recent_events.
¿Confirmas, degradas o escalas?
"""

supervisor_result = supervisor.run(supervisor_prompt)
print(supervisor_result.content)
```

**Output:**
```json
{
  "validation": "DEGRADADO",
  "final_level": "NORMAL",
  "vigilante_level": "ALERTA",
  "confidence": 0.82,
  "rationale": "Aunque el Vigilante detectó vel=1.8 mm/hr en ventana 1h, el análisis de contexto 12-48h muestra que las EMAs 24h y 48h permanecen estables (11.2 y 10.8 mm respectivamente). El historial de últimas 12h indica solo 2 eventos ALERTA aislados sin persistencia (IV_6h=0.35). Este patrón sugiere variabilidad normal más que una tendencia preocupante. Recomiendo degradar a NORMAL con monitoreo.",
  "context": {
    "ema_12h": 11.8,
    "ema_24h": 11.2,
    "ema_48h": 10.8,
    "iv_6h_avg": 0.35
  }
}
```

---

### Ejemplo 3: Pipeline Completo

```python
from agente_geotecnico_agno import vigilante, supervisor, reportador

def analizar_completo(csv_path: str, punto: int):
    # 1. Vigilante
    v_result = vigilante.run(f"""
    Analiza punto {punto} de {csv_path} con tool_analyze_window.
    """)

    # 2. Supervisor
    s_result = supervisor.run(f"""
    Valida este análisis del Vigilante:
    {v_result.content}

    Usa tool_get_recent_events con hours=12.
    """)

    # 3. Reportador
    r_result = reportador.run(f"""
    Genera reporte horario consolidando:

    Vigilante: {v_result.content}
    Supervisor: {s_result.content}

    Usa formato de reporte horario.
    """)

    return {
        "vigilante": v_result.content,
        "supervisor": s_result.content,
        "reporte": r_result.content
    }

# Ejecutar
resultado = analizar_completo("disp_example.csv", 5000)
print(resultado["reporte"])
```

---

### Ejemplo 4: Análisis Batch con Tools Directos

```python
from agente_geotecnico_agno import (
    tool_load_geotechnical_data,
    tool_compute_thresholds,
    tool_analyze_window
)

# 1. Cargar datos
data = tool_load_geotechnical_data("disp_example.csv")
print(f"Puntos cargados: {data['n_points']}")
print(f"Rango: {data['time_range']}")

# 2. Calcular umbrales
thresholds = tool_compute_thresholds("disp_example.csv", baseline_fraction=0.2)
print(f"Umbrales: ALERTA={thresholds['thresholds']['alerta']:.2f}, "
      f"ALARMA={thresholds['thresholds']['alarma']:.2f}")

# 3. Analizar múltiples ventanas
puntos_criticos = [1000, 3000, 5000, 7000, 9000]

for punto in puntos_criticos:
    snapshot = tool_analyze_window(
        csv_path="disp_example.csv",
        window_end_idx=punto,
        lookback_minutes=60
    )

    if snapshot["status"] == "success":
        current = snapshot["snapshot"]["current"]
        print(f"\nPunto {punto}:")
        print(f"  Tiempo: {current['time']}")
        print(f"  Estado: {current['state']}")
        print(f"  Vel: {current['vel_mm_hr']:.2f} mm/hr")
        print(f"  Disp: {current['disp_mm']:.2f} mm")
```

**Output:**
```
Puntos cargados: 15000
Rango: {'start': '2025-01-01 00:00', 'end': '2025-01-31 23:59'}
Umbrales: ALERTA=1.18, ALARMA=2.73

Punto 1000:
  Tiempo: 2025-01-02 09:20
  Estado: NORMAL
  Vel: 0.45 mm/hr
  Disp: 5.20 mm

Punto 3000:
  Tiempo: 2025-01-07 18:40
  Estado: ALERTA
  Vel: 1.65 mm/hr
  Disp: 18.30 mm

Punto 5000:
  Tiempo: 2025-01-13 04:00
  Estado: ALERTA
  Vel: 1.80 mm/hr
  Disp: 32.10 mm

[...]
```

---

## Comparación con Implementación Original

| Aspecto | Original (`agente_geotecnico.py`) | Con Agno (`agente_geotecnico_agno.py`) |
|---------|-----------------------------------|----------------------------------------|
| **Arquitectura** | Monolítica (1349 líneas) | Multi-agente modular (800 líneas) |
| **Análisis** | Secuencial, un solo LLM call | 3 agentes especializados en paralelo |
| **Performance** | ~2-5s por análisis (DeepSeek API) | ~2μs creación agente + API paralela |
| **Memoria** | Sin contexto (stateless) | SQLite persistente con historial |
| **UI** | CLI + web custom (index.html) | AgentOS UI out-of-the-box |
| **Escalabilidad** | Limitada (loop secuencial) | Alta (agentes distribuibles) |
| **Tools** | Funciones ad-hoc | 5 tools nativos Agno |
| **Colaboración** | No (análisis único) | Sí (Vigilante→Supervisor→Reportador) |
| **Validación** | Solo reglas fijas/adaptativas | Doble validación (agentes) |
| **Reportes** | Resumen final básico | Reportes horarios + turnos |
| **Debug** | Logs + JSONL | AgentOS UI + tool calls visibles |

### Ventajas de Agno

✅ **Más rápido**: 529× vs Langgraph, creación de agentes en 2μs

✅ **Más memoria eficiente**: 3.75 KiB por agente

✅ **Colaboración**: 3 agentes especializados vs análisis único

✅ **Persistencia**: SQLite con historial completo de conversaciones

✅ **UI nativa**: AgentOS con interfaz web lista para producción

✅ **Tools integrados**: Detección automática, validación de parámetros

✅ **Escalable**: Agentes distribuibles, paralelización nativa

✅ **Mantenible**: Separación de responsabilidades (SOLID)

### Cuándo usar cada implementación

| Usa Original | Usa Agno |
|--------------|----------|
| Análisis batch simple | Sistema multi-agente complejo |
| No necesitas UI | Necesitas interfaz interactiva |
| Presupuesto limitado de API | Quieres validación multi-nivel |
| Script one-off | Sistema en producción |
| Análisis histórico | Monitoreo en tiempo real |

---

## Performance Benchmark

### Comparación de Tiempos (1000 análisis)

| Métrica | Original | Agno | Mejora |
|---------|----------|------|--------|
| **Creación agente** | N/A | 2μs | - |
| **Análisis por punto** | 2.5s | 2.5s* | - |
| **Validación** | No | 2.5s | - |
| **Reporte** | 0.1s | 2.5s | - |
| **Total (1000 pts)** | 2500s | 7500s* | - |
| **Memoria agentes** | N/A | 11.25 KiB | - |

*Nota: El tiempo de API (DeepSeek) es el mismo. La ventaja de Agno es en infraestructura, colaboración y escalabilidad, no en velocidad bruta de LLM calls.*

### Ventajas Reales de Performance

1. **Creación de agentes**: 2μs vs segundos en frameworks competidores
2. **Paralelización**: 3 agentes pueden analizar distintas ventanas en paralelo
3. **Memoria**: 3.75 KiB/agente permite miles de agentes concurrentes
4. **Caching**: SQLite reduce llamadas redundantes al LLM
5. **Streaming**: Agno soporta respuestas streaming para UX mejor

---

## Extensiones Futuras

### 1. Agentes Adicionales

```python
# Agente Predictor (Machine Learning)
predictor = Agent(
    name="Predictor",
    model=DeepSeek(id="deepseek-chat"),
    instructions="Predice próximas 6-24h usando modelos ARIMA/LSTM",
    tools=[tool_train_model, tool_forecast, tool_confidence_intervals]
)

# Agente Correlador (Factores Externos)
correlador = Agent(
    name="Correlador",
    instructions="Correlaciona con clima, sismicidad, mareas",
    tools=[tool_fetch_weather, tool_fetch_seismic, tool_correlate]
)
```

### 2. Workflows Avanzados

```python
from agno.workflow import Workflow

# Workflow con dependencias
workflow = Workflow(
    steps=[
        ("vigilante", vigilante, {"csv": "disp.csv"}),
        ("supervisor", supervisor, {"context": "${vigilante.output}"}),
        ("predictor", predictor, {"snapshot": "${supervisor.output}"}),
        ("reportador", reportador, {"inputs": ["${vigilante}", "${supervisor}", "${predictor}"]})
    ]
)

result = workflow.run()
```

### 3. Multi-Sitio

```python
# Monitorear múltiples sitios en paralelo
sitios = ["sitio_a.csv", "sitio_b.csv", "sitio_c.csv"]

teams = {
    sitio: AgentOS(agents=[
        create_vigilante_agent(db),
        create_supervisor_agent(db),
        create_reportador_agent(db)
    ])
    for sitio in sitios
}

# Análisis paralelo
results = await asyncio.gather(*[
    team.analyze(sitio) for sitio, team in teams.items()
])
```

### 4. Integración con Sistemas Externos

```python
# Tool para enviar alertas
def tool_send_alert(level: str, message: str, recipients: List[str]) -> Dict:
    """Envía alertas por email/SMS/Slack."""
    if level == "ALARMA":
        send_sms(recipients, message)
        send_slack("#geotecnia-alertas", message)
    elif level == "ALERTA":
        send_email(recipients, message)
    return {"status": "sent", "recipients": len(recipients)}

# Añadir a agentes
vigilante.tools.append(tool_send_alert)
```

---

## Referencias

- **Agno Framework**: https://docs.agno.com
- **Agno GitHub**: https://github.com/agno-agi/agno
- **DeepSeek API**: https://platform.deepseek.com
- **Vigilante Geotécnico (Original)**: `../agente_geotecnico.py`
- **Módulos Refactorizados**: `../vigilante_geotecnico/`

---

## Soporte

Para preguntas sobre:
- **Agno Framework**: Discord oficial de Agno
- **Vigilante Geotécnico**: Issues en GitHub del proyecto
- **DeepSeek API**: Documentación oficial de DeepSeek

---

**Última actualización**: 2025-10-28
**Versión Agno**: 0.1.0+
**Versión Python**: 3.9+
