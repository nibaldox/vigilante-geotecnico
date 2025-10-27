import argparse
import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv  # type: ignore
from openai import OpenAI  # type: ignore
try:
    from rich.console import Console  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.panel import Panel  # type: ignore
    _RICH_AVAILABLE = True
except Exception:
    _RICH_AVAILABLE = False

load_dotenv()


# Prompt del sistema (rol) robusto para guiar al LLM
SYSTEM_PROMPT = (
    "Eres un analista experto en monitoreo geotécnico con radares de deformación. "
    "Priorizas seguridad y trazabilidad. Trabajas SOLO con el contexto dado. "
    "Puedes razonar internamente, pero NO muestras esos pasos. "
    "Devuelve ÚNICAMENTE el JSON del esquema indicado (sin texto extra, sin markdown). "
    "Valida unidades (mm, mm/hr), aplica reglas fijas > adaptativas > persistencia 12h, "
    "y elige el criterio más conservador ante ambigüedad."
)


@dataclass
class Thresholds:
    alerta: float
    alarma: float

@dataclass
class FixedRules:
    v_alert: float  # mm/hr
    v_alarm: float  # mm/hr
    d_alert: float  # mm (acumulado)
    v_alarm_with_d1: float  # mm/hr (combo con d_alert)
    v_alarm_with_d2: float  # mm/hr (combo extra con d_alert)


def load_csv_with_custom_header(csv_path: str) -> pd.DataFrame:
    """Load the ARCSAR CSV with metadata rows and return a clean DataFrame.

    The file uses ';' as separator, metadata on top, and a header row with 'Time;ALT-*'.
    """
    raw = pd.read_csv(csv_path, sep=';', header=None, dtype=str, engine='python')
    mask_header = raw[0].astype(str).str.strip().eq('Time')
    header_idx = int(mask_header[mask_header].index.min()) if mask_header.any() else 2
    df = pd.read_csv(csv_path, sep=';', header=header_idx, engine='python')
    df = df.rename(columns={df.columns[0]: 'time', df.columns[1]: 'disp_mm'})
    df['time'] = pd.to_datetime(df['time'], format='%d-%m-%Y %H:%M', errors='coerce')
    df['disp_mm'] = pd.to_numeric(df['disp_mm'], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    return df


def preprocess_series(df: pd.DataFrame, resample_rule: str = '2T') -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Return (s_original, s_same, s_raw, vel_mm_hr, acc_mm_hr2) sin suavizado.

    Se usa la serie cruda del radar (ordenada) para que el LLM reciba datos no suavizados.
    """
    s = df.set_index('time')['disp_mm'].sort_index()
    # Sin resample ni suavizado: trabajar directo con timestamps originales
    s_raw = s

    dt_min = (s_raw.index.to_series().diff().dt.total_seconds() / 60.0).bfill()
    vel_mm_min = s_raw.diff() / dt_min.values
    acc_mm_min2 = vel_mm_min.diff() / dt_min.values
    vel_mm_hr = vel_mm_min * 60.0
    acc_mm_hr2 = acc_mm_min2 * (60.0 ** 2)
    return s, s_raw, s_raw, vel_mm_hr, acc_mm_hr2


def compute_thresholds_from_baseline(vel_abs: pd.Series, baseline_fraction: float = 0.2) -> Thresholds:
    """Umbrales robustos ALERTA/ALARMA a partir de |vel| cruda,
    usando mediana-rodante (w=5) para estimación y percentiles más conservadores.
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
    """Umbrales robustos en ventana deslizante de window_hours hacia atrás desde end_time.

    Usa mediana-rodante (w=5) sobre |vel| para estimar la distribución y calcula
    percentiles 0.975/0.995 y MAD con factores 7/11.
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


def detect_events(vel_mm_hr: pd.Series, s_smooth: pd.Series, thr: Thresholds) -> pd.DataFrame:
    """Return a DataFrame with events and metrics."""
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
                'inicio': t0,
                'fin': t1,
                'dur_min': dur_min,
                'nivel': 'ALARMA' if st == 2 else 'ALERTA',
                'vel_max_mm_hr': peak_vel,
                't_vel_max': peak_time,
                'disp_delta_mm': disp_delta,
            }
        )
    return pd.DataFrame(rows).sort_values(['inicio']).reset_index(drop=True)


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


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
    # En geotecnia, el desplazamiento acumulado proviene del sensor, puede ser +/-
    # Usamos directamente el valor reportado por el radar (suavizado) como acumulado total
    cur_cum_total = float(cum_total.iloc[i])
    # Acumulado en ventana (delta neto inicio->fin dentro de la ventana)
    cur_cum_window = float(s_smooth.iloc[i] - s_smooth.iloc[start_i])
    # Valor final de acumulado dentro de la ventana (el del último punto)
    cur_cum_final_window = float(s_smooth.iloc[i])
    # Delta instantáneo (último paso)
    cur_delta_mm = float(s_smooth.iloc[i] - s_smooth.iloc[i-1]) if i > 0 else 0.0
    cur_vel = float(vel_mm_hr.iloc[i])
    # duración de la ventana y tasa de acumulación
    dur_hours = max(1e-9, (xi[-1] - xi[0]).total_seconds() / 3600.0)
    accum_rate_mm_hr = float(cur_cum_window / dur_hours)
    accum_mm_per_period = float(accum_rate_mm_hr * max(0.0, accum_period_hours))
    state = 'NORMAL'
    vel_mag = abs(cur_vel)
    d_mag = abs(cur_cum_total)
    decision_source = 'adaptive'
    decision_rule = 'none'
    # reglas fijas (prioridad)
    if fixed is not None:
        if d_mag > fixed.d_alert and vel_mag > fixed.v_alarm_with_d2:
            state = 'ALARMA'
            decision_source = 'fixed'
            decision_rule = f"abs(d)>{fixed.d_alert} & v>{fixed.v_alarm_with_d2}"
        elif d_mag > fixed.d_alert and vel_mag > fixed.v_alarm_with_d1:
            state = 'ALARMA'
            decision_source = 'fixed'
            decision_rule = f"abs(d)>{fixed.d_alert} & v>{fixed.v_alarm_with_d1}"
        elif vel_mag > fixed.v_alarm:
            state = 'ALARMA'
            decision_source = 'fixed'
            decision_rule = f"v>{fixed.v_alarm}"
        elif vel_mag > fixed.v_alert:
            state = 'ALERTA'
            decision_source = 'fixed'
            decision_rule = f"v>{fixed.v_alert}"
        elif d_mag > fixed.d_alert:
            state = 'ALERTA'
            decision_source = 'fixed'
            decision_rule = f"abs(d)>{fixed.d_alert}"
        else:
            # si no disparan fijas, usar umbrales adaptativos
            if vel_mag > thr.alarma:
                state = 'ALARMA'
                decision_source = 'adaptive'
                decision_rule = 'thr_alarma'
            elif vel_mag > thr.alerta:
                state = 'ALERTA'
                decision_source = 'adaptive'
                decision_rule = 'thr_alerta'
            else:
                state = 'NORMAL'
                decision_source = 'adaptive'
                decision_rule = 'none'
    else:
        if vel_mag > thr.alarma:
            state = 'ALARMA'
            decision_rule = 'thr_alarma'
        elif vel_mag > thr.alerta:
            state = 'ALERTA'
            decision_rule = 'thr_alerta'

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
    sign_change_window = (cum_min_val <= 0.0 <= cum_max_val)

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
        'window': {
            'start': str(xi[0]),
            'end': str(xi[-1]),
            'n_points': len(xi),
            'duration_hours': dur_hours,
            'cum_min_mm': cum_min_val,
            't_cum_min': str(t_cum_min),
            'cum_max_mm': cum_max_val,
            't_cum_max': str(t_cum_max),
            'sign_change_window': bool(sign_change_window),
            'accum_window_threshold_mm': float(accum_window_threshold_mm),
        },
        'current': {
            'time': cur_time,
            'disp_mm': cur_disp,
            'cum_disp_mm_total': cur_cum_total,
            'cum_disp_mm_window': cur_cum_window,
            'cum_disp_mm_final_window': cur_cum_final_window,
            'delta_mm': cur_delta_mm,
            'vel_mm_hr': cur_vel,
            'accum_rate_mm_hr': accum_rate_mm_hr,
            'accum_mm_per_period': accum_mm_per_period,
            'accum_period_hours': accum_period_hours,
            'state': state,
        },
        'thresholds': {'alerta_mm_hr': thr.alerta, 'alarma_mm_hr': thr.alarma, 'source': thr_source},
        'decision': {'source': decision_source, 'rule': decision_rule},
        'fixed_rules': None if fixed is None else {
            'v_alert': fixed.v_alert,
            'v_alarm': fixed.v_alarm,
            'd_alert': fixed.d_alert,
            'v_alarm_with_d1': fixed.v_alarm_with_d1,
            'v_alarm_with_d2': fixed.v_alarm_with_d2,
        },
        'history': history or {},
        'bollinger': {
            'disp': {
                'center': disp_mean,
                'std': disp_std,
                'upper': bb_disp_upper,
                'lower': bb_disp_lower,
                'k': float(bb_k),
                'pos_pct': pos_disp,
            },
            'vel': {
                'center': vel_mean,
                'std': vel_std,
                'upper': bb_vel_upper,
                'lower': bb_vel_lower,
                'k': float(bb_k),
                'pos_pct': pos_vel,
            },
        },
        'slices': {
            'disp_mm': downsample_pair(disp_slice.index, disp_slice.values),
            'cum_disp_total_mm': downsample_pair(cum_total_slice.index, cum_total_slice.values),
            'vel_mm_hr': downsample_pair(vel_slice.index, vel_slice.values),
            'ema12': downsample_pair(ema12_slice.index, ema12_slice.values),
            'ema48': downsample_pair(ema48_slice.index, ema48_slice.values),
            'ema96': downsample_pair(ema96_slice.index, ema96_slice.values),
        },
    }


def build_prompt(snapshot: Dict) -> str:
    # Política refinada A–E
    policy = (
          "Instrucciones (español):\n"
        "A) Snapshot esperado: vel(mm/hr), deform(mm), history{vel_series,deform_series}, "
        "fixed_rules{v_alert,v_alarm,d_alert,v_alarm_with_d1,v_alarm_with_d2,use_abs}, "
        "thresholds{normal,alerta,alarma}, persistence{win_h,metric,rule}, "
        "meta{radar_id,site,bank,bench,report_window_min,quality_flags}.\n"
        "B) Sanidad: Rechaza NaN/Inf; si quality_flags.spikes=true aplica de-spike (>5σ) y agrega evidence=de-spike. "
        "Marca low_snr/gap_data si aplica. Si falta un parámetro crítico de una regla, omite esa regla y añade missing_param.\n"
        "C) Reglas (orden y prioridad): "
        "(Fijas; usar absoluto salvo use_abs=false) ALARMA si deform>d_alert y vel>v_alarm_with_d2; "
        "ALARMA si deform>d_alert y vel>v_alarm_with_d1; ALARMA si vel>v_alarm; "
        "ALERTA si deform>d_alert; ALERTA si vel>v_alert. En empate, prioriza combinaciones deform+vel.\n"
        "   (Adaptativas; solo si no disparan fijas) con |vel|: ALARMA si >= thresholds.alarma; "
        "ALERTA si >= thresholds.alerta; NORMAL si < thresholds.normal. Ante zona gris, el umbral más conservador.\n"
        "   (Persistencia 12h) Si la regla de persistence se cumple, eleva 1 nivel (máx. ALARMA) y añade pers_12h.\n"
        "D) Evidence (solo catálogo): v>v_alert, v>v_alarm, |v|>thr_alerta, |v|>thr_alarma, "
        "d>d_alert, d↑, v↑, pers_12h, de-spike, missing_param, low_snr, gap_data, hist_peak. "
        "PROHIBIDO números crudos en evidence.\n"
        "E) Salida JSON (formato estricto, sin texto extra):\n"
        "{"
        "\"level\":\"NORMAL|ALERTA|ALARMA\","
        "\"rationale\":\"<=180 chars\","
        "\"justificacion\":\"200-420 chars, explicación clara con números redondeados (2 decimales)\","
        "\"confidence_0_1\":0.0,"
        "\"actions\":[\"...\",\"...\",\"...\"],"
        "\"evidence\":[\"...\",\"...\"],"
        "\"metrics\":{"
        "\"vel\":0.0,\"deform\":0.0,"
        "\"umbral_disparado\":\"v_alarm|v_alert|d_alert|v_alarm_with_d1|v_alarm_with_d2|thr_alerta|thr_alarma|none\","
        "\"persistencia_h\":12}"
        "}\n"
        "F) Redacción:\n"
        "- 'rationale' (≤180): síntesis para banner (estado + tendencia + mención breve de umbral/persistencia).\n"
        "- 'justificacion' (200–420): usa esta plantilla compacta para no técnicos, con redondeo a 2 decimales:\n"
        "  1) Contexto: vel X mm/hr y deform Y mm en la ventana. "
        "  2) Disparo: se activa ___ por comparación con umbral ___. "
        "  3) Tendencia: en Z h la serie muestra ___. "
        "  4) Persistencia/calidad: ___. "
        "  5) Cierre: el nivel ___ es coherente con criterio conservador.\n"
        "G) Acciones: máximo 3, imperativas y verificables. "
        "H) Confianza: base 0.60; +0.15 si fijas; +0.10 si pers_12h; −0.20 low_snr; −0.15 si gap_data>10%; clip [0,1].\n"
        "I) Autochequeo: JSON único válido; límites de longitudes; evidence solo catálogo; "
        "coherencia fijas>adaptativas>persistencia; unidades y abs() donde corresponda.\n"
        "Contexto:\n"
    )
    return policy + "\nContexto:\n" + pd.Series(snapshot).to_json() + "\n"


def _print_structured_console(
    snapshot: Dict,
    llm_content: Optional[str],
    llm_json: Optional[Dict],
    disagreement: bool,
    console_format: str,
    llm_error: Optional[str],
) -> None:
    """Renderiza salida por consola en formato rich/plain/json."""
    import json

    summary = {
        'time': snapshot['current']['time'],
        'state': snapshot['current']['state'],
        'metrics': {
            'disp_mm': round(float(snapshot['current']['disp_mm']), 3),
            'delta_mm': round(float(snapshot['current']['delta_mm']), 3),
            'cum_window_mm': round(float(snapshot['current']['cum_disp_mm_window']), 3),
            'vel_mm_hr': round(float(snapshot['current']['vel_mm_hr']), 3),
            'accum_rate_mm_hr': round(float(snapshot['current']['accum_rate_mm_hr']), 3),
            'accum_mm_per_period': round(float(snapshot['current']['accum_mm_per_period']), 3),
            'period_hours': snapshot['current']['accum_period_hours'],
        },
        'thresholds': snapshot['thresholds'],
        'window': {
            'duration_hours': round(float(snapshot['window']['duration_hours']), 3),
            'n_points': snapshot['window']['n_points'],
            'cum_min_mm': round(float(snapshot['window']['cum_min_mm']), 3),
            'cum_max_mm': round(float(snapshot['window']['cum_max_mm']), 3),
            'sign_change_window': bool(snapshot['window']['sign_change_window']),
            'accum_window_threshold_mm': round(float(snapshot['window']['accum_window_threshold_mm']), 3),
        },
        'llm': {
            'json': llm_json,
            'raw': (llm_content[:500] + '…') if (llm_content and len(llm_content) > 500) else llm_content,
            'disagreement': disagreement or False,
            'error': llm_error,
        },
    }

    if console_format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if console_format == 'rich' and _RICH_AVAILABLE:
        console = Console()
        # Encabezado con color por estado
        state = summary['state']
        state_style = {
            'NORMAL': 'bold green',
            'ALERTA': 'bold yellow',
            'ALARMA': 'bold red',
        }.get(state, 'bold')
        title = f"SNAPSHOT @ {summary['time']}"
        console.rule(title)
        console.print(Panel(f"Estado: [ {state} ]", title="Situación", style=state_style))

        # Tabla de métricas con etiquetas amigables
        labels = {
            'disp_mm': 'Lectura acumulada (mm)',
            'delta_mm': 'Desplazamiento último paso (mm)',
            'cum_window_mm': 'Acumulado en ventana (mm)',
            'vel_mm_hr': 'Velocidad (mm/hr)',
            'accum_rate_mm_hr': 'Tasa de acumulación (mm/hr)',
            'accum_mm_per_period': f"Proyección {summary['metrics']['period_hours']} h (mm)",
            'period_hours': 'Periodo (h)',
        }
        t = Table(show_header=True, header_style="bold")
        t.add_column("Métrica")
        t.add_column("Valor")
        thr_alerta = float(summary['thresholds']['alerta_mm_hr'])
        thr_alarma = float(summary['thresholds']['alarma_mm_hr'])
        for key in ['disp_mm','delta_mm','cum_window_mm','vel_mm_hr','accum_rate_mm_hr','accum_mm_per_period']:
            if key not in summary['metrics']:
                continue
            value = summary['metrics'][key]
            value_str = str(value)
            if key == 'vel_mm_hr':
                try:
                    v = float(value)
                    av = abs(v)
                    if av > thr_alarma:
                        value_str = f"[bold red]{value_str}[/]"
                    elif av > thr_alerta:
                        value_str = f"[bold yellow]{value_str}[/]"
                    else:
                        value_str = f"[bold green]{value_str}[/]"
                except Exception:
                    pass
            t.add_row(labels.get(key, key), value_str)

        th = Table(show_header=True, header_style="bold")
        th.add_column("Umbral")
        th.add_column("mm/hr")
        th.add_row('Alerta', str(round(float(summary['thresholds']['alerta_mm_hr']), 3)))
        th.add_row('Alarma', str(round(float(summary['thresholds']['alarma_mm_hr']), 3)))
        th.add_row('Fuente', str(summary['thresholds'].get('source', 'N/A')))

        # Regla aplicada
        dec = snapshot.get('decision', {})
        dec_src = dec.get('source', 'N/A')
        dec_rule = dec.get('rule', 'N/A')
        console.print(Panel(f"Decisión: {dec_src} | Regla: {dec_rule}", title="Clasificación"))

        console.print(Panel(t, title="Métricas actuales"))
        # Ventana: extremos y cruce por cero
        w = snapshot['window']
        thr_acc = float(w.get('accum_window_threshold_mm', 0.0))
        color_acc = None
        try:
            aw = abs(float(summary['metrics']['cum_window_mm']))
            if thr_acc > 0:
                if aw > 2.0 * thr_acc:
                    color_acc = 'bold red'
                elif aw > thr_acc:
                    color_acc = 'bold yellow'
        except Exception:
            pass
        info = (
            f"Ventana: {w['duration_hours']:.2f} h, puntos={w['n_points']}\n"
            f"Min acumulado: {w['cum_min_mm']:.3f} mm @ {w['t_cum_min']}\n"
            f"Max acumulado: {w['cum_max_mm']:.3f} mm @ {w['t_cum_max']}\n"
            f"Cruce por 0 en ventana: {'Sí' if w['sign_change_window'] else 'No'}\n"
            f"Umbral acumulado ventana: {thr_acc:.3f} mm"
        )
        console.print(Panel(info, title="Ventana (extremos)", style=color_acc or ""))
        console.print(Panel(th, title="Umbrales"))

        llm_title = "LLM (acuerdo ✔)" if not summary['llm']['disagreement'] else "LLM (desacuerdo ✖)"
        if summary['llm']['error']:
            console.print(Panel(f"Error: {summary['llm']['error']}", title=llm_title, style="bold red"))
        elif summary['llm']['json']:
            lj = summary['llm']['json']
            lt = Table(show_header=True, header_style="bold")
            lt.add_column("Campo")
            lt.add_column("Valor")
            lt.add_row('Nivel sugerido', str(lj.get('level')))
            lt.add_row('Confianza (0-1)', str(lj.get('confidence_0_1')))
            actions = lj.get('actions') or []
            lt.add_row('Acciones', "; ".join(map(str, actions)))
            rationale = lj.get('rationale')
            console.print(Panel(lt, title=llm_title))
            if rationale:
                console.print(Panel(str(rationale), title="Justificación"))
        else:
            console.print(Panel(str(summary['llm']['raw'] or ''), title=llm_title))
        return

    # Plain fallback
    print(f"\n=== {summary['time']} ===")
    print(f"Estado: {summary['state']}")
    print("Métricas:")
    print(f"  - Lectura acumulada (mm): {summary['metrics']['disp_mm']}")
    print(f"  - Desplazamiento último paso (mm): {summary['metrics']['delta_mm']}")
    print(f"  - Acumulado en ventana (mm): {summary['metrics']['cum_window_mm']}")
    print(f"  - Velocidad (mm/hr): {summary['metrics']['vel_mm_hr']}")
    print(f"  - Tasa de acumulación (mm/hr): {summary['metrics']['accum_rate_mm_hr']}")
    print(f"  - Proyección {summary['metrics']['period_hours']} h (mm): {summary['metrics']['accum_mm_per_period']}")
    # Ventana: extremos y cruce por cero
    w = snapshot['window']
    print(f"Ventana: {w['duration_hours']:.2f} h, puntos={w['n_points']}")
    print(f"  - Min acumulado: {round(float(w['cum_min_mm']),3)} mm @ {w['t_cum_min']}")
    print(f"  - Max acumulado: {round(float(w['cum_max_mm']),3)} mm @ {w['t_cum_max']}")
    print(f"  - Cruce por 0 en ventana: {'Sí' if w['sign_change_window'] else 'No'}")
    print(f"  - Umbral acumulado ventana (mm): {w['accum_window_threshold_mm']}")
    print("Umbrales:")
    print(f"  - Alerta (mm/hr): {round(float(summary['thresholds']['alerta_mm_hr']), 3)}")
    print(f"  - Alarma (mm/hr): {round(float(summary['thresholds']['alarma_mm_hr']), 3)}")
    print(f"  - Fuente: {summary['thresholds'].get('source', 'N/A')}")
    dec = snapshot.get('decision', {})
    print(f"Clasificación: source={dec.get('source','N/A')} rule={dec.get('rule','N/A')}")
    if summary['llm']['error']:
        print(f"LLM error: {summary['llm']['error']}")
    elif summary['llm']['json']:
        lj = summary['llm']['json']
        print("LLM:")
        print(f"  - Nivel sugerido: {lj.get('level')}")
        print(f"  - Confianza (0-1): {lj.get('confidence_0_1')}")
        print(f"  - Acciones: {', '.join(map(str, (lj.get('actions') or [])))}")
        if lj.get('rationale'):
            print(f"  - Justificación: {lj.get('rationale')}")
        print(f"  - Acuerdo LLM vs regla: {not summary['llm']['disagreement']}")
    else:
        print(f"LLM: {summary['llm']['raw']}")


def call_deepseek(
    api_key: str,
    prompt: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_connect: float = 10.0,
    timeout_read: float = 60.0,
    retries: int = 3,
    retry_backoff: float = 2.0,
) -> str:
    base = base_url or os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com/v1'
    mdl = model or os.getenv('DEEPSEEK_MODEL') or 'deepseek-chat'
    # OpenAI SDK compatible client towards DeepSeek endpoint
    client = OpenAI(
        api_key=api_key,
        base_url=base.rstrip('/'),
        timeout=timeout_read,
    )
    last_exc: Optional[Exception] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            resp = client.chat.completions.create(
                model=mdl,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            try:
                return resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                return str(resp)
        except Exception as e:
            last_exc = e
            if attempt >= max(1, retries):
                break
            sleep_s = max(0.1, retry_backoff ** (attempt - 1))
            print(f"DeepSeek retry {attempt}/{retries} tras error: {repr(e)}; esperando {sleep_s:.2f}s...")
            time.sleep(sleep_s)
    raise RuntimeError(f"DeepSeek request failed after {retries} attempts: {repr(last_exc)}")


def run_simulation(
    csv_path: str,
    resample_rule: str,
    step_points: int,
    lookback_min: int,
    accum_rate_hours: float,
    accum_window_threshold_mm: float,
    baseline_fraction: float,
    sleep_seconds: float,
    llm_every: int,
    dry_run: bool,
    base_url: Optional[str],
    model: Optional[str],
    log_jsonl: Optional[str] = None,
    only_disagreements: bool = False,
    start_at: Optional[str] = None,
    v_alert: float = 1.0,
    v_alarm: float = 3.0,
    d_alert: float = 5.0,
    v_alarm_with_d1: float = 1.5,
    v_alarm_with_d2: float = 2.0,
    summary_json: Optional[str] = 'resumen.json',
    summary_top_k: int = 10,
    emit_every_min: Optional[float] = None,
) -> None:
    df = load_csv_with_custom_header(csv_path)
    if start_at:
        try:
            ts = pd.to_datetime(start_at)
            df = df[df['time'] >= ts].reset_index(drop=True)
        except Exception:
            pass
    _, _, s_smooth, vel_mm_hr, _ = preprocess_series(df, resample_rule=resample_rule)
    # la serie ya representa deformación acumulada; usar directamente
    cum_total = s_smooth

    # EMAs por rol (Vigilante: desplazamiento 1h/3h/12h)
    # Cálculo dinámico según resolución temporal
    x_idx = s_smooth.index
    if len(x_idx) > 1:
        pts_per_min = max(1, int(pd.Timedelta('60s') / (x_idx[1] - x_idx[0])))
    else:
        pts_per_min = 1
    ema1h_pts = max(1, 60 * pts_per_min)
    ema3h_pts = max(1, 180 * pts_per_min)
    ema12h_pts = max(1, 720 * pts_per_min)
    ema12 = ema(s_smooth, ema1h_pts)
    ema48 = ema(s_smooth, ema3h_pts)
    ema96 = ema(s_smooth, ema12h_pts)

    thr = compute_thresholds_from_baseline(vel_mm_hr.abs(), baseline_fraction=baseline_fraction)
    print(f"Umbrales iniciales: ALERTA={thr.alerta:.3f} mm/hr | ALARMA={thr.alarma:.3f} mm/hr")

    points_per_minute = max(1, int(pd.Timedelta('60s') / (x_idx[1] - x_idx[0]))) if len(x_idx) > 1 else 30
    lookback_points = max(points_per_minute, int((lookback_min * 60) / ((x_idx[1] - x_idx[0]).total_seconds() if len(x_idx) > 1 else 120)))

    # Programación de emisiones por tiempo (opcional)
    emit_interval = None
    next_emit = None
    if emit_every_min is not None:
        try:
            emit_interval = pd.Timedelta(minutes=float(emit_every_min))
            if start_at:
                next_emit = pd.to_datetime(start_at)
            else:
                next_emit = x_idx[0]
        except Exception:
            emit_interval = None
            next_emit = None

    api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if not api_key and not dry_run:
        print('ADVERTENCIA: DEEPSEEK_API_KEY no configurada. Se usará dry-run (sin llamadas a LLM).')
        dry_run = True

    # Contadores de resumen
    level_counts: Dict[str, int] = {'NORMAL': 0, 'ALERTA': 0, 'ALARMA': 0}
    source_counts: Dict[str, int] = {'fixed': 0, 'adaptive': 0}
    rule_counts: Dict[str, int] = defaultdict(int)

    # Acumuladores de eventos
    alarm_events: List[Dict] = []
    alert_events: List[Dict] = []

    for i in range(1, len(x_idx)):
        if i % step_points != 0 and i < len(x_idx) - 1:
            continue
        # recalcular umbrales deslizantes de 12h (si hay datos suficientes)
        thr_sliding = compute_thresholds_sliding(vel_mm_hr.abs(), end_time=x_idx[i], window_hours=12.0)
        thr_effective = thr_sliding or thr
        thr_source = 'sliding_12h' if thr_sliding is not None else 'initial'

        snapshot = summarize_window(
            x_idx=x_idx,
            s_smooth=s_smooth,
            vel_mm_hr=vel_mm_hr,
            cum_total=cum_total,
            ema12=ema12,
            ema48=ema48,
            ema96=ema96,
            thr=thr_effective,
            thr_source=thr_source,
            i=i,
            lookback_points=lookback_points,
            accum_period_hours=max(0.0, float(accum_rate_hours)),
            accum_window_threshold_mm=float(accum_window_threshold_mm),
            bb_k=float(os.getenv('BOLLINGER_K', '2.0')),
            fixed=FixedRules(v_alert=v_alert, v_alarm=v_alarm, d_alert=d_alert, v_alarm_with_d1=v_alarm_with_d1, v_alarm_with_d2=v_alarm_with_d2),
            history={
                'start_time': str(x_idx[0]) if len(x_idx) else None,
                'elapsed_hours': float((x_idx[i] - x_idx[0]).total_seconds()/3600.0) if len(x_idx) else 0.0,
                'cum_total_min_mm': float(cum_total.min()) if len(cum_total) else 0.0,
                'cum_total_max_mm': float(cum_total.max()) if len(cum_total) else 0.0,
                'vel_abs_p95_mm_hr': float(vel_mm_hr.abs().quantile(0.95)) if len(vel_mm_hr.dropna()) else 0.0,
                'vel_abs_p99_mm_hr': float(vel_mm_hr.abs().quantile(0.99)) if len(vel_mm_hr.dropna()) else 0.0,
            },
        )
        if not snapshot:
            continue
        prompt = build_prompt(snapshot)

        # salida estructurada: intentaremos parsear JSON del LLM y mostrar con rich/plain

        llm_content: Optional[str] = None
        # Decidir si llamar al LLM por programación temporal u ordinal
        should_call_llm = False
        if not dry_run:
            if emit_interval is not None and next_emit is not None:
                if x_idx[i] >= next_emit:
                    should_call_llm = True
            else:
                if llm_every and (i // step_points) % max(1, llm_every) == 0:
                    should_call_llm = True

        if not should_call_llm or dry_run:
            print('(dry-run/skip) omitiendo llamada LLM por programación)')
        else:
            try:
                llm_content = call_deepseek(
                    api_key=api_key,
                    prompt=prompt,
                    base_url=base_url,
                    model=model,
                    timeout_connect=float(os.getenv('LLM_TIMEOUT_CONNECT', '10')),
                    timeout_read=float(os.getenv('LLM_TIMEOUT_READ', '60')),
                    retries=int(os.getenv('LLM_RETRIES', '3')),
                    retry_backoff=float(os.getenv('LLM_RETRY_BACKOFF', '2.0')),
                )
                # Programar la siguiente emisión si usamos reloj simulado
                if emit_interval is not None and next_emit is not None:
                    # avanzar next_emit hasta que supere el tiempo actual
                    while next_emit is not None and x_idx[i] >= next_emit:
                        next_emit = next_emit + emit_interval
            except Exception as e:
                llm_error = repr(e)
                _print_structured_console(snapshot, None, None, False, os.getenv('CONSOLE_FORMAT', 'rich'), llm_error)
                continue

        # logging JSONL y discrepancias
        if log_jsonl:
            import json
            record = {
                'time': snapshot['current']['time'],
                'current_state': snapshot['current']['state'],
                'vel_mm_hr': snapshot['current']['vel_mm_hr'],
                'disp_mm': snapshot['current']['disp_mm'],
                'cum_disp_mm_total': snapshot['current']['cum_disp_mm_total'],
                'thresholds': snapshot['thresholds'],
                'llm': llm_content,
                'llm_model': model,
            }
            # inferencia simple del nivel del LLM si entregó JSON
            disagreement = False
            llm_json = None
            if llm_content:
                try:
                    # buscar bloque JSON básico
                    start = llm_content.find('{')
                    end = llm_content.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        llm_json = json.loads(llm_content[start : end + 1])
                        record['llm_json'] = llm_json
                        # extraer rationale en texto natural
                        try:
                            record['llm_rationale'] = str(llm_json.get('rationale', ''))
                        except Exception:
                            pass
                        llm_level = str(llm_json.get('level', '')).upper()
                        if llm_level in {'NORMAL', 'ALERTA', 'ALARMA'}:
                            record['llm_level'] = llm_level
                            if llm_level != snapshot['current']['state']:
                                disagreement = True
                                record['disagreement'] = True
                except Exception:
                    pass
            if only_disagreements and not disagreement:
                pass
            else:
                with open(log_jsonl, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # impresión estructurada en consola
        _print_structured_console(
            snapshot=snapshot,
            llm_content=llm_content,
            llm_json=record.get('llm_json') if log_jsonl else None,
            disagreement=bool(record.get('disagreement')) if log_jsonl else False,
            console_format=os.getenv('CONSOLE_FORMAT', 'rich'),
            llm_error=None,
        )

        # actualizar contadores
        try:
            lvl = str(snapshot['current']['state'])
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            dec = snapshot.get('decision', {})
            src = dec.get('source')
            if src:
                source_counts[src] = source_counts.get(src, 0) + 1
            rule = dec.get('rule')
            if rule:
                rule_counts[str(rule)] += 1
            # capturar eventos
            ev = {
                'time': snapshot['current']['time'],
                'vel_mm_hr': float(snapshot['current']['vel_mm_hr']),
                'cum_disp_mm_total': float(snapshot['current']['cum_disp_mm_total']),
                'cum_disp_mm_window': float(snapshot['current']['cum_disp_mm_window']),
                'accum_rate_mm_hr': float(snapshot['current']['accum_rate_mm_hr']),
                'decision_source': str(dec.get('source', '')),
                'decision_rule': str(dec.get('rule', '')),
            }
            if lvl == 'ALARMA':
                alarm_events.append(ev)
            elif lvl == 'ALERTA':
                alert_events.append(ev)
        except Exception:
            pass

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    # Resumen final
    try:
        import json
        if _RICH_AVAILABLE and os.getenv('CONSOLE_FORMAT', 'rich') == 'rich':
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel

            console = Console()
            console.rule("Resumen de simulación")

            t_levels = Table(show_header=True, header_style="bold")
            t_levels.add_column("Nivel")
            t_levels.add_column("Conteo", justify="right")
            for k in ['NORMAL', 'ALERTA', 'ALARMA']:
                t_levels.add_row(k, str(level_counts.get(k, 0)))

            t_sources = Table(show_header=True, header_style="bold")
            t_sources.add_column("Fuente")
            t_sources.add_column("Conteo", justify="right")
            for k in ['fixed', 'adaptive']:
                t_sources.add_row(k, str(source_counts.get(k, 0)))

            t_rules = Table(show_header=True, header_style="bold")
            t_rules.add_column("Regla")
            t_rules.add_column("Conteo", justify="right")
            for rule, cnt in sorted(rule_counts.items(), key=lambda x: (-x[1], x[0]))[:10]:
                t_rules.add_row(rule, str(cnt))

            console.print(Panel(t_levels, title="Niveles"))
            console.print(Panel(t_sources, title="Fuentes de decisión"))
            console.print(Panel(t_rules, title="Top reglas activadas"))
            # Top alarmas
            def _top_table(items: List[Dict], key: str, title: str) -> Table:
                tt = Table(show_header=True, header_style="bold")
                tt.add_column("time")
                tt.add_column("vel_mm_hr", justify="right")
                tt.add_column("cum_total_mm", justify="right")
                tt.add_column("cum_win_mm", justify="right")
                tt.add_column("rule")
                for ev in items[:max(0, int(summary_top_k))]:
                    tt.add_row(
                        str(ev['time']),
                        f"{ev['vel_mm_hr']:.3f}",
                        f"{ev['cum_disp_mm_total']:.3f}",
                        f"{ev['cum_disp_mm_window']:.3f}",
                        ev.get('decision_rule','')
                    )
                return tt
            top_by_vel = sorted(alarm_events, key=lambda e: abs(e.get('vel_mm_hr', 0.0)), reverse=True)
            top_by_accum = sorted(alarm_events, key=lambda e: abs(e.get('cum_disp_mm_window', 0.0)), reverse=True)
            console.print(Panel(_top_table(top_by_vel, 'vel_mm_hr', 'Alarmas por |vel|'), title="Alarmas TOP por |vel|"))
            console.print(Panel(_top_table(top_by_accum, 'cum_disp_mm_window', 'Alarmas por |acum_win|'), title="Alarmas TOP por |acum ventana|"))
        else:
            print("\n=== Resumen de simulación ===")
            print("Niveles:")
            for k in ['NORMAL', 'ALERTA', 'ALARMA']:
                print(f"  - {k}: {level_counts.get(k, 0)}")
            print("Fuentes de decisión:")
            for k in ['fixed', 'adaptive']:
                print(f"  - {k}: {source_counts.get(k, 0)}")
            print("Top reglas activadas:")
            for rule, cnt in sorted(rule_counts.items(), key=lambda x: (-x[1], x[0]))[:10]:
                print(f"  - {rule}: {cnt}")
            # Top alarmas
            top_by_vel = sorted(alarm_events, key=lambda e: abs(e.get('vel_mm_hr', 0.0)), reverse=True)
            top_by_accum = sorted(alarm_events, key=lambda e: abs(e.get('cum_disp_mm_window', 0.0)), reverse=True)
            print("Top alarmas por |vel|:")
            for ev in top_by_vel[:max(0, int(summary_top_k))]:
                print(f"  - {ev['time']} vel={ev['vel_mm_hr']:.3f} cum_win={ev['cum_disp_mm_window']:.3f} rule={ev.get('decision_rule','')}")
            print("Top alarmas por |acum ventana|:")
            for ev in top_by_accum[:max(0, int(summary_top_k))]:
                print(f"  - {ev['time']} cum_win={ev['cum_disp_mm_window']:.3f} vel={ev['vel_mm_hr']:.3f} rule={ev.get('decision_rule','')}")
        # escribir resumen a JSON si se solicita
        if summary_json:
            # estadísticas básicas
            try:
                vel_series = vel_mm_hr.dropna()
                v_mean = float(vel_series.mean()) if len(vel_series) else 0.0
                v_p95_abs = float(vel_series.abs().quantile(0.95)) if len(vel_series) else 0.0
                v_p99_abs = float(vel_series.abs().quantile(0.99)) if len(vel_series) else 0.0
                accum_12h_series = s_smooth.rolling('12H').apply(lambda x: x.iloc[-1] - x.iloc[0], raw=False).dropna()
                a_mean = float(accum_12h_series.mean()) if len(accum_12h_series) else 0.0
                a_p95_abs = float(accum_12h_series.abs().quantile(0.95)) if len(accum_12h_series) else 0.0
                a_p99_abs = float(accum_12h_series.abs().quantile(0.99)) if len(accum_12h_series) else 0.0
                a_min = float(accum_12h_series.min()) if len(accum_12h_series) else 0.0
                a_max = float(accum_12h_series.max()) if len(accum_12h_series) else 0.0
                stats = {
                    'vel_mm_hr': {
                        'mean': v_mean,
                        'p95_abs': v_p95_abs,
                        'p99_abs': v_p99_abs,
                    },
                    'accum_12h_mm': {
                        'mean': a_mean,
                        'p95_abs': a_p95_abs,
                        'p99_abs': a_p99_abs,
                        'min': a_min,
                        'max': a_max,
                    },
                }
            except Exception:
                stats = {}

            summary = {
                'meta': {
                    'csv_path': csv_path,
                    'start_at': start_at,
                    'resample_rule': resample_rule,
                    'accum_rate_hours': accum_rate_hours,
                    'accum_window_threshold_mm': accum_window_threshold_mm,
                    'fixed_rules': {
                        'v_alert': v_alert,
                        'v_alarm': v_alarm,
                        'd_alert': d_alert,
                        'v_alarm_with_d1': v_alarm_with_d1,
                        'v_alarm_with_d2': v_alarm_with_d2,
                    },
                    'llm': {
                        'base_url': base_url,
                        'model': model,
                        'every': llm_every,
                    },
                    'initial_thresholds_mm_hr': {
                        'alerta': thr.alerta,
                        'alarma': thr.alarma,
                    },
                    'time_range': {
                        'start': str(x_idx[0]) if len(x_idx) else None,
                        'end': str(x_idx[-1]) if len(x_idx) else None,
                        'points': int(len(x_idx)),
                    },
                },
                'counts': {
                    'levels': level_counts,
                    'sources': source_counts,
                    'rules': dict(sorted(rule_counts.items(), key=lambda x: (-x[1], x[0]))),
                },
                'stats': stats,
                'events': {
                    'alarms_top_by_vel': top_by_vel[:max(0, int(summary_top_k))],
                    'alarms_top_by_accum': top_by_accum[:max(0, int(summary_top_k))],
                    'alerts_count': len(alert_events),
                    'alarms_count': len(alarm_events),
                },
            }
            with open(summary_json, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Agente geotécnico con evaluación LLM (DeepSeek).')
    p.add_argument('--csv', default='disp_example.csv', help='Ruta al CSV de entrada')
    p.add_argument('--resample', default='2T', help='Regla de resampleo pandas (ej: 2T)')
    p.add_argument('--start-at', type=str, default=None, help='Fecha/hora de inicio (ej: 2025-08-01 03:00)')
    p.add_argument('--step-points', type=int, default=60, help='Puntos por iteración de simulación')
    p.add_argument('--lookback-min', type=int, default=120, help='Minutos de ventana para resumen')
    p.add_argument('--accum-rate-hours', type=float, default=24.0, help='Horas para tasa de acumulación normalizada (mm por X h)')
    p.add_argument('--baseline-fraction', type=float, default=0.2, help='Fracción inicial para baseline de umbrales')
    p.add_argument('--sleep', type=float, default=0.05, help='Segundos de espera entre iteraciones')
    p.add_argument('--llm-every', type=int, default=1, help='Realizar llamada LLM cada N snapshots (si no se usa --emit-every-min)')
    p.add_argument('--emit-every-min', type=float, default=None, help='Emitir (y llamar LLM) cada M minutos simulados (prioritario)')
    p.add_argument('--dry-run', action='store_true', help='No llamar al LLM, solo imprimir')
    p.add_argument('--base-url', default=None, help='Base URL de la API de DeepSeek (opcional)')
    p.add_argument('--model', default=None, help='Modelo DeepSeek (ej: deepseek-chat)')
    p.add_argument('--log-jsonl', default=None, help='Ruta a archivo JSONL para registrar snapshots/LLM')
    p.add_argument('--only-disagreements', action='store_true', help='Guardar solo discrepancias LLM vs lógica')
    p.add_argument('--llm-timeout-connect', type=float, default=10.0, help='Timeout conexión LLM (s)')
    p.add_argument('--llm-timeout-read', type=float, default=60.0, help='Timeout lectura LLM (s)')
    p.add_argument('--llm-retries', type=int, default=3, help='Reintentos LLM')
    p.add_argument('--llm-retry-backoff', type=float, default=2.0, help='Backoff exponencial base')
    p.add_argument('--accum-window-threshold-mm', type=float, default=1.0, help='Umbral visual para acumulado en ventana (mm)')
    # Reglas fijas
    p.add_argument('--v-alert', type=float, default=1.0, help='Velocidad alerta (mm/hr)')
    p.add_argument('--v-alarm', type=float, default=3.0, help='Velocidad alarma (mm/hr)')
    p.add_argument('--d-alert', type=float, default=5.0, help='Deformación acumulada alerta (mm)')
    p.add_argument('--v-alarm-with-d1', type=float, default=1.5, help='Vel alarma con deformación>5 (mm/hr)')
    p.add_argument('--v-alarm-with-d2', type=float, default=2.0, help='Vel alarma extra con deformación>5 (mm/hr)')
    p.add_argument('--summary-json', type=str, default='resumen.json', help='Ruta para guardar resumen JSON (o vacío para desactivar)')
    p.add_argument('--summary-top-k', type=int, default=10, help='Top K alarmas a incluir en resumen')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    # Filtrar fecha de inicio si se define
    run_simulation(
        csv_path=args.csv,
        resample_rule=args.resample,
        step_points=args.step_points,
        lookback_min=args.lookback_min,
        accum_rate_hours=float(args.accum_rate_hours),
        accum_window_threshold_mm=float(args.accum_window_threshold_mm),
        baseline_fraction=args.baseline_fraction,
        sleep_seconds=args.sleep,
        llm_every=max(1, args.llm_every),
        dry_run=bool(args.dry_run),
        base_url=args.base_url,
        model=args.model,
        log_jsonl=args.log_jsonl,
        only_disagreements=bool(args.only_disagreements),
        start_at=args.start_at,
        v_alert=float(args.v_alert),
        v_alarm=float(args.v_alarm),
        d_alert=float(args.d_alert),
        v_alarm_with_d1=float(args.v_alarm_with_d1),
        v_alarm_with_d2=float(args.v_alarm_with_d2),
        summary_json=(args.summary_json or None),
        summary_top_k=int(args.summary_top_k),
        emit_every_min=args.emit_every_min,
    )


if __name__ == '__main__':
    main()


