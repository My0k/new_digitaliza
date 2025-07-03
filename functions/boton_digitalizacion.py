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

def generate_folder_name(lote_prefix='LOTE1'):
    """Genera un nombre único para una carpeta con prefijo y número correlativo."""
    base_dir = 'proceso/carpetas'
    os.makedirs(base_dir, exist_ok=True)
    
    # Obtener todas las carpetas existentes
    existing_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    print(f"Carpetas existentes: {existing_folders}")
    
    # Extraer los 3 dígitos a la izquierda de cada nombre de carpeta
    correlative_numbers = []
    
    for folder in existing_folders:
        # Buscar los 3 dígitos al inicio del nombre
        match = re.match(r'^(\d{3})_', folder)
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
    hash_prefix = hashlib.md5(timestamp.encode()).hexdigest()[:6].upper()
    
    # Sanitizar el prefijo del lote (eliminar caracteres no permitidos)
    lote_prefix = re.sub(r'[^\w\-]', '', lote_prefix)
    
    # Formatear el número correlativo con ceros a la izquierda (3 dígitos)
    formatted_number = f"{next_number:03d}"
    
    # Combinar para crear el nombre de carpeta: CORRELATIVO_LOTE_HASH
    folder_name = f"{formatted_number}_{lote_prefix}_{hash_prefix}"
    print(f"Nombre de carpeta generado: {folder_name}")
    
    return folder_name

def create_new_folder(lote_prefix='LOTE1'):
    """Crea una nueva carpeta con un nombre único basado en el prefijo del lote, hash MD5 y número correlativo."""
    try:
        # Generar nombre de carpeta único
        folder_name = generate_folder_name(lote_prefix)
        
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
                    writer.writerow(['carpeta_indexada', 'ocr_generado', 'lote_identifier'])
            
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
                
                if 'lote_identifier' not in header:
                    # Añadir la columna de identificador de lote si no existe
                    header.append('lote_identifier')
                
                rows.append(header)
                
                # Leer filas existentes y verificar si la carpeta ya está registrada
                for row in reader:
                    if len(row) > 1 and row[1] == folder_name:
                        folder_exists = True
                    
                    # Asegurar que la fila tiene suficientes columnas
                    while len(row) < len(header):
                        row.append('')
                    
                    rows.append(row)
            
            # Añadir la nueva carpeta si no existe
            if not folder_exists:
                # Añadir fila con la nueva carpeta
                new_row = ['', folder_name, lote_prefix]
                
                # Asegurar que la fila tiene suficientes columnas
                while len(new_row) < len(header):
                    new_row.append('')
                
                rows.append(new_row)
                
                # Escribir cambios
                with open(carpetas_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
            
            logger.info(f"Carpeta {folder_name} registrada en carpetas.csv con identificador de lote: {lote_prefix}")
            
        except Exception as csv_err:
            logger.error(f"Error al actualizar carpetas.csv: {str(csv_err)}")
            # Continuar a pesar del error con el CSV
        
        return {
            'success': True,
            'folder_name': folder_name,
            'folder_path': folder_path,
            'lote_identifier': lote_prefix,
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
    Mueve todas las imágenes de la carpeta de entrada a la carpeta especificada,
    renombrándolas como 001.jpg, 002.jpg, etc. según el orden en orden.csv.
    
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
        
        logger.info(f"DEBUG: Encontradas {len(images)} imágenes en {source_folder}")
        
        # Crear un diccionario con los nombres de archivos como claves
        image_dict = {}
        for img_path in images:
            filename = os.path.basename(img_path)
            image_dict[filename] = img_path
            logger.info(f"DEBUG: Imagen disponible en input: {filename}")
        
        # Leer el archivo orden.csv para determinar el orden de las imágenes
        csv_path = 'orden.csv'
        ordered_filenames = []
        
        if os.path.exists(csv_path):
            logger.info(f"DEBUG: Leyendo orden desde {csv_path}")
            try:
                # Imprimir el contenido completo del CSV para depuración
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    csv_content = csvfile.read()
                    logger.info(f"DEBUG: Contenido completo del CSV:\n{csv_content}")
                
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)  # Leer encabezados
                    logger.info(f"DEBUG: Encabezados del CSV: {headers}")
                    
                    # Leer todas las filas en una lista para depuración
                    all_rows = list(reader)
                    logger.info(f"DEBUG: Leídas {len(all_rows)} filas del CSV")
                    
                    # Crear una lista de tuplas (nombre_archivo, posicion)
                    file_positions = []
                    for row in all_rows:
                        logger.info(f"DEBUG: Procesando fila CSV: {row}")
                        if len(row) >= 2 and row[0].strip():
                            nombre_img = row[0].strip()
                            try:
                                posicion = int(row[1]) if row[1].strip() else 999999
                            except (ValueError, TypeError):
                                logger.warning(f"DEBUG: Valor de posición inválido: {row[1]}")
                                posicion = 999999
                            
                            file_positions.append((nombre_img, posicion))
                            logger.info(f"DEBUG: Añadido a file_positions: {nombre_img}, posición {posicion}")
                            
                            # Verificar si la imagen existe en input
                            if nombre_img in image_dict:
                                logger.info(f"DEBUG: Imagen {nombre_img} encontrada en input")
                            else:
                                logger.warning(f"DEBUG: Imagen {nombre_img} NO encontrada en input")
                    
                    # Ordenar por posición
                    file_positions.sort(key=lambda x: x[1])
                    logger.info(f"DEBUG: Ordenadas {len(file_positions)} imágenes por posición")
                    
                    # Extraer solo los nombres de archivo en el orden correcto
                    ordered_filenames = [filename for filename, _ in file_positions]
                    logger.info(f"DEBUG: Orden final de archivos: {ordered_filenames}")
            except Exception as e:
                logger.error(f"Error al leer orden.csv: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("DEBUG: No se encontró el archivo orden.csv")
        
        # Si no hay orden definido o hubo un error, usar todos los archivos sin orden específico
        if not ordered_filenames:
            logger.warning("DEBUG: No se pudo determinar el orden desde CSV, usando archivos disponibles")
            ordered_filenames = list(image_dict.keys())
        
        logger.info(f"DEBUG: Procesando {len(ordered_filenames)} archivos en orden definido")
        
        # Mover y renombrar las imágenes a la carpeta destino
        moved_count = 0
        new_index = 1  # Contador para los nuevos nombres de archivo
        
        # Primero procesar los archivos que están en el orden definido
        for filename in ordered_filenames:
            if filename in image_dict:
                img_path = image_dict[filename]
                logger.info(f"DEBUG: Procesando archivo en orden: {filename}, ruta: {img_path}")
                
                # Determinar la extensión original
                _, ext = os.path.splitext(img_path)
                if not ext:  # Si no tiene extensión, asumir .jpg
                    ext = '.jpg'
                else:
                    ext = ext.lower()  # Normalizar a minúsculas
                
                # Crear nuevo nombre con formato 001.jpg
                new_filename = f"{new_index:03d}{ext}"
                dest_path = os.path.join(folder_path, new_filename)
                
                logger.info(f"DEBUG: Renombrando {filename} → {new_filename}")
                
                try:
                    # Copiar la imagen con el nuevo nombre
                    shutil.copy2(img_path, dest_path)
                    logger.info(f"DEBUG: Imagen copiada correctamente a {dest_path}")
                    
                    # Eliminar la imagen original
                    os.remove(img_path)
                    logger.info(f"DEBUG: Imagen original eliminada: {img_path}")
                    
                    logger.info(f"RENOMBRADO: {filename} → {new_filename}")
                    moved_count += 1
                    new_index += 1
                    
                    # Eliminar del diccionario para no procesarlo de nuevo
                    del image_dict[filename]
                except Exception as copy_err:
                    logger.error(f"Error al copiar/eliminar imagen {filename}: {str(copy_err)}")
        
        # Procesar cualquier archivo restante que no estaba en el orden definido
        remaining_files = list(image_dict.keys())
        logger.info(f"DEBUG: Procesando {len(remaining_files)} archivos restantes")
        
        for filename, img_path in image_dict.items():
            logger.info(f"DEBUG: Procesando archivo restante: {filename}, ruta: {img_path}")
            
            # Determinar la extensión original
            _, ext = os.path.splitext(img_path)
            if not ext:  # Si no tiene extensión, asumir .jpg
                ext = '.jpg'
            else:
                ext = ext.lower()  # Normalizar a minúsculas
            
            # Crear nuevo nombre con formato 001.jpg
            new_filename = f"{new_index:03d}{ext}"
            dest_path = os.path.join(folder_path, new_filename)
            
            logger.info(f"DEBUG: Renombrando {filename} → {new_filename}")
            
            try:
                # Copiar la imagen con el nuevo nombre
                shutil.copy2(img_path, dest_path)
                logger.info(f"DEBUG: Imagen copiada correctamente a {dest_path}")
                
                # Eliminar la imagen original
                os.remove(img_path)
                logger.info(f"DEBUG: Imagen original eliminada: {img_path}")
                
                logger.info(f"RENOMBRADO (adicional): {filename} → {new_filename}")
                moved_count += 1
                new_index += 1
            except Exception as copy_err:
                logger.error(f"Error al copiar/eliminar imagen restante {filename}: {str(copy_err)}")
        
        # Verificar el resultado final
        dest_images = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
        logger.info(f"DEBUG: Resultado final - {len(dest_images)} imágenes en carpeta destino")
        for img in sorted(dest_images)[:10]:
            logger.info(f"DEBUG: Imagen en destino: {os.path.basename(img)}")
        
        logger.info(f"TOTAL: Se movieron y renombraron {moved_count} imágenes a {folder_path}")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error al mover imágenes a {folder_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
