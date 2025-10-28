import numpy as np
import pandas as pd

from agente_geotecnico import compute_thresholds_from_baseline, load_csv_with_custom_header


def test_compute_thresholds_from_baseline_simple():
    # simple series with low variance: thresholds should be numeric and alarma >= alerta
    s = pd.Series(np.concatenate([np.zeros(50), np.ones(50) * 0.5]))
    thr = compute_thresholds_from_baseline(s.abs(), baseline_fraction=0.2)
    assert hasattr(thr, "alerta")
    assert hasattr(thr, "alarma")
    assert thr.alarma >= thr.alerta


def test_load_csv_with_custom_header(tmp_path):
    csv = tmp_path / "sample.csv"
    # create a small ARCSAR-like file with header row starting with 'Time'
    # ensure metadata lines use separators so pandas can parse rows with a fixed number of fields
    content = (
        "meta line 1;;\n"
        "meta line 2;;\n"
        "Time;ALT-001;note\n"
        "01-01-2025 00:00;1.23;x\n"
        "02-01-2025 01:00;2.34;y\n"
    )
    csv.write_text(content, encoding="utf-8")
    df = load_csv_with_custom_header(str(csv))
    assert "time" in df.columns
    assert "disp_mm" in df.columns
    assert len(df) == 2
