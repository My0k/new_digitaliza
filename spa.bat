@echo off
setlocal enabledelayedexpansion

echo ================================================
echo === Instalador robusto de Tesseract + spa  ====
echo ================================================
echo.

:: Verificar si Chocolatey esta instalado
where choco >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Chocolatey no esta instalado. Instalando...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
     "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
)

:: Esperar hasta que choco este disponible (máximo 10 segundos)
set /a retries=0
:wait_for_choco
where choco >nul 2>&1
if %errorlevel% neq 0 (
    set /a retries+=1
    if !retries! gtr 10 (
        echo [ERROR] No se pudo instalar Chocolatey correctamente.
        pause
        exit /b 1
    )
    timeout /t 1 >nul
    goto wait_for_choco
)

echo [OK] Chocolatey esta disponible.

:: Agregar choco al PATH (por si acaso)
set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

:: Instalar Tesseract
echo [INFO] Instalando Tesseract OCR...
choco install tesseract -y
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Tesseract.
    pause
    exit /b 1
)

:: Descargar spa.traineddata
set "TESSDATA_PATH=C:\Program Files\Tesseract-OCR\tessdata"
set "LANG_FILE=spa.traineddata"
set "DEST_FILE=!TESSDATA_PATH!\!LANG_FILE!"

if not exist "!TESSDATA_PATH!" (
    echo [ERROR] No se encontro la carpeta: !TESSDATA_PATH!
    echo Es posible que Tesseract no se haya instalado correctamente.
    pause
    exit /b 1
)

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

:: Verificación final
echo.
echo === Verificando instalación ===
where tesseract
tesseract --version

echo.
echo === COMPLETADO ===
pause
