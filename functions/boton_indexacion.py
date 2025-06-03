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

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_folder_name():
    """
    Genera un nombre único para una carpeta usando hash MD5 y contador.
    """
    # Generar prefijo único con hash MD5 de timestamp + random
    timestamp = str(time.time())
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    hash_input = timestamp + random_str
    hash_prefix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # Encontrar el número más alto actual
    base_dir = 'proceso/carpetas'
    os.makedirs(base_dir, exist_ok=True)
    
    # Buscar carpetas con patrón similar
    existing_folders = glob.glob(os.path.join(base_dir, hash_prefix + "_*"))
    
    # Determinar el siguiente número
    if existing_folders:
        # Extraer números de las carpetas existentes
        numbers = []
        for folder in existing_folders:
            folder_name = os.path.basename(folder)
            parts = folder_name.split('_')
            if len(parts) > 1 and parts[1].isdigit():
                numbers.append(int(parts[1]))
        
        # Usar el siguiente número después del máximo
        next_num = max(numbers) + 1 if numbers else 1
    else:
        next_num = 1
    
    # Formatear el número con ceros a la izquierda
    folder_name = f"{hash_prefix}_{next_num:04d}"
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
                    text += page_text
                    logger.info(f"Texto extraído de página {page_num+1}: {page_text[:100]}...")
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
