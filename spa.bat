@echo off
setlocal
echo.
echo ================================
echo === INSTALANDO TESSERACT + IDIOMA 'spa' ===
echo ================================
echo.

cd /d C:\new_digitaliza-sinapi

:: Paso 1 - Descargar el instalador de Tesseract OCR
set "INSTALLER_URL=https://github.com/UB-Mannheim/tesseract/wiki/tesseract-ocr-w64-setup-v5.3.3.20231005.exe"
set "INSTALLER_FILE=tesseract-installer.exe"

echo [INFO] Descargando instalador de Tesseract OCR...
powershell -Command "Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_FILE%'"

:: Paso 2 - Ejecutar el instalador en modo silencioso
echo [INFO] Instalando Tesseract OCR...
start /wait %INSTALLER_FILE% /SILENT

:: Paso 3 - Establecer ruta de instalación
set "TESS_PATH=C:\Program Files\Tesseract-OCR"
set "TESSDATA_PATH=%TESS_PATH%\tessdata"

:: Agregar temporalmente al PATH para esta sesión
set "PATH=%PATH%;%TESS_PATH%"

:: Paso 4 - Descargar idioma spa
set "LANG_FILE=spa.traineddata"
set "DOWNLOAD_URL=https://github.com/tesseract-ocr/tessdata/raw/main/%LANG_FILE%"
set "DEST_FILE=%TESSDATA_PATH%\%LANG_FILE%"

if not exist "%TESSDATA_PATH%" (
    echo [ERROR] No se encontro la carpeta: %TESSDATA_PATH%
    echo Asegurate de que Tesseract se haya instalado correctamente.
    pause
    exit /b
)

if exist "%DEST_FILE%" (
    echo [OK] El idioma 'spa' ya esta instalado en: %DEST_FILE%
) else (
    echo [INFO] Descargando idioma 'spa' para Tesseract...
    powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%DEST_FILE%'"

    if exist "%DEST_FILE%" (
        echo [OK] Descarga completada. El idioma fue instalado exitosamente.
    ) else (
        echo [ERROR] No se pudo descargar el archivo. Verifica tu conexion o permisos.
    )
)

:: Paso 5 - Verificación final
echo.
echo === VERIFICANDO INSTALACION DE TESSERACT ===
where tesseract
tesseract --version

echo.
echo === FINALIZADO ===
pause
