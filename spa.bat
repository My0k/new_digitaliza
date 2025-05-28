@echo off
setlocal
echo.
echo ================================
echo === INSTALANDO IDIOMA TESSERACT ===
echo ================================
echo.

set "TESSDATA_PATH=C:\Program Files\Tesseract-OCR\tessdata"
set "LANG_FILE=spa.traineddata"
set "DOWNLOAD_URL=https://github.com/tesseract-ocr/tessdata/raw/main/%LANG_FILE%"
set "DEST_FILE=%TESSDATA_PATH%\%LANG_FILE%"

rem Verificar que la carpeta tessdata existe
if not exist "%TESSDATA_PATH%" (
    echo [ERROR] No se encontro la carpeta: %TESSDATA_PATH%
    echo Asegurate de que Tesseract este instalado correctamente.
    pause
    exit /b
)

rem Verificar si el archivo ya existe
if exist "%DEST_FILE%" (
    echo [OK] El idioma 'spa' ya esta instalado en: %DEST_FILE%
    pause
    exit /b
)

echo [INFO] Descargando idioma 'spa' para Tesseract...
powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%DEST_FILE%'"

if exist "%DEST_FILE%" (
    echo [OK] Descarga completada. El idioma fue instalado exitosamente.
) else (
    echo [ERROR] No se pudo descargar el archivo. Verifica tu conexion a Internet o permisos de escritura.
)

pause
