import os
import glob
import shutil
import logging
import hashlib
import time
import re
import csv

# Configurar logging
logger = logging.getLogger(__name__)

def generate_folder_name():
    """Genera un nombre único para una carpeta con prefijo y número correlativo."""
    base_dir = 'proceso/carpetas'
    os.makedirs(base_dir, exist_ok=True)
    
    # Obtener todas las carpetas existentes
    existing_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    print(f"Carpetas existentes: {existing_folders}")
    
    # Extraer números correlativos usando expresión regular
    pattern = r'_(\d+)$'  # Busca _XXX al final del nombre
    correlative_numbers = []
    
    for folder in existing_folders:
        match = re.search(pattern, folder)
        if match:
            try:
                number = int(match.group(1))
                correlative_numbers.append(number)
                print(f"Carpeta {folder} tiene número correlativo: {number}")
            except ValueError:
                pass
    
    # Determinar el siguiente número correlativo
    next_number = 1  # Valor predeterminado si no hay carpetas
    if correlative_numbers:
        next_number = max(correlative_numbers) + 1
        print(f"Números correlativos encontrados: {correlative_numbers}")
        print(f"Máximo número correlativo: {max(correlative_numbers)}")
        print(f"Siguiente número a usar: {next_number}")
    else:
        print("No se encontraron números correlativos. Usando número inicial: 1")
    
    # Generar un prefijo único (ejemplo: usando hash MD5 de timestamp)
    timestamp = str(time.time())
    prefix = hashlib.md5(timestamp.encode()).hexdigest()[:6].upper()
    print(f"Prefijo generado: {prefix}")
    
    # Formatear el número correlativo con ceros a la izquierda (3 dígitos)
    formatted_number = f"{next_number:03d}"
    
    # Combinar para crear el nombre de carpeta
    folder_name = f"{prefix}_{formatted_number}"
    print(f"Nombre de carpeta generado: {folder_name}")
    
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
        
        # Registrar la nueva carpeta en carpetas.csv
        try:
            carpetas_path = 'carpetas.csv'
            
            # Verificar si el archivo existe
            if not os.path.exists(carpetas_path):
                # Crear el archivo con encabezados si no existe
                with open(carpetas_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['carpeta_indexada', 'ocr_generado'])
            
            # Leer el archivo existente
            rows = []
            folder_exists = False
            
            with open(carpetas_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
                reader = csv.reader(file)
                header = next(reader)  # Leer encabezados
                
                # Verificar columnas necesarias
                if 'ocr_generado' not in header:
                    # Añadir la columna si no existe
                    header.append('ocr_generado')
                
                rows.append(header)
                
                # Leer filas existentes y verificar si la carpeta ya está registrada
                for row in reader:
                    if len(row) > 1 and row[1] == folder_name:
                        folder_exists = True
                    rows.append(row)
            
            # Añadir la nueva carpeta si no existe
            if not folder_exists:
                # Añadir fila con la nueva carpeta (columna carpeta_indexada vacía)
                new_row = ['', folder_name]
                rows.append(new_row)
                
                # Escribir cambios
                with open(carpetas_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
            
            logger.info(f"Carpeta {folder_name} registrada en carpetas.csv")
            
        except Exception as csv_err:
            logger.error(f"Error al actualizar carpetas.csv: {str(csv_err)}")
            # Continuar a pesar del error con el CSV
        
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

def move_images_to_folder(folder_path, source_folder='input'):
    """
    Mueve todas las imágenes de la carpeta de entrada a la carpeta especificada.
    
    Args:
        folder_path (str): Ruta a la carpeta de destino
        source_folder (str): Carpeta de origen (por defecto 'input')
        
    Returns:
        int: Número de archivos movidos
    """
    try:
        # Verificar que hay imágenes para mover
        images = glob.glob(os.path.join(source_folder, '*.jpg')) + glob.glob(os.path.join(source_folder, '*.jpeg'))
        if not images:
            logger.info("No hay imágenes para mover")
            return 0
        
        # Mover las imágenes a la carpeta destino
        moved_count = 0
        for img_path in images:
            filename = os.path.basename(img_path)
            dest_path = os.path.join(folder_path, filename)
            shutil.move(img_path, dest_path)
            moved_count += 1
            logger.debug(f"Movida imagen {img_path} a {dest_path}")
        
        logger.info(f"Se movieron {moved_count} imágenes a {folder_path}")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error al mover imágenes a {folder_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
