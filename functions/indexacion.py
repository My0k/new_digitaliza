import hashlib
import time
import os
import logging
import glob
import re

logger = logging.getLogger(__name__)

def generate_folder_name():
    """Genera un nombre de carpeta único con formato hash_NNNN."""
    # Generar el hash MD5 basado en el timestamp actual
    timestamp = str(time.time())
    hash_obj = hashlib.md5(timestamp.encode())
    hash_str = hash_obj.hexdigest()[:8]  # Usamos los primeros 8 caracteres del hash
    
    # Buscar las carpetas existentes para determinar el próximo número correlativo
    base_dir = 'proceso/carpetas'
    os.makedirs(base_dir, exist_ok=True)
    
    # Buscar carpetas que coincidan con el patrón hash_NNNN
    existing_folders = glob.glob(os.path.join(base_dir, "*_????"))
    
    # Extraer los números correlativos de las carpetas existentes
    correlative_numbers = []
    pattern = re.compile(r'.*_(\d{4})$')
    
    for folder in existing_folders:
        match = pattern.match(folder)
        if match:
            correlative_numbers.append(int(match.group(1)))
    
    # Determinar el próximo número correlativo
    next_number = 1
    if correlative_numbers:
        next_number = max(correlative_numbers) + 1
    
    # Formatear el número correlativo con ceros a la izquierda (0001, 0002, etc.)
    correlative_str = f"{next_number:04d}"
    
    # Combinar el hash y el número correlativo
    folder_name = f"{hash_str}_{correlative_str}"
    
    return folder_name

def create_new_folder():
    """Crea una nueva carpeta con un nombre único basado en hash MD5 y número correlativo."""
    try:
        # Generar nombre de carpeta único
        folder_name = generate_folder_name()
        
        # Definir la ruta completa de la carpeta
        base_dir = 'proceso/carpetas'
        os.makedirs(base_dir, exist_ok=True)
        folder_path = os.path.join(base_dir, folder_name)
        
        # Crear la carpeta
        os.makedirs(folder_path, exist_ok=True)
        
        return {
            'success': True,
            'folder_name': folder_name,
            'folder_path': folder_path,
            'message': f'Carpeta creada: {folder_name}'
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        return {
            'success': False,
            'error': str(e),
            'traceback': error_trace,
            'message': f'Error al crear carpeta: {str(e)}'
        }
