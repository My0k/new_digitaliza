import shutil
import os
import sys

# Obtener la ruta base del proyecto (donde se ejecuta app.py)
# Si el script se ejecuta directamente, la ruta base es el directorio actual
# Si se ejecuta desde otro directorio, necesitamos ajustar la ruta
if os.path.exists('app.py'):
    # Estamos en la raíz del proyecto
    base_dir = os.path.abspath('.')
else:
    # Estamos en otro directorio, probablemente en functions/
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Rutas absolutas
src_dir = os.path.join(base_dir, 'test')
dest_dir = os.path.join(base_dir, 'input')
archivos = ["pagina_1.jpg", "pagina_2.jpg"]

print(f"Directorio base: {base_dir}")
print(f"Directorio fuente: {src_dir}")
print(f"Directorio destino: {dest_dir}")

# Verificar que el directorio fuente existe
if not os.path.exists(src_dir):
    print(f"Error: El directorio fuente {src_dir} no existe.")
    sys.exit(1)

# Crear carpeta destino si no existe
os.makedirs(dest_dir, exist_ok=True)
print(f"Carpeta destino verificada: {dest_dir}")

# Copiar archivos
archivos_copiados = 0
for archivo in archivos:
    src_path = os.path.join(src_dir, archivo)
    dest_path = os.path.join(dest_dir, archivo)
    
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"Copiado: {archivo} -> {dest_path}")
        archivos_copiados += 1
    else:
        print(f"Archivo no encontrado: {src_path}")

print(f"Proceso completado. {archivos_copiados} archivos copiados.")
