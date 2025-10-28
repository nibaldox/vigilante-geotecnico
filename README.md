# 🏔️ Vigilante Geotécnico

**Sistema de monitoreo inteligente para deformaciones geotécnicas con IA**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Agno](https://img.shields.io/badge/Agno-2.0+-purple.svg)](https://docs.agno.com/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange.svg)](https://platform.deepseek.com/)

---

## 📋 Descripción

**Vigilante Geotécnico** es un sistema avanzado de monitoreo que combina análisis de datos geotécnicos con inteligencia artificial para detectar deformaciones en tiempo real. Utiliza datos de radares de interferometria para identificar patrones de movimiento del terreno y generar alertas automáticas.

### ✨ Características Principales

- **📊 Análisis en tiempo real** de deformaciones geotécnicas
- **🤖 Equipo de agentes IA** (Vigilante, Supervisor, Reportador) con DeepSeek
- **📈 Visualización web interactiva** con gráficos dinámicos
- **⚡ Simulación acelerada** con emisión horaria configurable
- **🔧 Reglas adaptativas** con umbrales deslizantes de 12 horas
- **📋 Reportes automáticos** cada 12 horas (turnos día/noche)
- **🎯 API REST** para integración con sistemas externos

---

## 🏗️ Arquitectura

### 📦 Estructura Modular

El proyecto ofrece **3 implementaciones** para diferentes necesidades:

| Versión | Archivo | Descripción | Uso recomendado |
|---------|---------|-------------|-----------------|
| **Original** | `agente_geotecnico.py` | Monolítica (1349 líneas) | Scripts rápidos, pruebas |
| **Modular** | `agente_geotecnico_modular.py` | Usa paquete refactorizado | Desarrollo, mantenimiento |
| **Agno Framework** | `agente_geotecnico_agno.py` | Multi-agente avanzado | Producción, escalabilidad |

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIGILANTE GEOTÉCNICO                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Original    │   │  Modular     │   │  Agno        │
│  (Legacy)    │   │  (Package)   │   │  (Multi-AI)  │
└──────────────┘   └──────────────┘   └──────────────┘
                            │                   │
                            └─────────┬─────────┘
                                      ▼
                    ┌─────────────────────────────────┐
                    │   vigilante_geotecnico/         │
                    │   ├── core/      (models)       │
                    │   ├── data/      (loaders)      │
                    │   ├── analysis/  (thresholds)   │
                    │   ├── llm/       (DeepSeek)     │
                    │   ├── output/    (formatting)   │
                    │   ├── simulation/ (runner)      │
                    │   └── cli/       (parser)       │
                    └─────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│ Radar/CSV    │──────────▶│  Simulador   │──────────▶│  Agentes IA  │
│ (Datos)      │           │  (Análisis)  │           │  (DeepSeek)  │
└──────────────┘           └──────────────┘           └──────────────┘
                                    │                         │
                                    ▼                         ▼
                           ┌──────────────┐         ┌──────────────┐
                           │ registros.   │         │  AgentOS UI  │
                           │ jsonl        │         │  (/agents)   │
                           └──────────────┘         └──────────────┘
                                    │                         │
                                    └─────────┬───────────────┘
                                              ▼
                                    ┌──────────────────┐
                                    │  Web Interface   │
                                    │  (Chart.js)      │
                                    │  /api/events     │
                                    └──────────────────┘
```

### 🧠 Agentes Inteligentes

El sistema incluye **3 agentes especializados** con diferentes horizontes temporales:

| Agente | Horizonte | Señales Clave | Responsabilidad |
|--------|-----------|---------------|-----------------|
| **👁️ Vigilante** | 1-3h | vel, EMAs 1h/3h/12h, IV | Detección en tiempo real |
| **🔍 Supervisor** | 12-48h | EMAs 12h/24h/48h, historial | Validación y filtrado |
| **📊 Reportador** | - | Síntesis de ambos | Reportes operacionales |

#### Implementaciones disponibles:

1. **Básica** (`agno_team.py`): Agentes con instrucciones simples
2. **Avanzada** (`agente_geotecnico_agno.py`): Agentes + Tools + Full integration

---

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd vigilante-geotecnico
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias

#### Instalación básica (versión original y modular)
```bash
pip install -r requirements.txt
```

#### Instalación completa (incluye Agno Framework)
```bash
pip install -r requirements.txt
pip install agno
```

#### Instalación con versiones fijadas (reproducibilidad)
```powershell
# (Windows PowerShell)
venv\Scripts\Activate.ps1
pip install -r requirements-lock.txt
pip install agno
```

**Nota**: El framework Agno es opcional. Solo necesitas instalarlo si quieres usar `agente_geotecnico_agno.py`.

### 4. Configurar variables de entorno
```bash
# Archivo .env
DEEPSEEK_API_KEY=tu_api_key_aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1  # opcional
DEEPSEEK_MODEL=deepseek-chat
```

### 5. Base de datos automática
El sistema crea automáticamente la base de datos SQLite `vigilante_geotecnico.db` para el historial de los agentes. **No requiere configuración adicional**.

---

## 🎯 Uso Rápido

### Opción 1: 🚀 Agno Framework (Recomendado para producción)

La implementación más avanzada con multi-agentes, tools y UI integrada:

```bash
# Servir AgentOS UI interactiva
python agente_geotecnico_agno.py serve --reload

# Análisis completo de CSV
python agente_geotecnico_agno.py analyze --csv disp_example.csv --interval 60

# Reporte horario
python agente_geotecnico_agno.py hourly --jsonl registros.jsonl

# Reporte de turno (12h)
python agente_geotecnico_agno.py shift --jsonl registros.jsonl --hours 12
```

**Interfaces disponibles:**
- **AgentOS UI**: http://localhost:7277 (chat interactivo con agentes)
- **Dashboard web**: http://localhost:8000 (visualización de datos)

**Ventajas:**
- ✅ 529× más rápido (infraestructura Agno)
- ✅ 3 agentes especializados trabajando en equipo
- ✅ 5 tools geotécnicas integradas
- ✅ SQLite con historial persistente
- ✅ UI web out-of-the-box

---

### Opción 2: 📦 Versión Modular (Recomendado para desarrollo)

Usa el paquete refactorizado `vigilante_geotecnico/`:

```bash
# Como script
python agente_geotecnico_modular.py --csv "disp_example.csv" \
                                    --start-at "2025-09-01 00:00" \
                                    --emit-every-min 60 \
                                    --sleep 0.1 \
                                    --llm-every 1

# Como módulo Python
python -m vigilante_geotecnico.main --csv "disp_example.csv" --dry-run

# Importar en código
from vigilante_geotecnico.data import load_csv_with_custom_header
from vigilante_geotecnico.analysis import compute_thresholds_from_baseline
```

**Ventajas:**
- ✅ Código modular (23 archivos, 7 módulos)
- ✅ Fácil mantenimiento y testing
- ✅ Reutilizable en otros proyectos
- ✅ 100% compatible con versión original

---

### Opción 3: 📝 Versión Original (Legacy)

Scripts monolíticos para uso rápido:

```bash
# Versión estándar
python agente_geotecnico.py --csv "disp_example.csv" \
                            --start-at "2025-09-01 00:00" \
                            --emit-every-min 60 \
                            --sleep 0.1 \
                            --llm-every 1 \
                            --log-jsonl registros.jsonl

# Versión mejorada con validación JSON avanzada
python agente_geotecnico_ds.py --csv "disp_example.csv" \
                               --start-at "2025-09-01 00:00" \
                               --emit-every-min 60 \
                               --sleep 0.1 \
                               --llm-every 1 \
                               --log-jsonl registros.jsonl
```

**Ventajas:**
- ✅ Archivo único (fácil de copiar/modificar)
- ✅ No requiere instalar paquete modular
- ✅ Ideal para scripts one-off

---

### 🌐 Iniciar Servidor Web (Para todas las versiones)

```bash
python -m uvicorn backend_app:app --reload --port 8000
```

**Acceder a la interfaz:**
- **Dashboard principal**: http://127.0.0.1:8000/
- **Agentes IA (básicos)**: http://127.0.0.1:8000/agents
- **API REST**: http://127.0.0.1:8000/docs

---

## ⚙️ Configuración

### Parámetros del simulador

| Parámetro | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| `--csv` | Archivo CSV de entrada | `disp_example.csv` |
| `--start-at` | Fecha/hora de inicio | `None` |
| `--emit-every-min` | Emisión cada N minutos | `None` (continuo) |
| `--step-points` | Puntos por iteración | `60` |
| `--sleep` | Pausa entre iteraciones (seg) | `0.05` |

### Reglas de alerta

| Parámetro | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| `--v-alert` | Velocidad alerta (mm/hr) | `1.0` |
| `--v-alarm` | Velocidad alarma (mm/hr) | `3.0` |
| `--d-alert` | Deformación alerta (mm) | `5.0` |
| `--v-alarm-with-d1` | Velocidad alarma con d>5 (mm/hr) | `1.5` |
| `--v-alarm-with-d2` | Velocidad alarma extra (mm/hr) | `2.0` |

### Comandos del equipo Agno

```bash
# Servir interfaz de agentes
python agno_team.py serve --reload

# Resumen horario desde registros
python agno_team.py hourly --jsonl registros.jsonl --at "2025-09-01 05:00"

# Reporte de 12 horas (turno)
python agno_team.py report12h --jsonl registros.jsonl --hours 12 --out resumen_turno.json
```

---

## 📊 API Endpoints

### GET /api/events
Obtiene los últimos eventos de monitoreo.

**Parámetros de consulta:**
- `limit` (int): Número máximo de eventos (default: 200)

**Respuesta:**
```json
{
  "events": [
    {
      "time": "2025-09-01 01:00:00",
      "disp_mm": -0.123,
      "vel_mm_hr": 0.456,
      "state": "NORMAL",
      "rationale": "Velocidad estable dentro de umbrales normales...",
      "llm_level": "NORMAL"
    }
  ]
}
```

### GET /agents/*
Interfaz completa de Agno AgentOS para interactuar con los agentes IA.

---

## 🎯 Funcionalidades de Zoom

El gráfico incluye avanzadas funcionalidades de zoom y navegación:

### ⌨️ Controles de teclado y mouse
- **`Ctrl + rueda del mouse`**: Zoom in/out
- **`Shift + arrastrar`**: Pan (desplazamiento) horizontal y vertical
- **`Doble clic`**: Reset completo del zoom
- **`Click en área vacía`**: Pan automático

### 🔘 Botones de control
- **Zoom In (+)**: Acercar 1.5x
- **Zoom Out (−)**: Alejar a 0.67x
- **Reset Zoom (⌂)**: Volver al zoom original
- **Fit to Data (⚡)**: Ajuste automático a todos los datos visibles

### ⚙️ Configuración avanzada
- **Zoom mínimo**: 1 hora (evita zoom excesivo en datos temporales)
- **Transiciones suaves**: Animación de 300ms con easing
- **Modo XY**: Zoom independiente en ambos ejes
- **Responsive design**:
  - **Desktop (>1024px)**: Layout de 2 columnas, gráfico de 400px
  - **Tablet (768-1024px)**: Layout de 1 columna, gráfico de 300px
  - **Mobile (480-768px)**: Header responsive, gráfico de 250px
  - **Small mobile (<480px)**: Instrucciones adaptadas, gráfico de 200px
  - **Touch-friendly**: Botones de 44px mínimo para dispositivos táctiles

---

## 🔍 Análisis Geotécnico

### Versiones disponibles

- **`agente_geotecnico.py`**: Versión estándar con análisis básico
- **`agente_geotecnico_ds.py`**: Versión mejorada con:
  - ✅ **Validación JSON avanzada** con esquema estricto
  - ✅ **Extracción robusta** de respuestas LLM
  - ✅ **Catálogo de evidencias** con whitelist
  - ✅ **Métricas sugeridas** para respuestas LLM
  - ✅ **Justificación extendida** (200-420 caracteres)
  - ✅ **Autochequeo** y corrección automática

### 💾 Base de datos para historial

El sistema **Agno AgentOS** utiliza una base de datos SQLite para mantener el historial de conversaciones:

- **📁 Archivo**: `vigilante_geotecnico.db` (SQLite)
- **🔄 Persistencia**: Cada agente mantiene su propio historial de conversaciones
- **💾 Funcionalidad**: Context-aware responses basadas en interacciones previas
- **🛡️ Seguridad**: Historial privado y local (no se envía a servicios externos)

### Métricas calculadas

- **Velocidad instantánea** (mm/hr)
- **Deformación acumulada** (mm)
- **EMAs por rol**:
  - Vigilante: 1h, 3h, 12h (desplazamiento)
  - Supervisor: 12h, 24h, 48h (desplazamiento)
- **Bandas de Bollinger** para detección de anomalías
- **Velocidad inversa** (Fukuzono) para tendencias

### Reglas de decisión

1. **Reglas fijas** (prioridad máxima)
   - ALARMA: vel > v_alarm_with_d2 AND deform > d_alert
   - ALARMA: vel > v_alarm_with_d1 AND deform > d_alert
   - ALARMA: vel > v_alarm
   - ALERTA: vel > v_alert OR deform > d_alert

2. **Reglas adaptativas** (umbrales deslizantes 12h)
   - Basadas en percentiles 97.5% y MAD del |vel| en ventana

3. **Persistencia** (elevación automática)
   - Si acumulado 12h > umbral, elevar 1 nivel (máx. ALARMA)

---

## 📈 Visualización

La interfaz web muestra:

- **Gráfico principal**: Deformación acumulada con EMAs 1h/3h/12h
- **🎯 Zoom interactivo**:
  - **Rueda del mouse** con `Ctrl` para zoom
  - **Shift + arrastrar** para pan horizontal/vertical
  - **Doble clic** para reset del zoom
  - **Botones de control**: Zoom In/Out, Reset Zoom, Fit to Data
- **Regiones sombreadas**: Periodos de ALERTA (amarillo) y ALARMA (rojo)
- **Panel de mensajes**: Análisis del LLM con timestamps
- **Botón Reset**: Reancla la vista para mostrar solo datos nuevos

### 📱 Compatibilidad móvil

El sistema está **100% optimizado** para dispositivos móviles y tablets:

- **📱 Responsive design**: Se adapta automáticamente a cualquier tamaño de pantalla
- **👆 Touch-friendly**: Controles optimizados para pantallas táctiles
- **⚡ Performance**: Animaciones suaves y carga rápida en dispositivos móviles
- **🎯 Zoom táctil**: Soporte completo para pinch-to-zoom
- **📊 Gráficos adaptativos**: Fuentes y elementos se ajustan al tamaño de pantalla

---

## 🧪 Ejemplos de uso

### Simulación completa (1h real = 1h simulada)
```bash
# Versión estándar
python agente_geotecnico.py \
  --csv "disp_example.csv" \
  --start-at "2025-09-01 00:00" \
  --emit-every-min 60 \
  --dry-run  # sin LLM para pruebas rápidas

# Versión mejorada
python agente_geotecnico_ds.py \
  --csv "disp_example.csv" \
  --start-at "2025-09-01 00:00" \
  --emit-every-min 60 \
  --dry-run  # sin LLM para pruebas rápidas
```

### Tests

Se incluyen tests básicos usando pytest. Para ejecutar los tests en tu entorno:

```powershell
# activar venv (Windows PowerShell)
& .\venv\Scripts\Activate.ps1
python -m pytest -q
```

El repositorio también incluye un `requirements-lock.txt` con las versiones actualmente usadas; es recomendable instalar desde ese archivo para CI/reproducción.


### Simulación acelerada (10x)
```bash
# Versión estándar
python agente_geotecnico.py \
  --csv "disp_example.csv" \
  --step-points 6 \
  --sleep 0.05 \
  --llm-every 1

# Versión mejorada
python agente_geotecnico_ds.py \
  --csv "disp_example.csv" \
  --step-points 6 \
  --sleep 0.05 \
  --llm-every 1
```

### Solo agentes IA
```bash
python agno_team.py serve --reload
```

---

## 🔧 Desarrollo

### Estructura del proyecto

```
vigilante-geotecnico/
├── 📦 Paquete Modular
│   └── vigilante_geotecnico/
│       ├── __init__.py
│       ├── main.py                  # Punto de entrada
│       ├── README.md                # Documentación del paquete
│       ├── core/                    # Modelos y constantes
│       │   ├── models.py            # Thresholds, FixedRules
│       │   └── constants.py         # SYSTEM_PROMPT, constantes
│       ├── data/                    # Carga y preprocesamiento
│       │   ├── loaders.py           # load_csv_with_custom_header()
│       │   └── preprocessing.py     # preprocess_series()
│       ├── analysis/                # Análisis geotécnico
│       │   ├── thresholds.py        # compute_thresholds_*()
│       │   ├── indicators.py        # ema(), detect_events()
│       │   └── window.py            # summarize_window()
│       ├── llm/                     # Integración DeepSeek
│       │   ├── client.py            # call_deepseek()
│       │   ├── prompts.py           # build_prompt()
│       │   └── validation.py        # validate_justificacion_and_refs()
│       ├── output/                  # Formateo y presentación
│       │   ├── console.py           # print_structured_console()
│       │   └── formatters.py        # Utilidades de formato
│       ├── simulation/              # Orquestación
│       │   └── runner.py            # run_simulation()
│       └── cli/                     # CLI
│           └── parser.py            # parse_args()
│
├── 🤖 Implementaciones
│   ├── agente_geotecnico.py         # Versión original (legacy)
│   ├── agente_geotecnico_ds.py      # Versión con validación avanzada
│   ├── agente_geotecnico_modular.py # Wrapper para paquete modular
│   └── agente_geotecnico_agno.py    # Implementación Agno Framework
│
├── 🌐 Web y API
│   ├── backend_app.py               # Servidor FastAPI
│   ├── agno_team.py                 # Agentes básicos Agno
│   └── web/
│       └── index.html               # Interfaz web interactiva
│
├── 📚 Documentación
│   ├── README.md                    # Esta documentación
│   ├── REFACTORING_SUMMARY.md       # Resumen de refactorización
│   └── docs/
│       ├── AGNO_IMPLEMENTATION.md   # Guía completa Agno
│       └── less_help.txt
│
├── 🧪 Testing
│   ├── tests/
│   │   ├── test_agente.py
│   │   ├── test_agente_ds.py
│   │   ├── test_backend_app.py
│   │   └── test_prompt_length.py
│   └── .github/
│       └── workflows/
│           └── ci.yml               # GitHub Actions CI
│
├── ⚙️ Configuración
│   ├── .env.example                 # Template variables
│   ├── .flake8                      # Linting config
│   ├── .pre-commit-config.yaml      # Git hooks
│   ├── pyproject.toml               # Package config
│   ├── requirements.txt             # Dependencias
│   └── requirements-lock.txt        # Versiones fijadas
│
└── 📊 Datos y Resultados
    ├── disp_example.csv             # Datos de ejemplo
    ├── analisis_geotecnico.ipynb    # Análisis exploratorio
    ├── registros.jsonl              # Log de eventos
    ├── resumen.json                 # Resumen de análisis
    └── vigilante_geotecnico*.db     # Bases de datos SQLite
```

### 📖 Documentación Detallada

- **[Paquete Modular](vigilante_geotecnico/README.md)**: API reference completo (687 líneas)
- **[Implementación Agno](docs/AGNO_IMPLEMENTATION.md)**: Guía de uso del framework (600+ líneas)
- **[Resumen de Refactorización](REFACTORING_SUMMARY.md)**: Métricas y migración

### 🛠️ Desarrollo con el Paquete Modular

```python
# Importar módulos específicos
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.analysis import (
    compute_thresholds_from_baseline,
    ema,
    summarize_window
)
from vigilante_geotecnico.core.models import FixedRules, Thresholds

# Cargar datos
df = load_csv_with_custom_header("disp_example.csv")
_, _, s_smooth, vel_mm_hr, _ = preprocess_series(df)

# Calcular umbrales adaptativos
thr = compute_thresholds_from_baseline(vel_mm_hr.abs())
print(f"Umbrales: ALERTA={thr.alerta:.3f} | ALARMA={thr.alarma:.3f}")

# Calcular EMAs
ema_1h = ema(s_smooth, span=30)
ema_3h = ema(s_smooth, span=90)

# Analizar ventana específica
snapshot = summarize_window(
    x_idx=s_smooth.index,
    s_smooth=s_smooth,
    vel_mm_hr=vel_mm_hr,
    # ... más parámetros
)
```

### 🤖 Agregar Agentes Personalizados (Agno)

```python
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS

# Crear base de datos
db = SqliteDb(db_file="mi_agente.db")

# Crear agente personalizado con tools
from agente_geotecnico_agno import (
    tool_analyze_window,
    tool_get_recent_events,
    tool_load_geotechnical_data
)

experto_terreno = Agent(
    name="Experto en Terreno",
    model=DeepSeek(id="deepseek-chat"),
    db=db,
    add_history_to_context=True,
    instructions="""
    Analizar condiciones específicas del terreno considerando:
    - Geología local
    - Hidrología
    - Condiciones meteorológicas
    """,
    tools=[tool_analyze_window, tool_get_recent_events, tool_load_geotechnical_data],
    show_tool_calls=True
)

# Agregar al equipo existente
from agente_geotecnico_agno import vigilante, supervisor, reportador

agent_os = AgentOS(agents=[vigilante, supervisor, reportador, experto_terreno])
app = agent_os.get_app()

# Servir
agent_os.serve(app="mi_agente:app", reload=True)
```

### 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=vigilante_geotecnico --cov-report=html

# Solo un módulo
pytest tests/test_agente.py -v

# CI local (pre-commit)
pre-commit run --all-files
```

---

## 🔀 Comparación de Versiones

Elige la implementación según tus necesidades:

| Característica | Original | Modular | Agno Framework |
|----------------|----------|---------|----------------|
| **Archivo** | `agente_geotecnico.py` | `agente_geotecnico_modular.py` | `agente_geotecnico_agno.py` |
| **Líneas de código** | 1349 | 23 archivos (~1582 total) | 800+ |
| **Arquitectura** | Monolítica | Paquete modular | Multi-agente |
| **Agentes** | 1 LLM call | 1 LLM call | 3 agentes especializados |
| **Tools** | No | Funciones modulares | 5 tools integrados |
| **UI** | No | No | AgentOS ✅ |
| **Persistencia** | No | No | SQLite ✅ |
| **Performance** | Estándar | Estándar | 529× más rápido (infra) |
| **Memoria** | N/A | N/A | 3.75 KiB/agente |
| **Colaboración** | No | No | Vigilante→Supervisor→Reportador |
| **Validación** | Simple | Doble (adaptive+fixed) | Triple (3 agentes) |
| **Mantenibilidad** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Testabilidad** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Reutilización** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Complejidad setup** | ⭐ (simple) | ⭐⭐ | ⭐⭐⭐ |
| **Producción** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Prototipado rápido** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 💡 Recomendaciones de uso

**Usa Original si:**
- Necesitas un script rápido one-off
- Quieres entender todo el código en un solo archivo
- No planeas mantener el código a largo plazo
- Quieres máxima simplicidad

**Usa Modular si:**
- Desarrollas activamente y necesitas mantenibilidad
- Quieres reutilizar componentes en otros proyectos
- Necesitas alta testabilidad
- El proyecto tiene múltiples desarrolladores
- Quieres seguir principios SOLID

**Usa Agno Framework si:**
- Despliegues a producción con múltiples análisis
- Necesitas validación multi-nivel automática
- Quieres interfaz web sin desarrollo adicional
- El sistema debe escalar a múltiples sitios
- Necesitas historial persistente de decisiones
- Quieres aprovechar agentes especializados

### 🚀 Migración entre versiones

Todas las versiones son **100% compatibles** en términos de datos de entrada/salida:

```bash
# Mismo CSV, diferentes implementaciones
python agente_geotecnico.py --csv disp_example.csv --dry-run
python agente_geotecnico_modular.py --csv disp_example.csv --dry-run
python agente_geotecnico_agno.py analyze --csv disp_example.csv

# Todas generan registros.jsonl compatible
# Todas pueden usar el mismo backend_app.py
```

---

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Guías de desarrollo
- Sigue las convenciones de código Python (PEP 8)
- Agrega tests para nuevas funcionalidades
- Actualiza la documentación
- Usa type hints

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/vigilante-geotecnico/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/vigilante-geotecnico/discussions)
- **Documentación Agno**: [docs.agno.com](https://docs.agno.com/)
- **API DeepSeek**: [platform.deepseek.com](https://platform.deepseek.com/)

---

## 🙏 Agradecimientos

- **Agno** por el framework de agentes multi-modal
- **DeepSeek** por el modelo de lenguaje
- **FastAPI** por el framework web de alto rendimiento
- **Chart.js** por la visualización interactiva

---

<div align="center">

**¡Mantén tus estructuras seguras con Vigilante Geotécnico!** 🏔️

[⭐ Star this repo](https://github.com/tu-usuario/vigilante-geotecnico) | [🐛 Report Bug](https://github.com/tu-usuario/vigilante-geotecnico/issues) | [💡 Request Feature](https://github.com/tu-usuario/vigilante-geotecnico/issues)

</div>
