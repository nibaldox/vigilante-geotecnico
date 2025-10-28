"""Análisis de ventanas temporales y resumen de métricas."""

from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from vigilante_geotecnico.core.models import FixedRules, Thresholds


def summarize_window(
    x_idx: pd.DatetimeIndex,
    s_smooth: pd.Series,
    vel_mm_hr: pd.Series,
    cum_total: pd.Series,
    ema12: pd.Series,
    ema48: pd.Series,
    ema96: pd.Series,
    thr: Thresholds,
    thr_source: str,
    i: int,
    lookback_points: int,
    accum_period_hours: float,
    accum_window_threshold_mm: float,
    bb_k: float,
    fixed: Optional[FixedRules],
    history: Optional[Dict],
) -> Dict:
    """Resume métricas y estado en una ventana temporal.

    Args:
        x_idx: Índice temporal de las series
        s_smooth: Serie de deformación suavizada
        vel_mm_hr: Velocidad en mm/hr
        cum_total: Deformación acumulada total
        ema12: EMA 1h
        ema48: EMA 3h
        ema96: EMA 12h
        thr: Umbrales adaptativos
        thr_source: Fuente de los umbrales ("initial" o "sliding_12h")
        i: Índice actual en la serie
        lookback_points: Número de puntos hacia atrás para la ventana
        accum_period_hours: Horas para proyección de acumulación
        accum_window_threshold_mm: Umbral visual para acumulado en ventana
        bb_k: Factor K para bandas de Bollinger
        fixed: Reglas fijas (opcional)
        history: Historial de métricas globales (opcional)

    Returns:
        Diccionario con resumen de ventana, métricas actuales, umbrales, decisión, etc.
    """
    start_i = max(0, i - lookback_points)
    xi = x_idx[start_i:i]
    if len(xi) == 0:
        return {}

    disp_slice = s_smooth.iloc[start_i:i]
    cum_total_slice = cum_total.iloc[start_i:i]
    vel_slice = vel_mm_hr.iloc[start_i:i]
    ema12_slice = ema12.iloc[start_i:i]
    ema48_slice = ema48.iloc[start_i:i]
    ema96_slice = ema96.iloc[start_i:i]

    cur_time = str(x_idx[i])
    cur_disp = float(s_smooth.iloc[i])
    cur_cum_total = float(cum_total.iloc[i])
    cur_cum_window = float(s_smooth.iloc[i] - s_smooth.iloc[start_i])
    cur_cum_final_window = float(s_smooth.iloc[i])
    cur_delta_mm = float(s_smooth.iloc[i] - s_smooth.iloc[i - 1]) if i > 0 else 0.0
    cur_vel = float(vel_mm_hr.iloc[i])

    dur_hours = max(1e-9, (xi[-1] - xi[0]).total_seconds() / 3600.0)
    accum_rate_mm_hr = float(cur_cum_window / dur_hours)
    accum_mm_per_period = float(accum_rate_mm_hr * max(0.0, accum_period_hours))

    state = "NORMAL"
    vel_mag = abs(cur_vel)
    d_mag = abs(cur_cum_total)
    decision_source = "adaptive"
    decision_rule = "none"

    # reglas fijas (prioridad)
    if fixed is not None:
        if d_mag > fixed.d_alert and vel_mag > fixed.v_alarm_with_d2:
            state = "ALARMA"
            decision_source = "fixed"
            decision_rule = f"abs(d)>{fixed.d_alert} & v>{fixed.v_alarm_with_d2}"
        elif d_mag > fixed.d_alert and vel_mag > fixed.v_alarm_with_d1:
            state = "ALARMA"
            decision_source = "fixed"
            decision_rule = f"abs(d)>{fixed.d_alert} & v>{fixed.v_alarm_with_d1}"
        elif vel_mag > fixed.v_alarm:
            state = "ALARMA"
            decision_source = "fixed"
            decision_rule = f"v>{fixed.v_alarm}"
        elif vel_mag > fixed.v_alert:
            state = "ALERTA"
            decision_source = "fixed"
            decision_rule = f"v>{fixed.v_alert}"
        elif d_mag > fixed.d_alert:
            state = "ALERTA"
            decision_source = "fixed"
            decision_rule = f"abs(d)>{fixed.d_alert}"
        else:
            # si no disparan fijas, usar umbrales adaptativos
            if vel_mag > thr.alarma:
                state = "ALARMA"
                decision_source = "adaptive"
                decision_rule = "thr_alarma"
            elif vel_mag > thr.alerta:
                state = "ALERTA"
                decision_source = "adaptive"
                decision_rule = "thr_alerta"
            else:
                state = "NORMAL"
                decision_source = "adaptive"
                decision_rule = "none"
    else:
        if vel_mag > thr.alarma:
            state = "ALARMA"
            decision_rule = "thr_alarma"
        elif vel_mag > thr.alerta:
            state = "ALERTA"
            decision_rule = "thr_alerta"

    # downsample up to 30 points for concise context
    def downsample_pair(idx: Iterable, values: Iterable, k: int = 30) -> List[Tuple[str, float]]:
        idx_list = list(idx)
        val_list = list(values)
        if len(idx_list) <= k:
            return [(str(idx_list[j]), float(val_list[j])) for j in range(len(idx_list))]
        step = max(1, len(idx_list) // k)
        sel = range(0, len(idx_list), step)
        pairs: List[Tuple[str, float]] = []
        for j in sel:
            pairs.append((str(idx_list[j]), float(val_list[j])))
        return pairs[:k]

    # Extremos en la ventana
    if len(cum_total_slice) > 0:
        cum_min_val = float(cum_total_slice.min())
        t_cum_min = cum_total_slice.idxmin()
        cum_max_val = float(cum_total_slice.max())
        t_cum_max = cum_total_slice.idxmax()
    else:
        cum_min_val = cur_cum_total
        t_cum_min = x_idx[i]
        cum_max_val = cur_cum_total
        t_cum_max = x_idx[i]
    sign_change_window = cum_min_val <= 0.0 <= cum_max_val

    # Bandas tipo Bollinger en ventana (media ± k*std)
    try:
        disp_mean = float(disp_slice.mean())
        disp_std = float(disp_slice.std(ddof=0))
        bb_disp_upper = disp_mean + bb_k * disp_std
        bb_disp_lower = disp_mean - bb_k * disp_std
        pos_disp = float((cur_disp - bb_disp_lower) / max(1e-12, (bb_disp_upper - bb_disp_lower)))
    except Exception:
        disp_mean = cur_disp
        disp_std = 0.0
        bb_disp_upper = cur_disp
        bb_disp_lower = cur_disp
        pos_disp = 0.5

    try:
        vel_mean = float(vel_slice.mean())
        vel_std = float(vel_slice.std(ddof=0))
        bb_vel_upper = vel_mean + bb_k * vel_std
        bb_vel_lower = vel_mean - bb_k * vel_std
        pos_vel = float((cur_vel - bb_vel_lower) / max(1e-12, (bb_vel_upper - bb_vel_lower)))
    except Exception:
        vel_mean = cur_vel
        vel_std = 0.0
        bb_vel_upper = cur_vel
        bb_vel_lower = cur_vel
        pos_vel = 0.5

    return {
        "window": {
            "start": str(xi[0]),
            "end": str(xi[-1]),
            "n_points": len(xi),
            "duration_hours": dur_hours,
            "cum_min_mm": cum_min_val,
            "t_cum_min": str(t_cum_min),
            "cum_max_mm": cum_max_val,
            "t_cum_max": str(t_cum_max),
            "sign_change_window": bool(sign_change_window),
            "accum_window_threshold_mm": float(accum_window_threshold_mm),
        },
        "current": {
            "time": cur_time,
            "disp_mm": cur_disp,
            "cum_disp_mm_total": cur_cum_total,
            "cum_disp_mm_window": cur_cum_window,
            "cum_disp_mm_final_window": cur_cum_final_window,
            "delta_mm": cur_delta_mm,
            "vel_mm_hr": cur_vel,
            "accum_rate_mm_hr": accum_rate_mm_hr,
            "accum_mm_per_period": accum_mm_per_period,
            "accum_period_hours": accum_period_hours,
            "state": state,
        },
        "thresholds": {"alerta_mm_hr": thr.alerta, "alarma_mm_hr": thr.alarma, "source": thr_source},
        "decision": {"source": decision_source, "rule": decision_rule},
        "fixed_rules": (
            None
            if fixed is None
            else {
                "v_alert": fixed.v_alert,
                "v_alarm": fixed.v_alarm,
                "d_alert": fixed.d_alert,
                "v_alarm_with_d1": fixed.v_alarm_with_d1,
                "v_alarm_with_d2": fixed.v_alarm_with_d2,
            }
        ),
        "history": history or {},
        "bollinger": {
            "disp": {
                "center": disp_mean,
                "std": disp_std,
                "upper": bb_disp_upper,
                "lower": bb_disp_lower,
                "k": float(bb_k),
                "pos_pct": pos_disp,
            },
            "vel": {
                "center": vel_mean,
                "std": vel_std,
                "upper": bb_vel_upper,
                "lower": bb_vel_lower,
                "k": float(bb_k),
                "pos_pct": pos_vel,
            },
        },
        "slices": {
            "disp_mm": downsample_pair(disp_slice.index, disp_slice.values),
            "cum_disp_total_mm": downsample_pair(cum_total_slice.index, cum_total_slice.values),
            "vel_mm_hr": downsample_pair(vel_slice.index, vel_slice.values),
            "ema12": downsample_pair(ema12_slice.index, ema12_slice.values),
            "ema48": downsample_pair(ema48_slice.index, ema48_slice.values),
            "ema96": downsample_pair(ema96_slice.index, ema96_slice.values),
        },
    }
