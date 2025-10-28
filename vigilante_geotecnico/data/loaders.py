"""Funciones para cargar datos desde diferentes formatos."""

import pandas as pd


def load_csv_with_custom_header(csv_path: str) -> pd.DataFrame:
    """Carga CSV de ARCSAR con filas de metadatos y devuelve DataFrame limpio.

    El archivo usa ';' como separador, metadatos en la parte superior,
    y una fila de encabezado con 'Time;ALT-*'.

    Args:
        csv_path: Ruta al archivo CSV de entrada

    Returns:
        DataFrame con columnas 'time' y 'disp_mm', ordenado por tiempo

    Example:
        >>> df = load_csv_with_custom_header("disp_example.csv")
        >>> df.columns
        Index(['time', 'disp_mm'], dtype='object')
    """
    raw = pd.read_csv(csv_path, sep=";", header=None, dtype=str, engine="python")
    mask_header = raw[0].astype(str).str.strip().eq("Time")
    header_idx = int(mask_header[mask_header].index.min()) if mask_header.any() else 2
    df = pd.read_csv(csv_path, sep=";", header=header_idx, engine="python")
    df = df.rename(columns={df.columns[0]: "time", df.columns[1]: "disp_mm"})
    df["time"] = pd.to_datetime(df["time"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["disp_mm"] = pd.to_numeric(df["disp_mm"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    return df
