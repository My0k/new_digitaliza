@echo off
setlocal

echo ============================================
echo Instalador de ocrmypdf para Windows (64-bit)
echo ============================================

:: Verifica que sea un sistema de 64 bits
reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT
if %OS%==32BIT (
    echo ❌ Este instalador solo es compatible con sistemas de 64 bits.
    pause
    exit /b 1
)

:: Verifica Python (asegurando versión 64 bits)
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no esta instalado o no esta en PATH. Instala Python 64-bit desde https://www.python.org
    pause
    exit /b 1
)

:: Verifica si Python es de 64 bits
python -c "import struct; print(struct.calcsize('P') * 8)" > %temp%\pyarch.txt
set /p PYARCH=<%temp%\pyarch.txt
if %PYARCH% NEQ 64 (
    echo ❌ Por favor instala Python de 64 bits. La version actual es de %PYARCH% bits.
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

:: Instala requirements.txt si existe
if exist requirements.txt (
    echo Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
) else (
    echo El archivo requirements.txt no se encuentra, continuando con la instalacion...
)

:: Instala pytesseract
echo Instalando pytesseract...
pip install pytesseract

:: Instala ocrmypdf
echo Instalando ocrmypdf con pip...
pip install ocrmypdf

:: Instala Tesseract 64-bit desde el instalador de UB Mannheim
echo Descargando instalador de Tesseract 64-bit (UB Mannheim)...
curl -L -o tesseract-installer.exe https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1.20230401/tesseract-ocr-w64-setup-5.3.1.20230401.exe

echo Ejecutando instalador de Tesseract 64-bit...
start /wait tesseract-installer.exe

:: Verifica Tesseract
where tesseract >nul 2>&1
if errorlevel 1 (
    echo ❌ Tesseract no se instalo correctamente. Asegurate de marcar "Add to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: Instala Ghostscript 64-bit
echo Descargando Ghostscript 64-bit...
curl -L -o gssetup.exe https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10010/gs10010w64.exe

echo Ejecutando instalador de Ghostscript 64-bit...
start /wait gssetup.exe

:: Verifica Ghostscript 64-bit
where gswin64c >nul 2>&1
if errorlevel 1 (
    echo ❌ Ghostscript 64-bit no se instalo correctamente.
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

:: Verifica pytesseract
python -c "import pytesseract" >nul 2>&1
if errorlevel 1 (
    echo ❌ pytesseract no se instalo correctamente.
    pause
    exit /b 1
) else (
    echo ✅ pytesseract instalado correctamente.
)

echo ✅ Instalacion completada exitosamente.
ocrmypdf --version

pause
endlocal
