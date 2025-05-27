@echo off
setlocal enabledelayedexpansion

set PYTHON_PATH=C:\Users\UCT\AppData\Local\Programs\Python\Python312\python.exe
set VENV_DIR=%CD%\venv
set PORT=5000

echo === Verificando si Tesseract OCR está instalado ===
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo Tesseract OCR no está instalado. Procediendo a instalarlo...
    
    echo === Verificando si Chocolatey está instalado ===
    where choco >nul 2>&1
    if %errorlevel% neq 0 (
        echo Instalando Chocolatey...
        @powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
        set PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin
    )
    
    echo === Instalando Tesseract OCR mediante Chocolatey ===
    choco install tesseract -y
    
    echo === Agregando Tesseract al PATH ===
    set PATH=%PATH%;C:\Program Files\Tesseract-OCR
    setx PATH "%PATH%;C:\Program Files\Tesseract-OCR" /M
    
    echo === Tesseract OCR ha sido instalado ===
    
    echo === IMPORTANTE: Se requiere reiniciar este script ===
    echo Tesseract ha sido instalado. Por favor, cierre esta ventana
    echo y ejecute nuevamente el script para que los cambios surtan efecto.
    pause
    exit
) else (
    echo Tesseract OCR ya está instalado.
)

echo === Verificando datos de idioma español para Tesseract ===
if not exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
    echo Los datos del idioma español no están instalados. Descargando...
    mkdir "C:\Program Files\Tesseract-OCR\tessdata" 2>nul
    
    echo Descargando archivo de datos del idioma español...
    powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata', 'C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata')"
    
    if exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
        echo Datos del idioma español instalados correctamente.
    ) else (
        echo Error al descargar los datos del idioma español.
        echo Por favor, descargue manualmente el archivo spa.traineddata de:
        echo https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata
        echo Y colóquelo en: C:\Program Files\Tesseract-OCR\tessdata\
        pause
    )
) else (
    echo Datos del idioma español ya están instalados.
)

echo === Cerrando procesos en el puerto %PORT% ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% "') do (
    if not "%%a"=="0" (
        echo Terminando proceso con PID: %%a
        taskkill /F /PID %%a 2>nul
    )
)

echo === Verificando entorno virtual ===
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creando entorno virtual...
    "%PYTHON_PATH%" -m venv "%VENV_DIR%"
) else (
    echo Entorno virtual ya existe.
)

echo === Activando entorno virtual ===
call "%VENV_DIR%\Scripts\activate.bat"

echo === Instalando requisitos ===
if exist "%CD%\requirements.txt" (
    echo Instalando desde requirements.txt...
    pip install -r "%CD%\requirements.txt"
) else (
    echo Archivo requirements.txt no encontrado.
    echo Instalando dependencias básicas...
    pip install flask pytesseract Pillow
)

echo === Configurando variables de entorno para Tesseract ===
set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
set PATH=%PATH%;C:\Program Files\Tesseract-OCR

echo === Iniciando aplicación Flask ===
echo.
echo Si la aplicación se cierra inmediatamente, puede ejecutarla manualmente con:
echo cd "%CD%" ^& "%VENV_DIR%\Scripts\python.exe" app.py
echo.

rem Inicia Flask en una nueva ventana con las variables de entorno configuradas
start "Flask App" cmd /k "set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata && cd "%CD%" && "%VENV_DIR%\Scripts\python.exe" app.py"

echo === Esperando a que la aplicación inicie ===
timeout /t 5 /nobreak > nul

echo === Abriendo navegador ===
start http://localhost:%PORT%

echo === Aplicación iniciada ===
echo Para detener la aplicación, cierre la ventana de comandos o presione Ctrl+C

echo.
echo === Manteniendo esta ventana abierta ===
echo La aplicación Flask está ejecutándose en una ventana separada.
echo Puede cerrar esta ventana cuando termine de usar la aplicación.
echo.
pause
