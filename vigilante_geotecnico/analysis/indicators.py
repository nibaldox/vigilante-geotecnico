"""Indicadores técnicos para análisis de series temporales geotécnicas."""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from vigilante_geotecnico.core.models import Thresholds


def ema(series: pd.Series, span: int) -> pd.Series:
    """Calcula la media móvil exponencial (EMA) de una serie.

    Args:
        series: Serie temporal de entrada
        span: Ventana de tiempo (span) para el cálculo del EMA

    Returns:
        Serie con los valores del EMA

    Example:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> ema_s = ema(s, span=3)
        >>> len(ema_s) == len(s)
        True
    """
    return series.ewm(span=span, adjust=False).mean()


def detect_events(vel_mm_hr: pd.Series, s_smooth: pd.Series, thr: Thresholds) -> pd.DataFrame:
    """Detecta eventos de alerta y alarma basados en umbrales de velocidad.

    Args:
        vel_mm_hr: Serie de velocidad en mm/hr
        s_smooth: Serie de deformación suavizada
        thr: Umbrales de alerta y alarma

    Returns:
        DataFrame con eventos detectados (inicio, fin, duración, nivel, métricas)

    Example:
        >>> dates = pd.date_range('2025-01-01', periods=100, freq='1H')
        >>> vel = pd.Series([0.5] * 50 + [2.0] * 50, index=dates)
        >>> disp = pd.Series(range(100), index=dates)
        >>> thr = Thresholds(alerta=1.0, alarma=3.0)
        >>> events = detect_events(vel, disp, thr)
        >>> 'nivel' in events.columns
        True
    """
    state = np.zeros(len(vel_mm_hr), dtype=int)
    mask_alerta = vel_mm_hr.abs() > thr.alerta
    mask_alarma = vel_mm_hr.abs() > thr.alarma
    state[mask_alerta.values] = 1
    state[mask_alarma.values] = 2

    idx = vel_mm_hr.index
    segments: List[Tuple[int, pd.Timestamp, pd.Timestamp]] = []
    if len(state) > 0:
        start = 0
        for i in range(1, len(state)):
            if state[i] != state[i - 1]:
                segments.append((state[i - 1], idx[start], idx[i - 1]))
                start = i
        segments.append((state[-1], idx[start], idx[-1]))

    rows: List[Dict] = []
    for st, t0, t1 in segments:
        if st == 0:
            continue
        seg = vel_mm_hr.loc[t0:t1]
        seg_abs = seg.abs()
        peak_vel = float(seg_abs.max())
        peak_time = seg_abs.idxmax()
        disp_delta = float(s_smooth.loc[t1] - s_smooth.loc[t0])
        dur_min = float((t1 - t0).total_seconds() / 60.0)
        rows.append(
            {
                "inicio": t0,
                "fin": t1,
                "dur_min": dur_min,
                "nivel": "ALARMA" if st == 2 else "ALERTA",
                "vel_max_mm_hr": peak_vel,
                "t_vel_max": peak_time,
                "disp_delta_mm": disp_delta,
            }
        )
    return pd.DataFrame(rows).sort_values(["inicio"]).reset_index(drop=True) if rows else pd.DataFrame()
