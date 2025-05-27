@echo off
setlocal EnableDelayedExpansion

echo ===== Iniciando aplicacion de digitalizacion =====
echo.

rem Ir al directorio donde está este .bat
cd /d "%~dp0"

rem Definir ruta del entorno virtual
set VENV_DIR=%CD%\venv

rem Verificar si el entorno virtual existe, si no, crearlo
if not exist "%VENV_DIR%" (
    echo Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual.
        echo Asegurate de tener Python instalado y en el PATH.
        pause
        exit /b 1
    )
    echo Entorno virtual creado exitosamente.
) else (
    echo Entorno virtual encontrado.
)

rem Activar el entorno virtual
echo.
echo Activando entorno virtual...
call "%VENV_DIR%\Scripts\activate.bat"

rem Instalar requirements.txt si existe
if exist requirements.txt (
    echo.
    echo Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ADVERTENCIA: Hubo problemas al instalar dependencias.
    ) else (
        echo Dependencias instaladas correctamente.
    )
) else (
    echo.
    echo ADVERTENCIA: No se encontro el archivo requirements.txt
)

rem Configurar Tesseract
echo.
echo Configurando Tesseract...
set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
set PATH=%PATH%;C:\Program Files\Tesseract-OCR

rem Cerrar procesos que usen el puerto 5000
echo.
echo Verificando si hay procesos usando el puerto 5000...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5000') do (
    set PID=%%p
    if not "!PID!"=="" (
        echo Cerrando proceso !PID! en puerto 5000...
        taskkill /F /PID !PID!
    )
)

rem Crear carpetas necesarias si no existen
if not exist "input" mkdir input
if not exist "pdf_procesado" mkdir pdf_procesado

rem Iniciar la aplicación Flask
echo.
echo ===== Iniciando aplicacion Flask =====
echo.
python app.py

rem Mantener la ventana abierta
pause
