@echo off
setlocal enabledelayedexpansion

echo ================================================
echo === Instalador automático de Tesseract OCR ====
echo ================================================
echo.

:: Verificar si Chocolatey ya esta instalado
where choco >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Chocolatey no esta instalado. Instalando...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
     "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo instalar Chocolatey.
        pause
        exit /b 1
    )
) else (
    echo [OK] Chocolatey ya esta instalado.
)

:: Agregar Chocolatey al PATH (en caso de que no este disponible aun)
set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

:: Instalar Tesseract OCR con Chocolatey
echo [INFO] Instalando Tesseract OCR...
choco install tesseract -y
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Tesseract.
    pause
    exit /b 1
)

:: Verificar si la carpeta tessdata existe
set "TESSDATA_PATH=C:\Program Files\Tesseract-OCR\tessdata"
if not exist "!TESSDATA_PATH!" (
    echo [ERROR] No se encontro la carpeta: !TESSDATA_PATH!
    echo Es posible que Tesseract no se haya instalado correctamente.
    pause
    exit /b 1
)

:: Descargar idioma spa.traineddata si no existe
set "LANG_FILE=spa.traineddata"
set "DEST_FILE=!TESSDATA_PATH!\!LANG_FILE!"
if exist "!DEST_FILE!" (
    echo [OK] El idioma 'spa' ya esta instalado.
) else (
    echo [INFO] Descargando idioma 'spa'...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata' -OutFile '!DEST_FILE!'"
    if exist "!DEST_FILE!" (
        echo [OK] spa.traineddata descargado correctamente.
    ) else (
        echo [ERROR] No se pudo descargar spa.traineddata.
    )
)

:: Verificar instalacion
echo.
echo === Verificando Tesseract ===
where tesseract
tesseract --version

echo.
echo === PROCESO COMPLETADO ===
pause
