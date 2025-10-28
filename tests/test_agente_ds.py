import numpy as np
import pandas as pd

from agente_geotecnico_ds import (
    FixedRules,
    Thresholds,
    ema,
    extract_first_json,
    summarize_window,
    validate_and_fix_llm_json,
)


def test_extract_first_json_basic():
    text = 'Info previa\n{"level": "ALERTA", "metrics": {"vel": 1.2}} extra'
    parsed = extract_first_json(text)
    assert isinstance(parsed, dict)
    assert parsed.get("level") == "ALERTA"


def test_validate_and_fix_llm_json_filters_evidence():
    raw = {
        "level": "alarma",
        "rationale": "Prueba",
        "justificacion": "x" * 210,
        "confidence_0_1": 0.7,
        "actions": ["accion1", "accion2", "accion3", "extra"],
        "evidence": ["v>v_alarm", "unknown_evidence"],
        "metrics": {"vel": 2.3456, "deform": 10.0, "umbral_disparado": "v_alarm", "persistencia_h": 12},
    }
    fixed, warnings = validate_and_fix_llm_json(raw)
    assert isinstance(fixed, dict)
    assert fixed["level"] == "ALARMA"
    assert fixed["metrics"]["vel"] == round(2.3456, 2)
    assert any(w.startswith("evidence_drop") for w in warnings)


def test_summarize_window_basic():
    # create a simple time index hourly
    idx = pd.date_range(start="2025-01-01", periods=12, freq="H")
    # create cumulative displacement with small incremental values
    values = np.cumsum(np.ones(len(idx)) * 0.5)
    s_smooth = pd.Series(values, index=idx)
    # compute vel_mm_hr: differences*60 because original code computes per minute then *60
    vel = s_smooth.diff().fillna(0) * 60.0

    cum_total = s_smooth
    ema12 = ema(s_smooth, span=2)
    ema48 = ema(s_smooth, span=3)
    ema96 = ema(s_smooth, span=4)

    thr = Thresholds(alerta=10.0, alarma=20.0)
    fixed = FixedRules(v_alert=1.0, v_alarm=3.0, d_alert=5.0, v_alarm_with_d1=1.5, v_alarm_with_d2=2.0)

    res = summarize_window(
        x_idx=idx,
        s_smooth=s_smooth,
        vel_mm_hr=vel,
        cum_total=cum_total,
        ema12=ema12,
        ema48=ema48,
        ema96=ema96,
        thr=thr,
        thr_source="test",
        i=6,
        lookback_points=6,
        accum_period_hours=24.0,
        accum_window_threshold_mm=1.0,
        bb_k=2.0,
        fixed=fixed,
        history={"start_time": str(idx[0])},
    )

    assert isinstance(res, dict)
    assert "current" in res and "window" in res
    assert res["current"]["state"] in {"NORMAL", "ALERTA", "ALARMA"}
