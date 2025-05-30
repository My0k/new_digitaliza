@echo off
setlocal
echo.
echo ========================================
echo === INSTALADOR TESSERACT + IDIOMA 'spa'
echo ========================================
echo.

cd /d C:\new_digitaliza-sinapi

:: Paso 1 - Detectar arquitectura de Windows
echo [INFO] Detectando arquitectura del sistema...
set "ARCH="
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set "ARCH=x64"
) else (
    set "ARCH=x86"
)
echo [INFO] Arquitectura detectada: %ARCH%

:: Paso 2 - Establecer URL del instalador según arquitectura
if "%ARCH%"=="x64" (
    set "INSTALLER_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-v5.3.3.20231005.exe"
) else (
    set "INSTALLER_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w32-setup-v5.3.3.20231005.exe"
)

set "INSTALLER_FILE=tesseract-installer.exe"

:: Paso 3 - Descargar instalador
echo [INFO] Descargando instalador desde:
echo %INSTALLER_URL%
powershell -Command "Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_FILE%'"

:: Paso 4 - Ejecutar instalador silenciosamente
echo [INFO] Instalando Tesseract OCR...
start /wait %INSTALLER_FILE% /SILENT

:: Paso 5 - Establecer variables
set "TESS_PATH=C:\Program Files\Tesseract-OCR"
set "TESSDATA_PATH=%TESS_PATH%\tessdata"
set "LANG_FILE=spa.traineddata"
set "DOWNLOAD_URL=https://github.com/tesseract-ocr/tessdata/raw/main/%LANG_FILE%"
set "DEST_FILE=%TESSDATA_PATH%\%LANG_FILE%"

:: Agregar Tesseract al PATH para esta sesión
set "PATH=%PATH%;%TESS_PATH%"

:: Paso 6 - Verificar carpeta tessdata
if not exist "%TESSDATA_PATH%" (
    echo [ERROR] No se encontro la carpeta: %TESSDATA_PATH%
    echo Asegurate de que Tesseract se haya instalado correctamente.
    pause
    exit /b
)

:: Paso 7 - Descargar idioma spa si no existe
if exist "%DEST_FILE%" (
    echo [OK] El idioma 'spa' ya esta instalado en: %DEST_FILE%
) else (
    echo [INFO] Descargando idioma 'spa'...
    powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%DEST_FILE%'"

    if exist "%DEST_FILE%" (
        echo [OK] spa instalado exitosamente.
    ) else (
        echo [ERROR] Fallo la descarga del idioma.
    )
)

:: Paso 8 - Verificacion
echo.
echo === VERIFICANDO INSTALACION DE TESSERACT ===
where tesseract
tesseract --version

echo.
echo === PROCESO COMPLETADO ===
pause
