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

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Radar         │──▶│   Simulador     │───▶│   Agentes IA    │
│   (Datos crudos)│    │   (Reglas + LLM)│    │   (DeepSeek)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   registros.    │    │   Agentes UI    │
                       │   jsonl         │    │   (/agents)     │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Interfaz Web  │    │   API Endpoints │
                       │   (Chart.js)    │    │   (/api/events) │
                       └─────────────────┘    └─────────────────┘
```

### 🧠 Agentes Inteligentes

1. **Vigilante** - Análisis de corto plazo (1-12h) con EMAs 1h/3h/12h
2. **Supervisor** - Validación y corroboración con contexto extendido (12-48h)
3. **Reportador** - Generación de mensajes horarios y reportes de turno

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
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Archivo .env
DEEPSEEK_API_KEY=tu_api_key_aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1  # opcional
DEEPSEEK_MODEL=deepseek-chat
```

---

## 🎯 Uso Rápido

### 1. Iniciar el servidor web
```bash
python -m uvicorn backend_app:app --reload --port 8000
```

### 2. Ejecutar simulación con LLM
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

### 3. Acceder a la interfaz
- **Dashboard principal**: http://127.0.0.1:8000/
- **Agentes IA**: http://127.0.0.1:8000/agents

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
- **Responsive**: Se adapta automáticamente al tamaño de la ventana

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
├── agente_geotecnico.py    # Simulador principal
├── agno_team.py           # Equipo de agentes IA
├── backend_app.py         # Servidor FastAPI
├── web/
│   └── index.html        # Interfaz web
├── analisis_geotecnico.ipynb  # Análisis exploratorio
├── requirements.txt       # Dependencias
└── README.md             # Esta documentación
```

### Agregar nuevos agentes
```python
from agno.agent import Agent
from agno.models.deepseek import DeepSeek

# Crear agente personalizado
experto_terreno = Agent(
    name="Experto en Terreno",
    model=DeepSeek(id="deepseek-chat"),
    instructions="Analizar condiciones específicas del terreno...",
)

# Agregar al equipo
agent_os = AgentOS(agents=[vigilante, supervisor, reportador, experto_terreno])
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
