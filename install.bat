@echo off
echo 🚀 Instalando Vigilante Geotécnico...
echo.

REM Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo ✅ Instalación completada!
echo.
echo Para configurar las variables de entorno, edita el archivo .env:
echo DEEPSEEK_API_KEY=tu_api_key_aqui
echo DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
echo DEEPSEEK_MODEL=deepseek-chat
echo.
echo Para iniciar el servidor:
echo python -m uvicorn backend_app:app --reload --port 8000
echo.
echo Para ejecutar la simulación:
echo python agente_geotecnico.py --csv "ARCSAR_20250404_F8_Displacement_AREA ALT-079..csv" --emit-every-min 60
echo.
pause
