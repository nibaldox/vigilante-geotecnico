from agente_geotecnico import build_prompt as build_prompt_main
from agente_geotecnico_ds import build_prompt as build_prompt_ds


def test_build_prompt_main_contains_length_note():
    snapshot = {"current": {"time": "2025-01-01T00:00:00Z"}}
    p = build_prompt_main(snapshot, just_len=750)
    assert "Nota: la 'justificacion' debe tener aproximadamente 750 caracteres" in p
    assert "Datos disponibles (usar todos)" in p


def test_build_prompt_ds_contains_length_note():
    snapshot = {"current": {"time": "2025-01-01T00:00:00Z"}}
    p = build_prompt_ds(snapshot, just_len=420)
    assert "Nota: la 'justificacion' debe tener aproximadamente 420 caracteres" in p
    assert "Datos disponibles (usar todos)" in p
