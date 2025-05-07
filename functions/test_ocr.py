import os
import sys
import logging
from PIL import Image
import subprocess
import re
import json

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def check_tesseract_installed():
    """Verifica si Tesseract OCR está instalado en el sistema."""
    try:
        # Intentar ejecutar tesseract para verificar si está instalado
        result = subprocess.run(['tesseract', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        return True
    except FileNotFoundError:
        return False

def extract_student_data(text):
    """
    Extrae datos del estudiante del texto OCR.
    Retorna un diccionario con los datos extraídos.
    """
    data = {
        'nombre': '',
        'rut': '',
        'carrera': '',
        'domicilio': ''
    }
    
    # Patrones para buscar los datos
    nombre_pattern = r"NOMBRE DEUDOR\(A\)\s*:\s*([^\n]+)"
    rut_pattern = r"CEDULA NACIONAL DE IDENTIDAD\s*:\s*([0-9.-]+)"
    carrera_pattern = r"CARRERA\s*:\s*([^\n]+)"
    domicilio_pattern = r"DOMICILIO\s*:\s*([^\n]+)"
    
    # Buscar nombre
    nombre_match = re.search(nombre_pattern, text)
    if nombre_match:
        data['nombre'] = nombre_match.group(1).strip()
    
    # Buscar RUT
    rut_match = re.search(rut_pattern, text)
    if rut_match:
        data['rut'] = rut_match.group(1).strip()
    
    # Buscar carrera
    carrera_match = re.search(carrera_pattern, text)
    if carrera_match:
        # Limpiar el texto de la carrera (puede contener texto adicional)
        carrera_text = carrera_match.group(1).strip()
        # Si hay "pa" u otros textos extraños al final, eliminarlos
        if " pa" in carrera_text:
            carrera_text = carrera_text.split(" pa")[0].strip()
        data['carrera'] = carrera_text
    
    # Buscar domicilio
    domicilio_match = re.search(domicilio_pattern, text)
    if domicilio_match:
        data['domicilio'] = domicilio_match.group(1).strip()
    
    return data

def perform_ocr():
    """
    Realiza OCR en las imágenes de la carpeta input y guarda el resultado en output.txt
    Además, extrae datos del estudiante y los guarda en un archivo JSON.
    """
    try:
        # Verificar si Tesseract está instalado
        if not check_tesseract_installed():
            logger.error("Tesseract OCR no está instalado en el sistema.")
            logger.error("Por favor, instala Tesseract OCR con el siguiente comando:")
            logger.error("sudo apt-get install tesseract-ocr tesseract-ocr-spa")
            
            # Crear un archivo de salida con instrucciones
            output_file = 'output.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== ERROR: TESSERACT OCR NO INSTALADO ===\n\n")
                f.write("Para instalar Tesseract OCR en Ubuntu/Debian, ejecuta:\n")
                f.write("sudo apt-get install tesseract-ocr tesseract-ocr-spa\n\n")
                f.write("Después de instalar, vuelve a intentar el OCR.\n")
            
            return False
        
        # Importar pytesseract solo si Tesseract está instalado
        import pytesseract
        
        # Determinar la ruta base del proyecto
        if os.path.exists('app.py'):
            # Estamos en la raíz del proyecto
            base_dir = os.path.abspath('.')
        else:
            # Estamos en otro directorio, probablemente en functions/
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # Rutas absolutas
        input_dir = os.path.join(base_dir, 'input')
        output_file = os.path.join(base_dir, 'output.txt')
        student_data_file = os.path.join(base_dir, 'student_data.json')
        
        logger.info(f"Directorio base: {base_dir}")
        logger.info(f"Directorio de entrada: {input_dir}")
        logger.info(f"Archivo de salida: {output_file}")
        
        # Verificar que el directorio de entrada existe
        if not os.path.exists(input_dir):
            logger.error(f"Error: El directorio de entrada {input_dir} no existe.")
            return False
        
        # Obtener las imágenes más recientes
        image_files = []
        for file in os.listdir(input_dir):
            if file.lower().endswith(('.jpg', '.jpeg')):
                image_files.append(os.path.join(input_dir, file))
        
        # Ordenar por fecha de modificación (más reciente primero)
        image_files.sort(key=os.path.getmtime, reverse=True)
        
        # Tomar las dos primeras imágenes (si existen)
        image_files = image_files[:2]
        
        if not image_files:
            logger.error("No se encontraron imágenes para procesar.")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== ERROR: NO HAY IMÁGENES PARA PROCESAR ===\n\n")
                f.write("No se encontraron imágenes JPG en la carpeta de entrada.\n")
                f.write("Por favor, asegúrate de que hay imágenes en la carpeta 'input'.\n")
            return False
        
        # Variable para almacenar todos los textos OCR
        all_ocr_text = ""
        extracted_data = {}
        
        # Realizar OCR en cada imagen y guardar el resultado
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== RESULTADOS DE OCR ===\n\n")
            
            for i, image_path in enumerate(image_files):
                try:
                    logger.info(f"Procesando imagen: {image_path}")
                    
                    # Determinar el tipo de documento basado en el orden
                    doc_type = "PAGARÉ" if i == 0 else "FIRMA"
                    
                    # Abrir la imagen
                    with Image.open(image_path) as img:
                        # Realizar OCR
                        text = pytesseract.image_to_string(img, lang='spa')
                        
                        # Acumular el texto para análisis posterior
                        all_ocr_text += text
                        
                        # Escribir resultados en el archivo
                        f.write(f"=== DOCUMENTO {i+1}: {doc_type} ===\n")
                        f.write(f"Archivo: {os.path.basename(image_path)}\n")
                        f.write("Texto extraído:\n")
                        f.write(text)
                        f.write("\n\n" + "="*50 + "\n\n")
                        
                        logger.info(f"OCR completado para {os.path.basename(image_path)}")
                
                except Exception as e:
                    logger.error(f"Error al procesar la imagen {image_path}: {str(e)}")
                    f.write(f"Error al procesar la imagen {os.path.basename(image_path)}: {str(e)}\n\n")
        
        # Extraer datos del estudiante del texto OCR
        extracted_data = extract_student_data(all_ocr_text)
        
        # Guardar los datos extraídos en un archivo JSON
        with open(student_data_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Proceso de OCR completado. Resultados guardados en {output_file}")
        logger.info(f"Datos del estudiante extraídos: {extracted_data}")
        logger.info(f"Datos del estudiante guardados en {student_data_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error general en el proceso de OCR: {str(e)}")
        
        # Crear un archivo de salida con el error
        output_file = 'output.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== ERROR EN EL PROCESO DE OCR ===\n\n")
            f.write(f"Error: {str(e)}\n")
        
        return False

if __name__ == "__main__":
    success = perform_ocr()
    sys.exit(0 if success else 1)
