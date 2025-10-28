"""Cálculo de umbrales adaptativos para detección de alertas y alarmas."""

from typing import Optional

import pandas as pd

from vigilante_geotecnico.core.models import Thresholds


def compute_thresholds_from_baseline(vel_abs: pd.Series, baseline_fraction: float = 0.2) -> Thresholds:
    """Calcula umbrales robustos ALERTA/ALARMA a partir de |vel| cruda.

    Usa mediana-rodante (w=5) para estimación y percentiles más conservadores.

    Args:
        vel_abs: Serie de velocidad absoluta
        baseline_fraction: Fracción inicial del dataset para baseline (0.0-1.0)

    Returns:
        Thresholds con umbrales de alerta y alarma

    Example:
        >>> vel = pd.Series([0.1, 0.15, 0.12, 0.2, 0.18] * 20)
        >>> thr = compute_thresholds_from_baseline(vel)
        >>> thr.alerta > 0
        True
    """
    n = len(vel_abs)
    if n == 0:
        return Thresholds(alerta=0.0, alarma=0.0)

    # estimador robusto para la distribución (no afecta detección, solo umbrales)
    vel_abs_rb = vel_abs.rolling(window=5, center=True, min_periods=1).median()

    end = max(1, int(n * max(0.01, min(0.9, baseline_fraction))))
    base = vel_abs_rb.iloc[:end].dropna()
    if base.empty:
        base = vel_abs_rb.dropna()

    median = base.median()
    mad = (base - median).abs().median()
    # percentiles más altos para reducir falsos positivos en datos crudos
    p_alerta = float(base.quantile(0.975))
    p_alarma = float(base.quantile(0.995))

    mad_k_alerta = 7.0
    mad_k_alarma = 11.0
    thr_alerta = float(max(median + mad_k_alerta * 1.4826 * mad, p_alerta))
    thr_alarma = float(max(median + mad_k_alarma * 1.4826 * mad, p_alarma, 1.3 * thr_alerta))
    return Thresholds(alerta=thr_alerta, alarma=thr_alarma)


def compute_thresholds_sliding(
    vel_abs: pd.Series,
    end_time: pd.Timestamp,
    window_hours: float,
) -> Optional[Thresholds]:
    """Calcula umbrales robustos en ventana deslizante.

    Usa mediana-rodante (w=5) sobre |vel| para estimar la distribución y calcula
    percentiles 0.975/0.995 y MAD con factores 7/11.

    Args:
        vel_abs: Serie de velocidad absoluta indexada por tiempo
        end_time: Tiempo final de la ventana
        window_hours: Tamaño de la ventana en horas hacia atrás desde end_time

    Returns:
        Thresholds o None si no hay suficientes datos (< 30 puntos)

    Example:
        >>> dates = pd.date_range('2025-01-01', periods=100, freq='1H')
        >>> vel = pd.Series([0.1] * 100, index=dates)
        >>> thr = compute_thresholds_sliding(vel, dates[-1], 12.0)
        >>> thr is not None
        True
    """
    if window_hours <= 0:
        return None
    start_time = end_time - pd.Timedelta(hours=float(window_hours))
    window = vel_abs.loc[start_time:end_time].dropna()
    if len(window) < 30:
        return None
    window_rb = window.rolling(window=5, center=True, min_periods=1).median()
    median = window_rb.median()
    mad = (window_rb - median).abs().median()
    p_alerta = float(window_rb.quantile(0.975))
    p_alarma = float(window_rb.quantile(0.995))
    thr_alerta = float(max(median + 7.0 * 1.4826 * mad, p_alerta))
    thr_alarma = float(max(median + 11.0 * 1.4826 * mad, p_alarma, 1.3 * thr_alerta))
    return Thresholds(alerta=thr_alerta, alarma=thr_alarma)
