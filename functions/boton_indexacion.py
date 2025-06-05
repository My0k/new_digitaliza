import os
import re
import random
import string
import hashlib
import time
import logging
import subprocess
import PyPDF2
import glob
import csv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_folder_name():
    """Genera un nombre único para una carpeta con prefijo y número correlativo."""
    base_dir = 'proceso/carpetas'
    os.makedirs(base_dir, exist_ok=True)
    
    # Obtener todas las carpetas existentes
    existing_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    print(f"Carpetas existentes: {existing_folders}")
    
    # Extraer números correlativos usando expresión regular
    import re
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
    import hashlib
    import time
    timestamp = str(time.time())
    prefix = hashlib.md5(timestamp.encode()).hexdigest()[:6].upper()
    print(f"Prefijo generado: {prefix}")
    
    # Formatear el número correlativo con ceros a la izquierda (3 dígitos)
    formatted_number = f"{next_number:03d}"  # 3 dígitos, no 4
    
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

def extract_project_code_from_ocr(folder_name):
    """
    Extrae el código de proyecto del PDF OCR usando una expresión regular.
    
    Args:
        folder_name (str): Nombre de la carpeta
        
    Returns:
        dict: Resultado de la operación con el código encontrado o un error
    """
    try:
        # Lista de posibles ubicaciones para la carpeta ocr_generado
        possible_ocr_dirs = [
            "ocr_generado",
            "proceso/ocr_generado",
            "../ocr_generado",
            "./ocr_generado",
            os.path.join(os.getcwd(), "ocr_generado"),
            os.path.join(os.getcwd(), "proceso", "ocr_generado")
        ]
        
        # Encontrar la carpeta ocr_generado
        ocr_dir = None
        for dir_path in possible_ocr_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                ocr_dir = dir_path
                logger.info(f"Carpeta ocr_generado encontrada en: {ocr_dir}")
                break
        
        if not ocr_dir:
            logger.error("No se pudo encontrar la carpeta ocr_generado en ninguna ubicación conocida")
            # Listar el directorio actual para diagnóstico
            logger.info(f"Directorio actual: {os.getcwd()}")
            logger.info(f"Contenido del directorio: {os.listdir('.')}")
            return {
                'success': False,
                'error': "No se pudo encontrar la carpeta ocr_generado"
            }
        
        # Listar todos los archivos en ocr_generado para diagnóstico
        pdf_files = [f for f in os.listdir(ocr_dir) if f.endswith('.pdf')]
        logger.info(f"Archivos PDF en carpeta {ocr_dir}: {len(pdf_files)}")
        logger.info(f"Lista de PDFs: {pdf_files}")
        
        # Verificar si existe el PDF específico
        pdf_path = os.path.join(ocr_dir, f"{folder_name}.pdf")
        if not os.path.exists(pdf_path):
            # Intentar buscar en otras ubicaciones
            alt_pdf_path = os.path.join("pdf_procesado", f"{folder_name}.pdf")
            if os.path.exists(alt_pdf_path):
                pdf_path = alt_pdf_path
            else:
                logger.warning(f"No se encontró el archivo PDF para la carpeta {folder_name}")
                return {
                    'success': False,
                    'error': f"No se encontró el archivo PDF con OCR para la carpeta {folder_name}"
                }
        
        logger.info(f"Procesando PDF: {pdf_path}")
        
        # Abrir el PDF y extraer el texto
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                logger.info(f"PDF abierto correctamente. Páginas: {len(reader.pages)}")
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    # Tratar problemas de codificación explícitamente
                    if page_text:
                        try:
                            # Si hay caracteres que no son UTF-8, intenta decodificar correctamente
                            if not isinstance(page_text, str):
                                page_text = page_text.decode('utf-8', errors='ignore')
                        except (UnicodeDecodeError, AttributeError):
                            # Si hay un error, usa una versión con caracteres problemáticos ignorados
                            page_text = str(page_text).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    
                    text += page_text if page_text else ""
                    logger.info(f"Texto extraído de página {page_num+1}: {page_text[:100] if page_text else 'No se pudo extraer texto'}...")
        except Exception as pdf_error:
            logger.error(f"Error al leer PDF {pdf_path}: {str(pdf_error)}")
            return {
                'success': False,
                'error': f"Error al leer el PDF: {str(pdf_error)}"
            }
        
        # Buscar el código de proyecto con la expresión regular
        pattern = r'\b23\d{2}[A-Z]{1,2}\d{4}\b'
        logger.info(f"Buscando patrón: {pattern}")
        matches = re.findall(pattern, text)
        
        if matches:
            # Devolver el primer código encontrado
            logger.info(f"Código de proyecto encontrado en {pdf_path}: {matches[0]}")
            return {
                'success': True,
                'project_code': matches[0],
                'message': f"Código de proyecto encontrado: {matches[0]}"
            }
        else:
            logger.warning(f"No se encontró código de proyecto en {pdf_path}")
            # Mostrar un fragmento del texto extraído para diagnóstico
            text_sample = text[:200] + "..." if len(text) > 200 else text
            logger.info(f"Muestra del texto extraído: {text_sample}")
            return {
                'success': False,
                'error': "No se encontró ningún código de proyecto en el documento"
            }
    
    except Exception as e:
        logger.error(f"Error al extraer código de proyecto: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        
        return {
            'success': False,
            'error': str(e),
            'traceback': error_trace,
            'message': f"Error al procesar el PDF: {str(e)}"
        }
