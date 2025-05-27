@echo off
echo === Iniciando aplicacion Flask ===

rem Definir ruta del entorno virtual
set VENV_DIR=%CD%\venv

rem Activar el entorno virtual
echo === Activando entorno virtual ===
call "%VENV_DIR%\Scripts\activate.bat"

rem Configurar Tesseract
echo === Configurando Tesseract ===
set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
set PATH=%PATH%;C:\Program Files\Tesseract-OCR

rem Iniciar la aplicación Flask
echo === Iniciando Flask ===
python app.py

rem En caso de error, mantener la ventana abierta
if %errorlevel% neq 0 (
    echo.
    echo === Error al iniciar la aplicacion ===
    pause
) 