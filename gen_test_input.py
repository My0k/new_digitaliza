import shutil
import os

# Rutas
src_dir = "test"
dest_dir = "documentos/input"
archivos = ["pagina_1.jpg", "pagina_2.jpg"]

# Crear carpeta destino si no existe
os.makedirs(dest_dir, exist_ok=True)

# Copiar archivos
for archivo in archivos:
    src_path = os.path.join(src_dir, archivo)
    dest_path = os.path.join(dest_dir, archivo)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"Copiado: {archivo}")
    else:
        print(f"Archivo no encontrado: {archivo}")
