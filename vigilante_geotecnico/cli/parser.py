"""Parser de argumentos de línea de comandos."""

import argparse


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos para el agente geotécnico.

    Returns:
        Namespace con todos los argumentos parseados

    Example:
        >>> import sys
        >>> sys.argv = ['prog', '--csv', 'data.csv', '--dry-run']
        >>> args = parse_args()
        >>> args.csv
        'data.csv'
        >>> args.dry_run
        True
    """
    p = argparse.ArgumentParser(description="Agente geotécnico con evaluación LLM (DeepSeek).")

    # Archivo de datos
    p.add_argument("--csv", default="disp_example.csv", help="Ruta al CSV de entrada")

    # Parámetros de preprocesamiento
    p.add_argument("--resample", default="2T", help="Regla de resampleo pandas (ej: 2T)")
    p.add_argument("--start-at", type=str, default=None, help="Fecha/hora de inicio (ej: 2025-08-01 03:00)")

    # Parámetros de simulación
    p.add_argument("--step-points", type=int, default=60, help="Puntos por iteración de simulación")
    p.add_argument("--lookback-min", type=int, default=12, help="Minutos de ventana para resumen")
    p.add_argument(
        "--accum-rate-hours", type=float, default=24.0, help="Horas para tasa de acumulación normalizada (mm por X h)"
    )
    p.add_argument("--baseline-fraction", type=float, default=0.2, help="Fracción inicial para baseline de umbrales")
    p.add_argument("--sleep", type=float, default=0.05, help="Segundos de espera entre iteraciones")

    # Parámetros LLM
    p.add_argument(
        "--llm-every", type=int, default=1, help="Realizar llamada LLM cada N snapshots (si no se usa --emit-every-min)"
    )
    p.add_argument(
        "--emit-every-min",
        type=float,
        default=None,
        help="Emitir (y llamar LLM) cada M minutos simulados (prioritario)",
    )
    p.add_argument("--dry-run", action="store_true", help="No llamar al LLM, solo imprimir")
    p.add_argument("--base-url", default=None, help="Base URL de la API de DeepSeek (opcional)")
    p.add_argument("--model", default=None, help="Modelo DeepSeek (ej: deepseek-chat)")

    # Logging y salida
    p.add_argument("--log-jsonl", default=None, help="Ruta a archivo JSONL para registrar snapshots/LLM")
    p.add_argument("--only-disagreements", action="store_true", help="Guardar solo discrepancias LLM vs lógica")

    # Timeouts y reintentos
    p.add_argument("--llm-timeout-connect", type=float, default=10.0, help="Timeout conexión LLM (s)")
    p.add_argument("--llm-timeout-read", type=float, default=60.0, help="Timeout lectura LLM (s)")
    p.add_argument("--llm-retries", type=int, default=3, help="Reintentos LLM")
    p.add_argument("--llm-retry-backoff", type=float, default=2.0, help="Backoff exponencial base")

    # Umbrales y reglas
    p.add_argument(
        "--accum-window-threshold-mm", type=float, default=1.0, help="Umbral visual para acumulado en ventana (mm)"
    )

    # Reglas fijas
    p.add_argument("--v-alert", type=float, default=1.0, help="Velocidad alerta (mm/hr)")
    p.add_argument("--v-alarm", type=float, default=3.0, help="Velocidad alarma (mm/hr)")
    p.add_argument("--d-alert", type=float, default=5.0, help="Deformación acumulada alerta (mm)")
    p.add_argument("--v-alarm-with-d1", type=float, default=1.5, help="Vel alarma con deformación>5 (mm/hr)")
    p.add_argument("--v-alarm-with-d2", type=float, default=2.0, help="Vel alarma extra con deformación>5 (mm/hr)")

    # Resumen
    p.add_argument(
        "--summary-json",
        type=str,
        default="resumen.json",
        help="Ruta para guardar resumen JSON (o vacío para desactivar)",
    )
    p.add_argument("--summary-top-k", type=int, default=10, help="Top K alarmas a incluir en resumen")

    # Validación LLM
    p.add_argument(
        "--just-length",
        type=int,
        default=600,
        help="Longitud objetivo para el campo 'justificacion' en caracteres (ej: 600)",
    )

    return p.parse_args()
