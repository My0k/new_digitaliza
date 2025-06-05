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

:: Verifica si se está ejecutando como administrador
net session >nul 2>&1
if errorlevel 1 (
    echo ❌ Este script requiere privilegios de administrador.
    echo Por favor, ejecuta el script como administrador.
    pause
    exit /b 1
)

:: Instala Chocolatey si no está instalado
where choco >nul 2>&1
if errorlevel 1 (
    echo Instalando Chocolatey...
    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    
    if errorlevel 1 (
        echo ❌ Error al instalar Chocolatey.
        pause
        exit /b 1
    ) else (
        echo ✅ Chocolatey instalado correctamente.
    )
) else (
    echo ✅ Chocolatey ya está instalado.
)

:: Verifica Python (asegurando versión 64 bits)
where python >nul 2>&1
if errorlevel 1 (
    echo Python no está instalado. Instalando Python 64-bit con Chocolatey...
    choco install python -y --version=3.10.0
    
    if errorlevel 1 (
        echo ❌ Error al instalar Python.
        pause
        exit /b 1
    )
    refreshenv
) else (
    echo ✅ Python ya está instalado.
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

:: Instala Tesseract con Chocolatey
echo Instalando Tesseract OCR 64-bit con Chocolatey...
choco install tesseract -y

:: Verifica Tesseract
where tesseract >nul 2>&1
if errorlevel 1 (
    echo ❌ Tesseract no se instaló correctamente.
    pause
    exit /b 1
) else (
    echo ✅ Tesseract instalado correctamente.
)

:: Instala requirements.txt si existe
if exist requirements.txt (
    echo Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
) else (
    echo El archivo requirements.txt no se encuentra, continuando con la instalación...
)

:: Instala pytesseract
echo Instalando pytesseract...
pip install pytesseract

:: Instala ocrmypdf
echo Instalando ocrmypdf con pip...
pip install ocrmypdf

:: Verifica ocrmypdf
where ocrmypdf >nul 2>&1
if errorlevel 1 (
    echo ❌ ocrmypdf no está disponible en el PATH. Intenta reiniciar la terminal o usar python -m ocrmypdf
    pause
    exit /b 1
) else (
    echo ✅ ocrmypdf instalado correctamente.
)

:: Verifica pytesseract
python -c "import pytesseract" >nul 2>&1
if errorlevel 1 (
    echo ❌ pytesseract no se instaló correctamente.
    pause
    exit /b 1
) else (
    echo ✅ pytesseract instalado correctamente.
)

echo ============================================
echo ✅ Instalación completada exitosamente.
echo ============================================
echo Versión de ocrmypdf:
ocrmypdf --version

pause
endlocal
