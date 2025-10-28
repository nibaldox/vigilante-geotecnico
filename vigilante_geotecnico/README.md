# 📦 Vigilante Geotécnico - Paquete Modular

Sistema modular de monitoreo inteligente para deformaciones geotécnicas con IA.

---

## 📖 Tabla de Contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Uso Básico](#uso-básico)
- [Módulos](#módulos)
- [API Reference](#api-reference)
- [Ejemplos Avanzados](#ejemplos-avanzados)
- [Testing](#testing)
- [Contribución](#contribución)

---

## 🎯 Descripción

Este paquete contiene la refactorización modular del sistema **Vigilante Geotécnico**, diseñado para:

- **Analizar datos geotécnicos** de radares de interferometría en tiempo real
- **Detectar deformaciones** del terreno con alta precisión
- **Generar alertas automáticas** basadas en reglas fijas y adaptativas
- **Integrar IA (DeepSeek)** para análisis avanzado y toma de decisiones

### ✨ Características Principales

- 🏗️ **Arquitectura modular**: 7 módulos independientes y reutilizables
- 📊 **Análisis robusto**: Umbrales adaptativos, EMAs, Bandas de Bollinger
- 🤖 **IA integrada**: Análisis con DeepSeek para validación y recomendaciones
- 📈 **Visualización**: Salida en formato rich/plain/json
- 🔧 **Configurable**: CLI completa con múltiples parámetros
- 📝 **Documentado**: Docstrings completos con ejemplos

---

## 🏗️ Arquitectura

```
vigilante_geotecnico/
│
├── core/               # 🎯 Núcleo
│   ├── models.py       # Dataclasses (Thresholds, FixedRules)
│   └── constants.py    # Constantes y prompts del sistema
│
├── data/               # 📊 Datos
│   ├── loaders.py      # Carga de CSV con metadata
│   └── preprocessing.py # Preprocesamiento de series temporales
│
├── analysis/           # 📈 Análisis
│   ├── thresholds.py   # Umbrales adaptativos y sliding window
│   ├── indicators.py   # EMAs, detección de eventos
│   └── window.py       # Análisis de ventanas temporales
│
├── llm/                # 🤖 IA
│   ├── client.py       # Cliente DeepSeek con reintentos
│   ├── prompts.py      # Construcción de prompts
│   └── validation.py   # Validación de respuestas LLM
│
├── output/             # 🖥️ Salida
│   ├── console.py      # Renderizado rich/plain/json
│   └── formatters.py   # Utilidades de formato
│
├── simulation/         # ⚙️ Simulación
│   └── runner.py       # Orquestación principal
│
└── cli/                # 🔧 CLI
    └── parser.py       # Parser de argumentos
```

### 🔄 Flujo de Datos

```
CSV → loaders → preprocessing → analysis → LLM → output
                                    ↓
                            simulation.runner
                                    ↓
                            (console/json)
```

---

## 📥 Instalación

### Opción 1: Desarrollo Local

```bash
# Clonar el repositorio
cd vigilante-geotecnico

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Instalar el paquete en modo desarrollo
pip install -e .
```

### Opción 2: Instalación desde Fuente

```bash
pip install git+https://github.com/tu-usuario/vigilante-geotecnico.git
```

### Opción 3: Instalación desde PyPI (próximamente)

```bash
pip install vigilante-geotecnico
```

---

## 🚀 Uso Básico

### 1. Desde Línea de Comandos

```bash
# Simulación completa con LLM
python -m vigilante_geotecnico.main \
  --csv disp_example.csv \
  --start-at "2025-09-01 00:00" \
  --emit-every-min 60 \
  --llm-every 1 \
  --log-jsonl registros.jsonl

# Modo dry-run (sin LLM)
python -m vigilante_geotecnico.main \
  --csv disp_example.csv \
  --dry-run
```

### 2. Como Módulo Python

```python
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.analysis import compute_thresholds_from_baseline, ema

# Cargar datos
df = load_csv_with_custom_header("disp_example.csv")
_, _, s_smooth, vel_mm_hr, _ = preprocess_series(df)

# Calcular umbrales
thr = compute_thresholds_from_baseline(vel_mm_hr.abs())
print(f"ALERTA: {thr.alerta:.3f} mm/hr | ALARMA: {thr.alarma:.3f} mm/hr")

# Calcular EMA
ema_1h = ema(s_smooth, span=30)
```

### 3. Usando el Wrapper

```bash
# Compatible con el script original
python agente_geotecnico_modular.py --csv disp_example.csv --dry-run
```

---

## 📚 Módulos

### 🎯 `core` - Núcleo del Sistema

Define los modelos de datos y constantes globales.

**Componentes principales:**
- `Thresholds`: Dataclass para umbrales de alerta/alarma
- `FixedRules`: Reglas fijas de detección
- `SYSTEM_PROMPT`: Prompt del sistema para el LLM

**Ejemplo:**
```python
from vigilante_geotecnico.core.models import Thresholds, FixedRules

thr = Thresholds(alerta=1.0, alarma=3.0)
rules = FixedRules(
    v_alert=1.0,
    v_alarm=3.0,
    d_alert=5.0,
    v_alarm_with_d1=1.5,
    v_alarm_with_d2=2.0
)
```

---

### 📊 `data` - Carga y Preprocesamiento

Manejo de archivos CSV y preprocesamiento de series temporales.

**Funciones principales:**

#### `load_csv_with_custom_header(csv_path: str) -> pd.DataFrame`
Carga CSV de ARCSAR con metadata y devuelve DataFrame limpio.

```python
from vigilante_geotecnico.data import load_csv_with_custom_header

df = load_csv_with_custom_header("disp_example.csv")
# Resultado: DataFrame con columnas ['time', 'disp_mm']
```

#### `preprocess_series(df: pd.DataFrame, resample_rule: str) -> Tuple`
Preprocesa series temporales y calcula velocidad/aceleración.

```python
from vigilante_geotecnico.data import preprocess_series

s, s_same, s_raw, vel_mm_hr, acc_mm_hr2 = preprocess_series(df)
# vel_mm_hr: Velocidad en mm/hr
# acc_mm_hr2: Aceleración en mm/hr²
```

---

### 📈 `analysis` - Análisis Geotécnico

Cálculo de umbrales, indicadores técnicos y análisis de ventanas.

**Funciones principales:**

#### `compute_thresholds_from_baseline(vel_abs: pd.Series, baseline_fraction: float) -> Thresholds`
Calcula umbrales robustos usando MAD y percentiles.

```python
from vigilante_geotecnico.analysis import compute_thresholds_from_baseline

thr = compute_thresholds_from_baseline(vel_mm_hr.abs(), baseline_fraction=0.2)
print(f"Umbrales: ALERTA={thr.alerta:.3f} | ALARMA={thr.alarma:.3f}")
```

#### `compute_thresholds_sliding(vel_abs, end_time, window_hours) -> Optional[Thresholds]`
Umbrales adaptativos en ventana deslizante.

```python
from vigilante_geotecnico.analysis import compute_thresholds_sliding

thr_sliding = compute_thresholds_sliding(
    vel_abs=vel_mm_hr.abs(),
    end_time=pd.Timestamp("2025-09-01 12:00"),
    window_hours=12.0
)
```

#### `ema(series: pd.Series, span: int) -> pd.Series`
Media móvil exponencial.

```python
from vigilante_geotecnico.analysis import ema

ema_1h = ema(s_smooth, span=30)   # EMA 1 hora
ema_3h = ema(s_smooth, span=90)   # EMA 3 horas
ema_12h = ema(s_smooth, span=360) # EMA 12 horas
```

#### `detect_events(vel_mm_hr, s_smooth, thr) -> pd.DataFrame`
Detecta eventos de alerta/alarma basados en umbrales.

```python
from vigilante_geotecnico.analysis import detect_events

events = detect_events(vel_mm_hr, s_smooth, thr)
# Resultado: DataFrame con columnas ['inicio', 'fin', 'nivel', 'vel_max_mm_hr', ...]
```

#### `summarize_window(...) -> Dict`
Resume métricas en una ventana temporal (función compleja con muchos parámetros).

---

### 🤖 `llm` - Integración con IA

Cliente para DeepSeek, construcción de prompts y validación.

**Funciones principales:**

#### `call_deepseek(api_key, prompt, ...) -> str`
Llama a la API de DeepSeek con reintentos automáticos.

```python
from vigilante_geotecnico.llm import call_deepseek
import os

response = call_deepseek(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    prompt="Analiza estos datos geotécnicos...",
    retries=3,
    retry_backoff=2.0
)
```

#### `build_prompt(snapshot: Dict, just_len: int) -> str`
Construye el prompt para el LLM con contexto completo.

```python
from vigilante_geotecnico.llm import build_prompt

prompt = build_prompt(snapshot, just_len=600)
```

#### `validate_justificacion_and_refs(llm_obj, snapshot, just_len) -> Tuple[bool, List[str]]`
Valida la respuesta del LLM (longitud, métricas, tendencias).

```python
from vigilante_geotecnico.llm import validate_justificacion_and_refs

ok, warnings = validate_justificacion_and_refs(llm_json, snapshot, 600)
if not ok:
    print(f"Advertencias: {warnings}")
```

---

### 🖥️ `output` - Formateo y Presentación

Renderizado de resultados en múltiples formatos.

**Funciones principales:**

#### `print_structured_console(snapshot, llm_content, ...) -> None`
Renderiza salida en formato rich/plain/json.

```python
from vigilante_geotecnico.output import print_structured_console

print_structured_console(
    snapshot=snapshot,
    llm_content=llm_response,
    llm_json=parsed_json,
    disagreement=False,
    console_format="rich",  # o "plain" o "json"
    llm_error=None
)
```

**Formatos soportados:**
- `rich`: Tablas coloreadas con Panel y Rich (por defecto)
- `plain`: Texto simple sin formato
- `json`: Salida JSON estructurada

---

### ⚙️ `simulation` - Orquestación

Loop principal de simulación con emisión programada.

**Función principal:**

#### `run_simulation(...) -> None`
Ejecuta la simulación completa (función con 18+ parámetros).

```python
from vigilante_geotecnico.simulation import run_simulation

run_simulation(
    csv_path="disp_example.csv",
    resample_rule="2T",
    step_points=60,
    lookback_min=12,
    accum_rate_hours=24.0,
    accum_window_threshold_mm=1.0,
    baseline_fraction=0.2,
    sleep_seconds=0.05,
    llm_every=1,
    dry_run=False,
    base_url=None,
    model=None,
    log_jsonl="registros.jsonl",
    only_disagreements=False,
    start_at="2025-09-01 00:00",
    v_alert=1.0,
    v_alarm=3.0,
    d_alert=5.0,
    v_alarm_with_d1=1.5,
    v_alarm_with_d2=2.0,
    summary_json="resumen.json",
    summary_top_k=10,
    emit_every_min=60.0,
    just_length=600
)
```

---

### 🔧 `cli` - Interfaz CLI

Parser de argumentos de línea de comandos.

**Función principal:**

#### `parse_args() -> argparse.Namespace`
Parsea todos los argumentos CLI disponibles.

```python
from vigilante_geotecnico.cli import parse_args

args = parse_args()
print(f"CSV: {args.csv}")
print(f"Dry-run: {args.dry_run}")
```

---

## 📖 API Reference

### Parámetros Comunes

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `csv_path` | `str` | - | Ruta al archivo CSV de entrada |
| `resample_rule` | `str` | `"2T"` | Regla de resampleo pandas (ej: "2T" = 2 minutos) |
| `baseline_fraction` | `float` | `0.2` | Fracción inicial para baseline de umbrales |
| `dry_run` | `bool` | `False` | Si True, no llama al LLM |
| `log_jsonl` | `str` | `None` | Ruta para logging JSON Lines |
| `v_alert` | `float` | `1.0` | Umbral fijo de velocidad alerta (mm/hr) |
| `v_alarm` | `float` | `3.0` | Umbral fijo de velocidad alarma (mm/hr) |
| `d_alert` | `float` | `5.0` | Umbral fijo de deformación alerta (mm) |

### Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DEEPSEEK_API_KEY` | API key de DeepSeek | - |
| `DEEPSEEK_BASE_URL` | URL base de la API | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | Modelo a usar | `deepseek-chat` |
| `CONSOLE_FORMAT` | Formato de salida | `rich` |
| `BOLLINGER_K` | Factor K para Bollinger | `2.0` |
| `LLM_TIMEOUT_CONNECT` | Timeout conexión (s) | `10` |
| `LLM_TIMEOUT_READ` | Timeout lectura (s) | `60` |
| `LLM_RETRIES` | Número de reintentos | `3` |
| `LLM_RETRY_BACKOFF` | Backoff exponencial | `2.0` |

---

## 💡 Ejemplos Avanzados

### Ejemplo 1: Pipeline Completo

```python
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.analysis import (
    compute_thresholds_from_baseline,
    compute_thresholds_sliding,
    ema,
    summarize_window
)
from vigilante_geotecnico.core.models import FixedRules
import pandas as pd

# 1. Cargar datos
df = load_csv_with_custom_header("disp_example.csv")
_, _, s_smooth, vel_mm_hr, _ = preprocess_series(df)

# 2. Calcular umbrales
thr_base = compute_thresholds_from_baseline(vel_mm_hr.abs())
print(f"Umbrales baseline: ALERTA={thr_base.alerta:.3f} | ALARMA={thr_base.alarma:.3f}")

# 3. Calcular EMAs
x_idx = s_smooth.index
ema_1h = ema(s_smooth, span=30)
ema_3h = ema(s_smooth, span=90)
ema_12h = ema(s_smooth, span=360)

# 4. Analizar punto específico
i = len(x_idx) // 2  # Punto medio
thr_sliding = compute_thresholds_sliding(
    vel_mm_hr.abs(),
    end_time=x_idx[i],
    window_hours=12.0
)

# 5. Resumen de ventana
snapshot = summarize_window(
    x_idx=x_idx,
    s_smooth=s_smooth,
    vel_mm_hr=vel_mm_hr,
    cum_total=s_smooth,
    ema12=ema_1h,
    ema48=ema_3h,
    ema96=ema_12h,
    thr=thr_sliding or thr_base,
    thr_source="sliding_12h" if thr_sliding else "baseline",
    i=i,
    lookback_points=360,
    accum_period_hours=24.0,
    accum_window_threshold_mm=1.0,
    bb_k=2.0,
    fixed=FixedRules(1.0, 3.0, 5.0, 1.5, 2.0),
    history=None
)

print(f"Estado actual: {snapshot['current']['state']}")
print(f"Velocidad: {snapshot['current']['vel_mm_hr']:.3f} mm/hr")
print(f"Deformación: {snapshot['current']['disp_mm']:.3f} mm")
```

### Ejemplo 2: Análisis Batch de Múltiples Archivos

```python
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
from vigilante_geotecnico.analysis import compute_thresholds_from_baseline
from pathlib import Path
import pandas as pd

# Analizar múltiples archivos
results = []
for csv_file in Path("data/").glob("*.csv"):
    df = load_csv_with_custom_header(str(csv_file))
    _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df)
    thr = compute_thresholds_from_baseline(vel_mm_hr.abs())

    results.append({
        "file": csv_file.name,
        "n_points": len(df),
        "thr_alerta": thr.alerta,
        "thr_alarma": thr.alarma,
        "vel_max": vel_mm_hr.abs().max(),
        "disp_total": s_smooth.iloc[-1] - s_smooth.iloc[0]
    })

# Crear DataFrame resumen
summary_df = pd.DataFrame(results)
print(summary_df)
```

### Ejemplo 3: Integración con LLM

```python
from vigilante_geotecnico.llm import build_prompt, call_deepseek
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
import os

# Preparar datos
df = load_csv_with_custom_header("disp_example.csv")
_, _, s_smooth, vel_mm_hr, _ = preprocess_series(df)

# Crear snapshot simplificado
snapshot = {
    "current": {
        "vel_mm_hr": float(vel_mm_hr.iloc[-1]),
        "disp_mm": float(s_smooth.iloc[-1])
    },
    "thresholds": {
        "alerta_mm_hr": 1.0,
        "alarma_mm_hr": 3.0
    }
}

# Construir prompt y llamar LLM
prompt = build_prompt(snapshot, just_len=400)
response = call_deepseek(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    prompt=prompt,
    retries=3
)

print(f"Respuesta LLM: {response}")
```

---

## 🧪 Testing

### Estructura de Tests

```bash
vigilante_geotecnico/
└── tests/
    ├── test_data.py          # Tests para módulo data
    ├── test_analysis.py      # Tests para módulo analysis
    ├── test_llm.py           # Tests para módulo llm
    └── test_integration.py   # Tests de integración
```

### Ejecutar Tests

```bash
# Todos los tests
pytest vigilante_geotecnico/tests/

# Test específico
pytest vigilante_geotecnico/tests/test_data.py

# Con cobertura
pytest --cov=vigilante_geotecnico vigilante_geotecnico/tests/

# Con verbose
pytest -v vigilante_geotecnico/tests/
```

### Ejemplo de Test

```python
import pytest
from vigilante_geotecnico.data import load_csv_with_custom_header, preprocess_series
import pandas as pd

def test_load_csv():
    """Test de carga de CSV."""
    df = load_csv_with_custom_header("tests/fixtures/test_data.csv")
    assert "time" in df.columns
    assert "disp_mm" in df.columns
    assert len(df) > 0

def test_preprocess_series():
    """Test de preprocesamiento."""
    df = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=100, freq='2T'),
        'disp_mm': range(100)
    })
    s, s_same, s_raw, vel, acc = preprocess_series(df)
    assert len(vel) == len(df)
    assert vel.dtype == 'float64'
```

---

## 🤝 Contribución

### Guidelines

1. **Fork** el repositorio
2. Crea una **rama** para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -am 'Add: nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un **Pull Request**

### Estándares de Código

- **PEP 8**: Seguir convenciones de Python
- **Type hints**: Obligatorios para funciones públicas
- **Docstrings**: Formato Google con ejemplos
- **Tests**: Cobertura mínima 80%
- **Linting**: flake8, ruff, mypy

```bash
# Verificar código
flake8 vigilante_geotecnico/
ruff check vigilante_geotecnico/
mypy vigilante_geotecnico/

# Auto-formateo
black vigilante_geotecnico/
isort vigilante_geotecnico/
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` en el directorio raíz.

---

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/vigilante-geotecnico/issues)
- **Documentación**: [docs.vigilante-geotecnico.com](https://docs.vigilante-geotecnico.com)
- **Email**: soporte@vigilante-geotecnico.com

---

## 🙏 Agradecimientos

- **Agno** por el framework de agentes
- **DeepSeek** por el modelo de lenguaje
- **FastAPI** por el framework web
- **Rich** por la visualización en terminal

---

<div align="center">

**Mantén tus estructuras seguras con Vigilante Geotécnico!** 🏔️

[⬆ Volver arriba](#-vigilante-geotécnico---paquete-modular)

</div>
