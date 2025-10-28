"""Funciones de preprocesamiento de series temporales geotécnicas."""

from typing import Tuple

import pandas as pd


def preprocess_series(
    df: pd.DataFrame, resample_rule: str = "2T"
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Preprocesa series temporales de deformación.

    Devuelve (s_original, s_same, s_raw, vel_mm_hr, acc_mm_hr2) sin suavizado.
    Se usa la serie cruda del radar (ordenada) para que el LLM reciba datos no suavizados.

    Args:
        df: DataFrame con columnas 'time' y 'disp_mm'
        resample_rule: Regla de resampleo pandas (por defecto "2T" = 2 minutos)

    Returns:
        Tupla con:
            - s_original: Serie original indexada por tiempo
            - s_same: Serie sin cambios (igual a s_raw)
            - s_raw: Serie cruda sin suavizado
            - vel_mm_hr: Velocidad en mm/hr
            - acc_mm_hr2: Aceleración en mm/hr²

    Example:
        >>> df = pd.DataFrame({
        ...     'time': pd.date_range('2025-01-01', periods=100, freq='2T'),
        ...     'disp_mm': np.cumsum(np.random.randn(100) * 0.1)
        ... })
        >>> s, s_same, s_raw, vel, acc = preprocess_series(df)
        >>> len(vel) == len(df)
        True
    """
    s = df.set_index("time")["disp_mm"].sort_index()
    # Sin resample ni suavizado: trabajar directo con timestamps originales
    s_raw = s

    dt_min = (s_raw.index.to_series().diff().dt.total_seconds() / 60.0).bfill()
    vel_mm_min = s_raw.diff() / dt_min.values
    acc_mm_min2 = vel_mm_min.diff() / dt_min.values
    vel_mm_hr = vel_mm_min * 60.0
    acc_mm_hr2 = acc_mm_min2 * (60.0**2)
    return s, s_raw, s_raw, vel_mm_hr, acc_mm_hr2
