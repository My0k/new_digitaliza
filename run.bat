@echo off
setlocal enabledelayedexpansion

echo ===============================================
echo Iniciando setup para la aplicación Digitaliza
echo ===============================================

:: Definir la ruta específica a Python
set PYTHON_PATH=C:\Users\UCT\AppData\Local\Microsoft\WindowsApps\python.exe

:: Verificar si Python existe en la ruta especificada
if not exist "%PYTHON_PATH%" (
    echo ERROR: Python no se encuentra en la ruta especificada:
    echo %PYTHON_PATH%
    echo.
    echo Por favor, verifica la instalación de Python o modifica este script con la ruta correcta.
    pause
    exit /b 1
)

:: Mostrar la versión de Python instalada
"%PYTHON_PATH%" --version
echo.

:: Verificar si existe el entorno virtual, si no, crearlo
if not exist "venv\" (
    echo Creando entorno virtual...
    "%PYTHON_PATH%" -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo Entorno virtual creado correctamente.
) else (
    echo Entorno virtual existente encontrado.
)

:: Activar el entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

:: Verificar si existe requirements.txt
if exist "requirements.txt" (
    echo Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
) else (
    echo ADVERTENCIA: No se encontró el archivo requirements.txt
    echo Instalando dependencias mínimas necesarias...
    pip install flask pillow pytesseract PyPDF2 reportlab
)

:: Verificar y crear directorios necesarios
if not exist "templates\" mkdir templates
if not exist "static\css\" mkdir static\css
if not exist "static\js\" mkdir static\js
if not exist "input\" mkdir input
if not exist "pdf_procesado\" mkdir pdf_procesado

:: Detener cualquier proceso que esté usando el puerto 5000
echo Verificando si el puerto 5000 está en uso...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5000') do (
    set pid=%%p
    echo Cerrando proceso !pid! que está usando el puerto 5000...
    taskkill /F /PID !pid! >nul 2>&1
)

:: Iniciar la aplicación Flask
echo.
echo ===============================================
echo Iniciando la aplicación Flask...
echo ===============================================
start "" http://localhost:5000
"%PYTHON_PATH%" app.py

:: Desactivar entorno virtual al finalizar
call venv\Scripts\deactivate.bat

endlocal
