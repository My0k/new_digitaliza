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

def extract_student_data(ocr_text):
    """Extrae información del estudiante desde el texto OCR."""
    print("=== EJECUTANDO VERSIÓN CORREGIDA DEL EXTRACTOR (v2) ===")
    data = {}
    
    # Patrón para RUT: Busca algo como "RUT: 12345678-9" o "12.345.678-9"
    rut_patterns = [
        r'RUT\s*[:-]?\s*(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])',
        r'RUT\s*[:-]?\s*(\d{7,8}-[\dkK])',
        r'(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])',
        r'(\d{7,8}-[\dkK])'
    ]
    
    # Encontrar todos los RUTs en el texto
    all_ruts = []
    for pattern in rut_patterns:
        matches = re.findall(pattern, ocr_text)
        all_ruts.extend(matches)
    
    print(f"Todos los RUTs encontrados: {all_ruts}")
    
    # Filtrar RUTs que comienzan con 7 (institucionales)
    valid_ruts = []
    for rut in all_ruts:
        # Limpiar el RUT para verificar el primer dígito
        clean_rut = rut.replace(".", "").replace("-", "").strip()
        print(f"Evaluando RUT: {rut}, limpio: {clean_rut}")
        if clean_rut and not clean_rut[0] == '7':
            print(f"  - Válido (no comienza con 7)")
            valid_ruts.append(rut)
        else:
            print(f"  - Ignorado (comienza con 7 o está vacío)")
    
    # Usar el primer RUT válido encontrado
    if valid_ruts:
        data['rut'] = valid_ruts[0]
        print(f"RUT válido seleccionado (no institucional): {data['rut']}")
    elif all_ruts:
        print(f"ADVERTENCIA: Solo se encontraron RUTs institucionales. No se asignará ninguno.")
    else:
        print("No se encontraron RUTs en el texto")
    
    # Patrón para folio: Primero buscamos el formato específico "; XXXXXXXXXX" (10 dígitos)
    # Primero buscar el patrón específico de punto y coma
    semicolon_match = re.search(r';\s*(\d{10})', ocr_text)
    if semicolon_match:
        data['folio'] = semicolon_match.group(1)
        print(f"Folio encontrado con patrón '; XXXXXXXXXX': {data['folio']}")
    else:
        # Si no se encuentra, buscar secuencia de 10 dígitos
        ten_digit_match = re.search(r'(?<!\d)(\d{10})(?!\d)', ocr_text)
        if ten_digit_match:
            data['folio'] = ten_digit_match.group(1)
            print(f"Folio encontrado como secuencia de 10 dígitos: {data['folio']}")
        else:
            # Si no hay secuencia de 10 dígitos, buscar otros patrones
            folio_patterns = [
                r';\s*(\d{10})',  # Patrón prioritario: punto y coma seguido de 10 dígitos
                r'[Ff][Oo][Ll][Ii][Oo]\s*[:-]?\s*(\d{10})',
                r'[Nn][Úú][Mm][Ee][Rr][Oo]\s*[:-]?\s*(\d{10})',
                r'[Nn][°º]\s*[:-]?\s*(\d{10})',
                r'[Ff][Oo][Ll][Ii][Oo]\s*[:-]?\s*(\d+)',
                r'[Nn][Úú][Mm][Ee][Rr][Oo]\s*[:-]?\s*(\d+)',
                r'[Nn][°º]\s*[:-]?\s*(\d+)'
            ]
            
            for pattern in folio_patterns:
                matches = re.findall(pattern, ocr_text)
                if matches:
                    data['folio'] = matches[0]
                    print(f"Folio encontrado con patrón alternativo: {data['folio']}")
                    break
    
    print(f"Datos extraídos: {data}")
    
    # Verificación explícita para RUTs institucionales
    if 'rut' in data and data['rut'].replace('.', '').replace('-', '').strip().startswith('7'):
        print(f"CORRECCIÓN FINAL: Eliminando RUT institucional: {data['rut']}")
        del data['rut']
    
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
    # Verificar si se proporcionó una imagen específica como parámetro
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        # Modo de procesamiento de una sola imagen (usado por el endpoint de OCR)
        image_path = sys.argv[1]
        
        # Verificar si Tesseract está instalado
        if not check_tesseract_installed():
            print("Tesseract OCR no está instalado")
            sys.exit(1)
            
        import pytesseract
        
        try:
            # Abrir la imagen y realizar OCR
            with Image.open(image_path) as img:
                ocr_text = pytesseract.image_to_string(img, lang='spa')
                
                # Extraer datos del estudiante
                student_data = extract_student_data(ocr_text)
                
                # Imprimir el texto OCR completo (esto será capturado por stdout)
                print(ocr_text)
                
                sys.exit(0)
        except Exception as e:
            print(f"Error al procesar la imagen: {str(e)}")
            sys.exit(1)
    else:
        # Modo de procesamiento normal (escaneando toda la carpeta)
        success = perform_ocr()
        sys.exit(0 if success else 1)
