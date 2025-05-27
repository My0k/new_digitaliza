@echo off
setlocal enabledelayedexpansion

echo ===============================================
echo Iniciando setup para la aplicación Digitaliza
echo ===============================================

:: Buscar Python en diferentes ubicaciones
set PYTHON_FOUND=0
set PYTHON_PATH=

:: Intentar encontrar Python en ubicaciones comunes (incluyendo Python 3.12)
if exist "C:\Program Files\Python312\python.exe" (
    set PYTHON_PATH=C:\Program Files\Python312\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Python312\python.exe" (
    set PYTHON_PATH=C:\Python312\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Program Files\Python311\python.exe" (
    set PYTHON_PATH=C:\Program Files\Python311\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Program Files\Python310\python.exe" (
    set PYTHON_PATH=C:\Program Files\Python310\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Program Files\Python39\python.exe" (
    set PYTHON_PATH=C:\Program Files\Python39\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Python311\python.exe" (
    set PYTHON_PATH=C:\Python311\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Python310\python.exe" (
    set PYTHON_PATH=C:\Python310\python.exe
    set PYTHON_FOUND=1
) else if exist "C:\Python39\python.exe" (
    set PYTHON_PATH=C:\Python39\python.exe
    set PYTHON_FOUND=1
)

:: Si no encontramos Python, intentar instalarlo con winget
if %PYTHON_FOUND% equ 0 (
    echo No se encontró una instalación válida de Python.
    echo.
    echo Intentando instalar Python automáticamente con winget...
    
    :: Verificar si winget está disponible
    winget --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Instalando Python 3.12 con winget (esto puede tomar varios minutos)...
        winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        
        :: Verificar si la instalación fue exitosa
        if exist "C:\Program Files\Python312\python.exe" (
            set PYTHON_PATH=C:\Program Files\Python312\python.exe
            set PYTHON_FOUND=1
            echo Python instalado correctamente.
        ) else (
            echo La instalación automática no pudo completarse.
        )
    ) else (
        echo Winget no está disponible en este sistema. No se puede instalar Python automáticamente.
    )
)

:: Si aún no encontramos Python, mostrar mensaje y salir
if %PYTHON_FOUND% equ 0 (
    echo ERROR: No se pudo encontrar o instalar Python en el sistema.
    echo.
    echo Es necesario instalar Python 3.8 o superior para ejecutar esta aplicación.
    echo Por favor, descargue e instale Python desde: https://www.python.org/downloads/
    echo.
    echo Asegúrese de marcar la opción "Add Python to PATH" durante la instalación.
    echo.
    echo ¿Desea abrir la página de descarga de Python ahora? (S/N)
    choice /c SN /m "Su elección:"
    if errorlevel 2 goto :end
    if errorlevel 1 start "" https://www.python.org/downloads/
    echo.
    echo Después de instalar Python, ejecute este script nuevamente.
    goto :end
)

echo Python encontrado en: %PYTHON_PATH%
echo.

:: Mostrar la versión de Python instalada
"%PYTHON_PATH%" --version
echo.

:: Verificar si existe el entorno virtual, si no, crearlo
if not exist "venv\" (
    echo Creando entorno virtual...
    "%PYTHON_PATH%" -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual.
        echo Intente instalando el módulo venv manualmente con:
        echo "%PYTHON_PATH%" -m pip install virtualenv
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

:end
endlocal
