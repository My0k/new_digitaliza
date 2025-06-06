import csv
import json
import os
import logging
import base64
import requests
import configparser
import re
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Carga la configuración desde el archivo config.conf"""
    config = configparser.ConfigParser(interpolation=None)
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.conf')
    
    try:
        with open(config_path, 'r') as f:
            # Agregar una sección predeterminada ya que configparser requiere secciones
            file_content = '[DEFAULT]\n' + f.read()
        config.read_string(file_content)
        return config['DEFAULT']
    except Exception as e:
        logger.error(f"Error al cargar la configuración: {e}")
        return None

def sanitize_rut(rut):
    """Sanitiza el formato del RUT para uso en la API"""
    # Eliminar espacios o puntos
    clean_rut = re.sub(r'[.\s]', '', rut)
    # Asegurar que tenga el formato con guion
    if '-' not in clean_rut and len(clean_rut) > 1:
        # Insertar guion antes del último carácter (dígito verificador)
        clean_rut = f"{clean_rut[:-1]}-{clean_rut[-1]}"
    return clean_rut

def generar_pdf_desde_imagenes(rut, folio, input_folder='input'):
    """Genera un PDF con todas las imágenes de la carpeta input"""
    logger.info(f"Generando PDF para RUT: {rut}, Folio: {folio}")
    
    # Crear carpeta para PDFs si no existe
    pdf_folder = 'pdf_procesado'
    os.makedirs(pdf_folder, exist_ok=True)
    
    # Nombre del archivo PDF
    filename = f"{rut}_{folio}.pdf"
    pdf_path = os.path.join(pdf_folder, filename)
    
    # Obtener todas las imágenes de la carpeta input
    image_files = []
    for file in os.listdir(input_folder):
        if file.lower().endswith(('.jpg', '.jpeg')):
            image_files.append(os.path.join(input_folder, file))
    
    if not image_files:
        logger.warning(f"No hay imágenes en la carpeta {input_folder} para generar el PDF")
        return None
    
    logger.info(f"Encontradas {len(image_files)} imágenes para incluir en el PDF")
    
    # Crear el PDF con las imágenes
    try:
        from reportlab.lib.utils import ImageReader
        
        # Crear un PDF con las imágenes
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Añadir cada imagen como una página del PDF
        for img_path in image_files:
            logger.info(f"Agregando imagen: {img_path}")
            img = Image.open(img_path)
            img_width, img_height = img.size
            
            # Ajustar tamaño para que quepa en la página
            page_width, page_height = letter
            ratio = min(page_width / img_width, page_height / img_height) * 0.9
            new_width = img_width * ratio
            new_height = img_height * ratio
            
            # Posicionar en el centro de la página
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            c.drawImage(ImageReader(img), x, y, width=new_width, height=new_height)
            c.showPage()
        
        # Guardar el PDF
        c.save()
        logger.info(f"PDF generado correctamente: {pdf_path}")
        
        return pdf_path
    except Exception as e:
        logger.error(f"Error al generar PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def encode_file_to_base64(file_path):
    """Codifica un archivo a base64"""
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
            return base64.b64encode(file_content).decode('utf-8')
    except Exception as e:
        logger.error(f"Error al codificar archivo a base64: {e}")
        return None

def upload_document_to_gesdoc(rut, folio, pdf_path, usuario="Sistema"):
    """Sube un documento a Gesdoc API usando RUT, folio y archivo codificado en base64"""
    logger.info(f"Subiendo documento a Gesdoc: RUT={rut}, Folio={folio}, Usuario={usuario}")
    
    config = load_config()
    if not config:
        return {"status": "error", "message": "No se pudo cargar la configuración"}
    
    # Sanitizar formato de RUT
    rut = sanitize_rut(rut)
    
    # Construir la URL desde la configuración
    base_url = config.get('endpoint', config.get('gesdoc_api'))
    
    # Asegurar que la URL comience con https://
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    
    # Usar el endpoint correcto
    api_path = "/api/v1/upload_document"
    api_key = config.get('apikey')
    auth_token = config.get('auth_token')
    
    logger.info(f"URL base: {base_url}")
    
    # Construir la URL con parámetros de consulta
    url = f"{base_url}{api_path}?rut={rut}&folio={folio}"
    
    # Configurar los headers
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Codificar el archivo a base64
    base64_file = encode_file_to_base64(pdf_path)
    if not base64_file:
        return {"status": "error", "message": "Error al codificar el archivo PDF a base64"}
    
    # Crear payload exactamente como en la colección de Postman
    payload = {
        "usuario": usuario,
        "file": base64_file
    }
    
    try:
        logger.info(f"Haciendo solicitud POST a: {url}")
        logger.info(f"Parámetros: rut={rut}, folio={folio}")
        logger.info(f"Payload contiene archivo de longitud: {len(base64_file)} caracteres")
        
        # Permitir redirecciones, pero usar una URL HTTPS directa
        response = requests.post(
            url, 
            headers=headers, 
            json=payload, 
            verify=False,
            allow_redirects=True
        )
        
        logger.info(f"Código de estado de la respuesta: {response.status_code}")
        
        # Intentar analizar la respuesta como JSON si es posible
        try:
            result = response.json()
            logger.info(f"¡Éxito! Respuesta JSON analizada: {result}")
            return result
        except ValueError:
            # No es JSON, verificar si es un código de estado exitoso
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Éxito con código de estado {response.status_code}, pero la respuesta no es JSON.")
                logger.info(f"Texto de la respuesta: {response.text[:200]}...")
                return {"status": "success", "message": f"Código de estado {response.status_code}"}
            else:
                logger.error(f"Respuesta de error (no JSON): {response.text[:200]}...")
                response.raise_for_status()  # Generar excepción para códigos no 2xx
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al hacer la solicitud: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Código de estado: {e.response.status_code}")
            logger.error(f"Texto de la respuesta: {e.response.text[:200]}...")
        return {"status": "error", "message": str(e)}

def actualizar_csv(folio, nombre_documento):
    """Actualiza el CSV con el nombre del documento."""
    try:
        csv_path = 'db_input.csv'
        temp_file = 'db_input_temp.csv'
        
        # Verificar si el archivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV no encontrado: {csv_path}")
            return False
        
        # Leer el CSV y actualizar la fila correspondiente
        actualizado = False
        with open(csv_path, 'r', encoding='utf-8') as file_in, open(temp_file, 'w', newline='', encoding='utf-8') as file_out:
            csv_reader = csv.DictReader(file_in)
            fieldnames = csv_reader.fieldnames
            
            csv_writer = csv.DictWriter(file_out, fieldnames=fieldnames)
            csv_writer.writeheader()
            
            for row in csv_reader:
                if row.get('folio') == folio:
                    row['nombre_documento'] = nombre_documento
                    actualizado = True
                csv_writer.writerow(row)
        
        # Reemplazar el archivo original con el temporal
        if actualizado:
            os.replace(temp_file, csv_path)
            logger.info(f"CSV actualizado correctamente para el folio {folio}")
            return True
        else:
            os.remove(temp_file)
            logger.warning(f"No se encontró el folio {folio} en el CSV")
            return False
    
    except Exception as e:
        logger.error(f"Error al actualizar CSV: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def buscar_por_folio(folio):
    """
    Busca un registro en el CSV por número de folio.
    
    Args:
        folio (str): Número de folio a buscar
        
    Returns:
        dict: Datos del registro encontrado o None si no se encuentra
    """
    try:
        # Ruta al archivo CSV
        csv_path = 'db_input.csv'
        
        # Verificar si el archivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV no encontrado: {csv_path}")
            return None
        
        # Imprimir información de depuración
        logger.info(f"Buscando folio: {folio}")
        logger.info(f"Ruta del CSV: {os.path.abspath(csv_path)}")
        
        # Contar registros en el CSV para verificar que se está leyendo correctamente
        total_registros = 0
        folios_disponibles = []
        
        # Buscar el folio en el CSV
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                total_registros += 1
                current_folio = row.get('folio', '')
                folios_disponibles.append(current_folio)
                
                if current_folio == folio:
                    # Construir los datos formateados
                    nombre_estudiante = f"{row.get('nombres_alumno', '')} {row.get('apellido_pat_alumno', '')} {row.get('apellido_mat_alumno', '')}"
                    nombre_aval = f"{row.get('nombres_aval', '')} {row.get('ape_pat_aval', '')} {row.get('ap_mat_aval', '')}"
                    
                    # Crear diccionario con los datos requeridos
                    datos = {
                        'nombre_estudiante': nombre_estudiante.strip(),
                        'nombre_aval': nombre_aval.strip(),
                        'rut_aval': row.get('rut_aval', ''),
                        'rut': row.get('rut', ''),  # Añadir el RUT del estudiante
                        'dig_ver': row.get('dig_ver', ''),  # Añadir el dígito verificador
                        'monto': row.get('monto', ''),
                        'email_aval': row.get('mail_aval', '')
                    }
                    
                    logger.info(f"Registro encontrado para folio {folio}: {datos}")
                    return datos
        
        # Si llegamos aquí, no se encontró el folio
        logger.warning(f"No se encontró registro para el folio {folio}")
        logger.info(f"Total de registros en el CSV: {total_registros}")
        logger.info(f"Primeros 5 folios disponibles: {folios_disponibles[:5]}")
        return None
    
    except Exception as e:
        logger.error(f"Error al buscar folio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def procesar_y_subir_documento(rut, folio, usuario):
    """
    Procesa un documento, genera un PDF y lo sube a Gesdoc.
    
    Args:
        rut (str): RUT con guion
        folio (str): Número de folio
        usuario (str): Nombre de usuario que está realizando la operación
    
    Returns:
        dict: Resultado de la operación
    """
    logger.info(f"Iniciando procesamiento para RUT: {rut}, Folio: {folio}, Usuario: {usuario}")
    
    # 1. Generar el PDF con las imágenes de input
    pdf_path = generar_pdf_desde_imagenes(rut, folio)
    if not pdf_path:
        return {
            "status": "error",
            "message": "No se pudo generar el PDF desde las imágenes de entrada."
        }
    
    # 2. Actualizar el CSV con el nombre del documento
    filename = os.path.basename(pdf_path)
    actualizado = actualizar_csv(folio, filename)
    if not actualizado:
        logger.warning(f"No se pudo actualizar el CSV para el folio {folio}")
    
    # 3. Subir el documento a Gesdoc
    resultado = upload_document_to_gesdoc(rut, folio, pdf_path, usuario)
    
    # 4. Agregar información adicional al resultado
    resultado["pdf_path"] = pdf_path
    resultado["csv_actualizado"] = actualizado
    
    logger.info(f"Procesamiento completo. Resultado: {resultado}")
    return resultado

if __name__ == "__main__":
    # Código para pruebas
    folio_test = "2025010058"  # Usar un folio que sabemos que existe en el CSV
    resultado = buscar_por_folio(folio_test)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    # Prueba de procesamiento completo
    if resultado:
        rut_completo = f"{resultado['rut']}-{resultado['dig_ver']}"
        print(f"\nProcesando documento para RUT: {rut_completo}, Folio: {folio_test}")
        res = procesar_y_subir_documento(rut_completo, folio_test, "test_user")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    
    # Listar todos los folios disponibles
    csv_path = 'db_input.csv'
    if os.path.exists(csv_path):
        print("\nFolios disponibles:")
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            folios = [row.get('folio', '') for row in csv_reader]
            print(f"Total de folios: {len(folios)}")
            print(f"Primeros 10 folios: {folios[:10]}")
