#!/usr/bin/env python
"""
Script para iniciar el servidor completo de Vigilante Geotécnico.

Inicia:
- Backend FastAPI (puerto 8000)
- Frontend web (servido por FastAPI)
- Scheduler de reportes automáticos
- Agno AgentOS (si está disponible)

Uso:
    python start_server.py
    python start_server.py --port 8000 --reload
"""

import argparse
import logging
import subprocess
import sys
import webbrowser
from pathlib import Path
from time import sleep

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def check_dependencies():
    """Verifica que las dependencias estén instaladas."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        from apscheduler.schedulers.background import BackgroundScheduler  # noqa: F401

        logging.info("✅ Dependencias verificadas")
        return True
    except ImportError as e:
        logging.error(f"❌ Falta dependencia: {e}")
        logging.error("Instala con: pip install -r requirements.txt")
        return False


def start_server(port: int = 8000, reload: bool = False, open_browser: bool = True):
    """Inicia el servidor FastAPI con uvicorn."""
    if not check_dependencies():
        sys.exit(1)

    logging.info("\n" + "=" * 80)
    logging.info("🏔️  VIGILANTE GEOTÉCNICO - Servidor Completo")
    logging.info("=" * 80 + "\n")

    logging.info(f"📡 Iniciando servidor en puerto {port}...")
    logging.info(f"🌐 Frontend: http://localhost:{port}")
    logging.info(f"📚 API Docs: http://localhost:{port}/docs")
    logging.info(f"🤖 Agno Agents: http://localhost:{port}/agents")
    logging.info(f"📊 Reportes: http://localhost:{port}/api/reports/list")
    logging.info("\n" + "-" * 80)
    logging.info("⏰ Reportes automáticos: 6:30 AM y 6:30 PM")
    logging.info("📁 Directorio de reportes: ./reports/")
    logging.info("-" * 80 + "\n")

    # Abrir navegador después de 2 segundos
    if open_browser:
        import threading

        def open_browser_delayed():
            sleep(2)
            try:
                webbrowser.open(f"http://localhost:{port}")
                logging.info("🌐 Navegador abierto automáticamente")
            except Exception:
                pass

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Iniciar uvicorn
    cmd = ["uvicorn", "backend_app:app", "--host", "0.0.0.0", "--port", str(port)]

    if reload:
        cmd.append("--reload")
        logging.info("🔄 Modo reload activado (auto-recarga en cambios)")

    logging.info(f"🚀 Ejecutando: {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logging.info("\n\n🛑 Servidor detenido por el usuario")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error al iniciar servidor: {e}")
        sys.exit(1)


def main():
    """Función principal con argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Inicia el servidor completo de Vigilante Geotécnico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:

  # Inicio básico
  python start_server.py

  # Con auto-reload (desarrollo)
  python start_server.py --reload

  # Puerto personalizado
  python start_server.py --port 9000

  # Sin abrir navegador
  python start_server.py --no-browser

Características incluidas:
  ✅ Backend FastAPI (API REST)
  ✅ Frontend web interactivo
  ✅ Selector de archivos JSONL
  ✅ Reportes automáticos (6:30 AM/PM)
  ✅ Generación de reportes bajo demanda
  ✅ Agno AgentOS (si está instalado)
  ✅ Zoom avanzado en gráficos
  ✅ Modo oscuro/claro
  ✅ Responsive design
        """,
    )

    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (default: 8000)")

    parser.add_argument("--reload", action="store_true", help="Auto-reload en cambios de código")

    parser.add_argument("--no-browser", action="store_true", help="No abrir navegador automáticamente")

    args = parser.parse_args()

    start_server(port=args.port, reload=args.reload, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
