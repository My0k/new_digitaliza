@echo off
echo === Iniciando Visor de Documentos ===

REM Verificar si el puerto 5000 está en uso
echo Verificando puerto 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000"') do (
    echo Matando proceso en puerto 5000: %%a
    taskkill /f /pid %%a >nul 2>&1
)

REM Verificar entorno virtual
if exist "venv" (
    echo Activando entorno virtual existente...
    call venv\Scripts\activate.bat
) else (
    echo Creando nuevo entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat

    echo Instalando dependencias...
    pip install flask pillow werkzeug PyPDF2 reportlab pdf2image pytesseract
)

REM Verificar carpeta input
if not exist "input" (
    echo Creando carpeta input...
    mkdir input
)

REM Configurar TESSDATA_PREFIX temporalmente
set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata

REM Verificar si spa.traineddata existe
if not exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
    echo Descargando spa.traineddata...
    powershell -Command ^
      "$url='https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata';" ^
      "$dest='spa.traineddata';" ^
      "Invoke-WebRequest -Uri $url -OutFile $dest;" ^
      "if (Test-Path $dest) { Move-Item -Path $dest -Destination 'C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata' -Force }"

    REM Verificar si la descarga funcionó
    if not exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
        echo ERROR: No se pudo descargar o mover spa.traineddata. Ejecuta este script como administrador.
        pause
        exit /b
    )
)

REM Iniciar aplicacion
echo Iniciando aplicacion...
python app.py

pause
