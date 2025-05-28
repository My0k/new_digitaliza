@echo off
setlocal
echo.
echo ================================
echo === INICIANDO APLICACION FLASK ===
echo ================================
echo.

rem Ir al directorio del script
cd /d %~dp0
echo [INFO] Directorio actual: %cd%
echo.

rem Verificar Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta en el PATH. Asegurate de tenerlo instalado.
    pause
    exit /b
)
python --version

rem Verificar entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [WARN] Entorno virtual no encontrado en "venv\Scripts\activate.bat"
    echo [INFO] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Fallo al crear el entorno virtual.
        pause
        exit /b
    )
    echo [OK] Entorno virtual creado correctamente.
) else (
    echo [OK] Entorno virtual encontrado.
)

rem Activar entorno virtual
echo.
echo [INFO] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b
)
echo [OK] Entorno virtual activado.

rem Instalar dependencias
echo.
echo [INFO] Instalando dependencias desde requirements.txt...
if exist requirements.txt (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo al instalar los paquetes de requirements.txt.
        pause
        exit /b
    )
    echo [OK] Dependencias instaladas.
) else (
    echo [WARN] No se encontro el archivo requirements.txt
)

rem Configurar Tesseract
echo.
echo [INFO] Configurando Tesseract...
set "TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata"
set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
echo [OK] PATH de Tesseract configurado.

rem Cerrar procesos en el puerto 5000
echo.
echo [INFO] Revisando si el puerto 5000 esta en uso...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
    echo [WARN] Proceso escuchando en puerto 5000 con PID %%a. Cerrando...
    taskkill /PID %%a /F >nul 2>&1
    echo [OK] Proceso %%a terminado.
)

rem Verificar existencia de app.py
echo.
if not exist app.py (
    echo [ERROR] No se encontro app.py en el directorio actual: %cd%
    pause
    exit /b
)
echo [OK] Archivo app.py encontrado.

rem Abrir navegador en localhost:5000
echo.
echo [INFO] Abriendo Microsoft Edge en http://localhost:5000...
start microsoft-edge:http://localhost:5000

rem Iniciar Flask
echo.
echo [INFO] Ejecutando app.py...
python app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion fallo al ejecutarse. Codigo de error: %errorlevel%
    pause
)
