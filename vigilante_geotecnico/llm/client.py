"""Cliente para comunicación con la API de DeepSeek."""

import os
import time
from typing import Optional

from openai import OpenAI  # type: ignore

from vigilante_geotecnico.core.constants import SYSTEM_PROMPT


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
    """Realiza llamada a la API de DeepSeek con reintentos.

    Args:
        api_key: API key de DeepSeek
        prompt: Prompt del usuario
        base_url: URL base de la API (opcional, por defecto de env)
        model: Modelo a usar (opcional, por defecto de env)
        timeout_connect: Timeout de conexión en segundos
        timeout_read: Timeout de lectura en segundos
        retries: Número de reintentos
        retry_backoff: Factor de backoff exponencial

    Returns:
        Respuesta del modelo como string

    Raises:
        RuntimeError: Si falla después de todos los reintentos

    Example:
        >>> response = call_deepseek(
        ...     api_key="sk-xxx",
        ...     prompt="Analiza estos datos...",
        ...     retries=1
        ... )  # doctest: +SKIP
    """
    base = base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1"
    mdl = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

    # OpenAI SDK compatible client towards DeepSeek endpoint
    client = OpenAI(
        api_key=api_key,
        base_url=base.rstrip("/"),
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
                temperature=0.6,
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
