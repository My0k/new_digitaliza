@echo off
setlocal enabledelayedexpansion

set PYTHON_PATH=C:\Users\UCT\AppData\Local\Programs\Python\Python312\python.exe
set VENV_DIR=venv
set PORT=5000

echo === Cerrando procesos en el puerto %PORT% ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do (
    echo Terminando proceso con PID: %%a
    taskkill /F /PID %%a 2>nul
)

echo === Verificando entorno virtual ===
if not exist %VENV_DIR%\Scripts\activate (
    echo Creando entorno virtual...
    "%PYTHON_PATH%" -m venv %VENV_DIR%
) else (
    echo Entorno virtual ya existe.
)

echo === Activando entorno virtual ===
call %VENV_DIR%\Scripts\activate

echo === Instalando requisitos ===
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo Archivo requirements.txt no encontrado.
    echo Instalando Flask...
    pip install flask
)

echo === Iniciando aplicación Flask ===
start "Flask App" cmd /c "%VENV_DIR%\Scripts\python.exe app.py"

echo === Esperando a que la aplicación inicie ===
timeout /t 3 /nobreak > nul

echo === Abriendo navegador ===
start http://localhost:%PORT%

echo === Aplicación iniciada ===
echo Para detener la aplicación, cierre la ventana de comandos o presione Ctrl+C
