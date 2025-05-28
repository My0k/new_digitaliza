@echo off
setlocal

echo ============================================
echo Instalador de ocrmypdf para Windows
echo ============================================

:: Verifica Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no esta instalado o no esta en PATH. Instala Python primero desde https://www.python.org
    pause
    exit /b 1
)

:: Verifica pip
where pip >nul 2>&1
if errorlevel 1 (
    echo ❌ pip no esta disponible. Asegurate de haber instalado Python con pip.
    pause
    exit /b 1
)

:: Instala ocrmypdf
echo Instalando ocrmypdf con pip...
pip install ocrmypdf

:: Instala Tesseract desde el instalador de UB Mannheim
echo Descargando instalador de Tesseract (UB Mannheim)...
curl -L -o tesseract-installer.exe https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1.20230401/tesseract-ocr-w64-setup-5.3.1.20230401.exe

echo Ejecutando instalador de Tesseract...
start /wait tesseract-installer.exe

:: Verifica Tesseract
where tesseract >nul 2>&1
if errorlevel 1 (
    echo ❌ Tesseract no se instalo correctamente. Asegurate de marcar "Add to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: Instala Ghostscript
echo Descargando Ghostscript...
curl -L -o gssetup.exe https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10010/gs10010w64.exe

echo Ejecutando instalador de Ghostscript...
start /wait gssetup.exe

:: Verifica Ghostscript
where gswin64c >nul 2>&1
if errorlevel 1 (
    echo ❌ Ghostscript no se instalo correctamente.
    pause
    exit /b 1
)

:: Verifica ocrmypdf
where ocrmypdf >nul 2>&1
if errorlevel 1 (
    echo ❌ ocrmypdf no esta disponible en el PATH. Intenta reiniciar la terminal o usar python -m ocrmypdf
    pause
    exit /b 1
)

echo ✅ Instalacion completada exitosamente.
ocrmypdf --version

pause
endlocal
