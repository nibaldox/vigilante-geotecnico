"""Modelos de datos para el sistema de monitoreo geotécnico."""

from dataclasses import dataclass


@dataclass
class Thresholds:
    """Umbrales de alerta y alarma para velocidad de deformación.

    Attributes:
        alerta: Umbral de alerta en mm/hr
        alarma: Umbral de alarma en mm/hr
    """

    alerta: float
    alarma: float


@dataclass
class FixedRules:
    """Reglas fijas para detección de alertas y alarmas.

    Attributes:
        v_alert: Velocidad de alerta (mm/hr)
        v_alarm: Velocidad de alarma (mm/hr)
        d_alert: Deformación acumulada de alerta (mm)
        v_alarm_with_d1: Vel alarma combinada con deformación > d_alert (mm/hr)
        v_alarm_with_d2: Vel alarma extra combinada con deformación > d_alert (mm/hr)
    """

    v_alert: float  # mm/hr
    v_alarm: float  # mm/hr
    d_alert: float  # mm (acumulado)
    v_alarm_with_d1: float  # mm/hr (combo con d_alert)
    v_alarm_with_d2: float  # mm/hr (combo extra con d_alert)
