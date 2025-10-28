"""
Vigilante Geotécnico - Sistema de monitoreo inteligente para deformaciones geotécnicas.

Este paquete proporciona herramientas para analizar datos de radares de interferometría
y detectar deformaciones del terreno en tiempo real.
"""

__version__ = "1.0.0"
__author__ = "Vigilante Geotécnico Team"

from vigilante_geotecnico.core.models import FixedRules, Thresholds

__all__ = ["FixedRules", "Thresholds", "__version__"]
