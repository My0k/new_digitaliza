import hashlib
import time
import os
import logging

logger = logging.getLogger(__name__)

def generate_folder_name():
    """
    Genera un nombre de carpeta único basado en un hash MD5 del timestamp actual.
    
    Returns:
        str: Nombre de la carpeta (hash MD5 truncado)
    """
    # Obtener timestamp actual con precisión de milisegundos
    timestamp = str(time.time())
    
    # Generar hash MD5 del timestamp
    md5_hash = hashlib.md5(timestamp.encode()).hexdigest()
    
    # Truncar el hash a los primeros 10 caracteres para mantenerlo manejable
    truncated_hash = md5_hash[:10]
    
    return truncated_hash

def create_new_folder():
    """
    Crea una nueva carpeta con un nombre basado en MD5 del timestamp.
    
    Returns:
        dict: Información sobre la carpeta creada (éxito, nombre, ruta)
    """
    try:
        # Generar un nombre único para la carpeta usando MD5 del timestamp
        folder_name = generate_folder_name()
        
        # Crear la ruta completa
        base_dir = 'proceso/carpetas'
        folder_path = os.path.join(base_dir, folder_name)
        
        # Crear la carpeta si no existe
        os.makedirs(folder_path, exist_ok=True)
        
        return {
            'success': True, 
            'folder_name': folder_name,
            'folder_path': folder_path
        }
        
    except Exception as e:
        error_msg = f"Error al crear nueva carpeta: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': error_msg}
