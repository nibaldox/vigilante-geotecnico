#!/usr/bin/env python
"""
Wrapper script que utiliza la estructura modular refactorizada.

Este script es compatible con el original agente_geotecnico.py pero importa
los módulos desde vigilante_geotecnico/*.

Para mantener compatibilidad completa con el archivo original, este wrapper
simplemente delega al módulo refactorizado.
"""

if __name__ == "__main__":
    from vigilante_geotecnico.main import main

    main()
