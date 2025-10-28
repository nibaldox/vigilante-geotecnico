"""Funciones auxiliares de formateo para salida."""

from typing import Any


def format_number(value: Any, decimals: int = 3) -> str:
    """Formatea un número con N decimales, retorna '—' si no es válido.

    Args:
        value: Valor a formatear
        decimals: Número de decimales

    Returns:
        String formateado o '—'

    Example:
        >>> format_number(1.2345, 2)
        '1.23'
        >>> format_number(None, 2)
        '—'
    """
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return "—"


def format_timestamp(ts: Any) -> str:
    """Formatea un timestamp de forma legible.

    Args:
        ts: Timestamp (string o datetime)

    Returns:
        String formateado

    Example:
        >>> format_timestamp("2025-01-01 12:30:45")
        '2025-01-01 12:30:45'
    """
    if ts is None:
        return "—"
    return str(ts)
