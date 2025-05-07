#!/bin/bash

# Definir colores para la salida
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Iniciando Visor de Documentos ===${NC}"

# Función para matar procesos en el puerto 5000
kill_port() {
    echo -e "${YELLOW}Verificando si el puerto 5000 está en uso...${NC}"
    
    # Buscar procesos usando el puerto 5000
    pid=$(lsof -t -i:5000 2>/dev/null)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Matando proceso(s) en puerto 5000: $pid${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
        echo -e "${GREEN}Puerto 5000 liberado${NC}"
    else
        echo -e "${GREEN}Puerto 5000 está libre${NC}"
    fi
}

# Función para activar el entorno virtual
activate_venv() {
    echo -e "${YELLOW}Verificando entorno virtual...${NC}"
    
    # Verificar si existe el directorio venv
    if [ -d "venv" ]; then
        echo -e "${GREEN}Activando entorno virtual existente${NC}"
        source venv/bin/activate
    else
        echo -e "${YELLOW}Creando nuevo entorno virtual...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        
        echo -e "${YELLOW}Instalando dependencias...${NC}"
        pip install flask pillow werkzeug
        echo -e "${GREEN}Dependencias instaladas${NC}"
    fi
}

# Función para verificar la carpeta input
check_input_folder() {
    echo -e "${YELLOW}Verificando carpeta input...${NC}"
    
    if [ ! -d "input" ]; then
        echo -e "${YELLOW}Creando carpeta input...${NC}"
        mkdir -p input
        echo -e "${GREEN}Carpeta input creada${NC}"
    else
        echo -e "${GREEN}Carpeta input existe${NC}"
    fi
}

# Función para iniciar la aplicación
start_app() {
    echo -e "${GREEN}Iniciando aplicación...${NC}"
    python app.py
}

# Ejecutar funciones
kill_port
activate_venv
check_input_folder
start_app
