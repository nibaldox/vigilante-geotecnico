"""Módulo llm: Integración con modelos de lenguaje (DeepSeek)."""

from vigilante_geotecnico.llm.client import call_deepseek
from vigilante_geotecnico.llm.prompts import build_prompt
from vigilante_geotecnico.llm.validation import validate_justificacion_and_refs

__all__ = ["call_deepseek", "build_prompt", "validate_justificacion_and_refs"]
