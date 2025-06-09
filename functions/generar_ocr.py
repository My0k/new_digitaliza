import os
import glob
import logging
import subprocess
import platform
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
import io
import shutil
import multiprocessing
import time
import threading
import codecs
import csv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_csv_handling(csv_file, mode='r', data_to_write=None):
    """
    Maneja de forma segura la lectura y escritura de archivos CSV con encoding UTF-8.
    Gestiona el BOM (Byte Order Mark) y otros problemas de codificación.
    
    Args:
        csv_file (str): Ruta al archivo CSV
        mode (str): Modo de apertura ('r' para lectura, 'w' para escritura)
        data_to_write (list): Datos a escribir si mode es 'w'
        
    Returns:
        list: Datos leídos del CSV si mode es 'r'
        bool: True si la escritura fue exitosa, si mode es 'w'
    """
    try:
        if mode == 'r':
            # Leer el archivo con UTF-8 y manejar BOM
            with open(csv_file, 'r', encoding='utf-8-sig', newline='', errors='replace') as f:
                reader = csv.reader(f)
                return list(reader)
        elif mode == 'w':
            # Escribir el archivo con UTF-8 sin BOM
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for row in data_to_write:
                    # Limpiar cualquier BOM residual en los datos
                    clean_row = [str(cell).replace('\ufeff', '') if cell else '' for cell in row]
                    writer.writerow(clean_row)
            return True
    except Exception as e:
        logger.error(f"Error en manejo de CSV {csv_file}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return [] if mode == 'r' else False

def generar_ocr_carpeta(folder_id):
    """
    Genera un PDF con OCR a partir de las imágenes en una carpeta específica.
    
    Args:
        folder_id (str): Identificador de la carpeta a procesar
        
    Returns:
        dict: Diccionario con el resultado de la operación
    """
    try:
        # Definir rutas
        base_dir = os.path.join('proceso', 'carpetas')
        folder_path = os.path.join(base_dir, folder_id)
        output_dir = os.path.join('proceso', 'ocr_generado')
        temp_dir = os.path.join('proceso', 'temp')
        
        # Crear directorios si no existen
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Verificar que la carpeta existe
        if not os.path.exists(folder_path):
            return {
                'success': False,
                'error': f"La carpeta {folder_id} no existe en {base_dir}"
            }
        
        # Obtener imágenes JPG/JPEG de la carpeta
        image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
        
        # Verificar que hay imágenes para procesar
        if not image_files:
            return {
                'success': False,
                'error': f"No hay imágenes JPG/JPEG en la carpeta {folder_id}"
            }
        
        # Ordenar imágenes por fecha de modificación (más antiguas primero)
        image_files.sort(key=os.path.getmtime)
        
        # Nombre del archivo PDF de salida
        output_pdf = os.path.join(output_dir, f"{folder_id}.pdf")
        
        # Generar PDF básico con las imágenes
        logger.info(f"Generando PDF básico para la carpeta {folder_id} con {len(image_files)} imágenes")
        basic_pdf = os.path.join(temp_dir, f"{folder_id}_basic.pdf")
        
        # Paso 1: Crear un PDF básico con las imágenes
        c = canvas.Canvas(basic_pdf, pagesize=letter)
        
        for img_path in image_files:
            try:
                with Image.open(img_path) as img:
                    # Verificar que la imagen es válida
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
            except Exception as img_err:
                logger.error(f"Error al procesar imagen {img_path}: {str(img_err)}")
        
        c.save()
        logger.info(f"PDF básico generado: {basic_pdf}")
        
        # Paso 2: Aplicar OCR al PDF básico
        try:
            # Comprobar si tenemos Tesseract instalado
            ocr_output_pdf = os.path.join(temp_dir, f"{folder_id}_ocr.pdf")
            
            if shutil.which('tesseract'):
                logger.info("Usando Tesseract para OCR...")
                
                # Método 1: Aplicar OCR con pytesseract a cada imagen y luego crear un PDF
                try:
                    # Crear un documento PDF con PyMuPDF (fitz)
                    doc = fitz.open()
                    
                    for img_path in image_files:
                        # Realizar OCR en la imagen
                        text = pytesseract.image_to_string(Image.open(img_path), lang='spa')
                        
                        # Insertar la imagen en el PDF
                        img_doc = fitz.open(img_path)
                        pdfbytes = img_doc.convert_to_pdf()
                        img_pdf = fitz.open("pdf", pdfbytes)
                        
                        # Añadir la página al documento final
                        page_num = doc.insert_pdf(img_pdf)
                        
                        # Añadir el texto OCR como capa invisible
                        page = doc[page_num[0]]  # La primera página insertada
                        
                        # Añadir texto como anotación invisible (capa de texto OCR)
                        page.insert_text((50, 50), text, fontsize=0.1, color=(1, 1, 1))
                        
                    # Guardar el documento final
                    doc.save(ocr_output_pdf)
                    doc.close()
                    
                    logger.info(f"OCR aplicado a {len(image_files)} imágenes y guardado en {ocr_output_pdf}")
                    
                    # Copiar el resultado final a la carpeta de salida
                    shutil.copy2(ocr_output_pdf, output_pdf)
                    
                except Exception as ocr_err:
                    logger.error(f"Error al aplicar OCR con pytesseract: {str(ocr_err)}")
                    logger.info("Usando método alternativo para OCR...")
                    
                    # Método 2: Intentar con OCRmyPDF si está disponible
                    if shutil.which('ocrmypdf'):
                        try:
                            cmd = ['ocrmypdf', '--force-ocr', '--language', 'spa', basic_pdf, output_pdf]
                            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            
                            if process.returncode != 0:
                                logger.warning(f"OCRmyPDF terminó con código {process.returncode}: {stderr.decode()}")
                                # Usar el PDF básico como respaldo
                                shutil.copy2(basic_pdf, output_pdf)
                            else:
                                logger.info(f"OCR aplicado exitosamente con OCRmyPDF: {output_pdf}")
                        except Exception as ocrmypdf_err:
                            logger.error(f"Error al ejecutar OCRmyPDF: {str(ocrmypdf_err)}")
                            # Usar el PDF básico como respaldo
                            shutil.copy2(basic_pdf, output_pdf)
                    else:
                        # Si no hay OCRmyPDF, usar el PDF básico
                        logger.warning("OCRmyPDF no está disponible, usando PDF básico")
                        shutil.copy2(basic_pdf, output_pdf)
            else:
                logger.warning("Tesseract no está instalado, se generará un PDF sin OCR")
                # Usar el PDF básico como salida final
                shutil.copy2(basic_pdf, output_pdf)
                
        except Exception as ocr_process_err:
            logger.error(f"Error en el proceso de OCR: {str(ocr_process_err)}")
            # Usar el PDF básico como respaldo
            shutil.copy2(basic_pdf, output_pdf)
        
        # Limpiar archivos temporales
        try:
            if os.path.exists(basic_pdf):
                os.remove(basic_pdf)
            if os.path.exists(ocr_output_pdf):
                os.remove(ocr_output_pdf)
        except Exception as cleanup_err:
            logger.warning(f"Error al limpiar archivos temporales: {str(cleanup_err)}")
        
        return {
            'success': True,
            'message': f"PDF con OCR generado: {output_pdf}",
            'pdf_path': output_pdf,
            'folder_id': folder_id
        }
        
    except Exception as e:
        error_msg = f"Error al generar OCR para carpeta {folder_id}: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }

def procesar_todas_carpetas():
    """
    Procesa todas las carpetas pendientes y genera PDFs con OCR.
    
    Returns:
        dict: Diccionario con el resultado de la operación
    """
    try:
        # Obtener lista de carpetas en proceso/carpetas
        base_dir = os.path.join('proceso', 'carpetas')
        os.makedirs(base_dir, exist_ok=True)
        
        folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
        
        if not folders:
            return {
                'success': False,
                'error': "No hay carpetas para procesar"
            }
        
        # Obtener carpetas ya procesadas (si existe archivo)
        processed_folders = []
        processed_file = 'carpetas_procesadas.txt'
        
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                processed_folders = [line.strip() for line in f.readlines()]
        
        # Filtrar carpetas ya procesadas
        folders_to_process = [f for f in folders if f not in processed_folders]
        
        if not folders_to_process:
            return {
                'success': False,
                'error': "Todas las carpetas ya han sido procesadas"
            }
        
        # Procesar cada carpeta
        results = []
        for folder in folders_to_process:
            result = generar_ocr_carpeta(folder)
            results.append(result)
            
            # Si el procesamiento fue exitoso, añadir a la lista de procesados
            if result['success']:
                with open(processed_file, 'a') as f:
                    f.write(f"{folder}\n")
        
        # Contar éxitos y fallos
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': True,
            'processed': len(results),
            'success_count': success_count,
            'error_count': len(results) - success_count,
            'details': results
        }
        
    except Exception as e:
        error_msg = f"Error al procesar todas las carpetas: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }

# Versión simplificada de la función para solo crear un PDF básico sin OCR
def generar_pdf_simple(folder_id):
    """
    Genera un PDF simple a partir de las imágenes en una carpeta específica.
    
    Args:
        folder_id (str): Identificador de la carpeta a procesar
        
    Returns:
        dict: Diccionario con el resultado de la operación
    """
    try:
        # Definir rutas
        base_dir = os.path.join('proceso', 'carpetas')
        folder_path = os.path.join(base_dir, folder_id)
        output_dir = os.path.join('proceso', 'ocr_generado')
        
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Verificar que la carpeta existe
        if not os.path.exists(folder_path):
            return {
                'success': False,
                'error': f"La carpeta {folder_id} no existe en {base_dir}"
            }
        
        # Obtener imágenes JPG/JPEG de la carpeta
        image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
        
        # Verificar que hay imágenes para procesar
        if not image_files:
            return {
                'success': False,
                'error': f"No hay imágenes JPG/JPEG en la carpeta {folder_id}"
            }
        
        # Ordenar imágenes por fecha de modificación (más antiguas primero)
        image_files.sort(key=os.path.getmtime)
        
        # Filtrar imágenes que son principalmente blancas
        print(f"Analizando {len(image_files)} imágenes para detectar páginas en blanco...")
        filtered_images = []
        white_images = 0
        
        for img_path in image_files:
            if not is_mostly_white(img_path):
                filtered_images.append(img_path)
            else:
                white_images += 1
        
        # Informar sobre las imágenes filtradas
        if white_images > 0:
            print(f"Se han filtrado {white_images} imágenes principalmente blancas")
            logger.info(f"Se han filtrado {white_images} imágenes principalmente blancas de la carpeta {folder_id}")
        
        # Verificar si quedan imágenes después del filtrado
        if not filtered_images:
            return {
                'success': False,
                'error': f"Todas las imágenes en la carpeta {folder_id} son principalmente blancas"
            }
        
        # Nombre del archivo PDF de salida
        output_pdf = os.path.join(output_dir, f"{folder_id}.pdf")
        
        # Generar PDF básico con las imágenes
        logger.info(f"Generando PDF para la carpeta {folder_id} con {len(filtered_images)} imágenes")
        
        # Crear un PDF con reportlab
        c = canvas.Canvas(output_pdf, pagesize=letter)
        
        for img_path in filtered_images:
            try:
                with Image.open(img_path) as img:
                    # Verificar que la imagen es válida
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
            except Exception as img_err:
                logger.error(f"Error al procesar imagen {img_path}: {str(img_err)}")
        
        c.save()
        logger.info(f"PDF generado: {output_pdf}")
        
        # Actualizar archivo de carpetas procesadas
        try:
            carpetas_csv = 'carpetas.csv'
            carpetas_headers = ['carpeta_indexada', 'ocr_generado']
            carpetas_rows = []
            
            # Leer archivo si existe
            if os.path.exists(carpetas_csv) and os.path.getsize(carpetas_csv) > 0:
                carpetas_data = safe_csv_handling(carpetas_csv, 'r')
                if carpetas_data:
                    carpetas_headers = carpetas_data[0]
                    carpetas_rows = carpetas_data[1:]
            
            # Buscar si la carpeta ya existe en el CSV
            folder_exists = False
            for row in carpetas_rows:
                if len(row) > 1 and row[1] == folder_id:
                    folder_exists = True
                    break
            
            # Si la carpeta no existe, añadirla
            if not folder_exists:
                carpetas_rows.append(['', folder_id])
            
            # Escribir archivo actualizado
            all_rows = [carpetas_headers] + carpetas_rows
            if safe_csv_handling(carpetas_csv, 'w', all_rows):
                logger.info(f"Carpeta {folder_id} registrada en carpetas.csv como ocr_generado")
            else:
                logger.error(f"Error al actualizar carpetas.csv para la carpeta {folder_id}")
                
        except Exception as csv_err:
            logger.error(f"Error al actualizar carpetas.csv: {str(csv_err)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return {
            'success': True,
            'message': f"PDF generado: {output_pdf}",
            'pdf_path': output_pdf,
            'folder_id': folder_id,
            'total_images': len(image_files),
            'processed_images': len(filtered_images),
            'skipped_white_images': white_images
        }
        
    except Exception as e:
        error_msg = f"Error al generar PDF para carpeta {folder_id}: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }

def generar_pdf_con_ocr(folder_id):
    """
    Genera un PDF con OCR a partir de las imágenes en una carpeta específica.
    Primero crea un PDF básico y luego aplica OCR usando ocrmypdf.
    Utiliza múltiples núcleos para optimizar el rendimiento.
    
    Args:
        folder_id (str): Identificador de la carpeta a procesar
        
    Returns:
        dict: Diccionario con el resultado de la operación
    """
    try:
        print(f"=== Iniciando generación de PDF con OCR para carpeta {folder_id} ===")
        start_time = time.time()
        
        # Primero generamos el PDF básico
        print(f"Paso 1/3: Generando PDF básico para carpeta {folder_id}...")
        result = generar_pdf_simple(folder_id)
        
        if not result['success']:
            print(f"Error al generar PDF básico: {result.get('error', 'Error desconocido')}")
            return result  # Si falla la generación del PDF básico, retornamos el error
        
        print(f"PDF básico generado correctamente: {result['pdf_path']}")
        
        # Rutas para el PDF generado y el PDF con OCR
        pdf_path = result['pdf_path']
        ocr_pdf_path = pdf_path.replace('.pdf', '_ocr.pdf')
        
        # Verificar que ocrmypdf está instalado
        print(f"Paso 2/3: Verificando instalación de ocrmypdf...")
        if not check_ocrmypdf_installed():
            print("ocrmypdf no está instalado. Intentando instalarlo...")
            if not install_ocrmypdf():
                print("No se pudo instalar ocrmypdf. Se utilizará el PDF básico.")
                return {
                    'success': False,
                    'error': "No se pudo instalar ocrmypdf para el procesamiento OCR.",
                    'pdf_path': pdf_path,  # Devolvemos el PDF básico como fallback
                    'folder_id': folder_id
                }
        
        # Aplicar OCR al PDF básico
        print(f"Paso 3/3: Aplicando OCR al PDF...")
        logger.info(f"Aplicando OCR al PDF de la carpeta {folder_id}...")
        
        ocr_start_time = time.time()
        success = process_pdf_with_ocr(pdf_path, ocr_pdf_path)
        ocr_duration = time.time() - ocr_start_time
        minutes, seconds = divmod(int(ocr_duration), 60)
        
        if success:
            # Si el OCR fue exitoso, reemplazamos el PDF original con el OCR
            if os.path.exists(ocr_pdf_path):
                print(f"OCR completado en {minutes}m {seconds}s. Reemplazando PDF original...")
                os.replace(ocr_pdf_path, pdf_path)
                logger.info(f"PDF con OCR generado exitosamente y reemplazado: {pdf_path}")
                
                total_duration = time.time() - start_time
                total_min, total_sec = divmod(int(total_duration), 60)
                print(f"=== Proceso completado en {total_min}m {total_sec}s ===")
                
                # Actualizar carpetas.csv
                print("Registrando carpeta procesada en carpetas.csv...")
                
                return {
                    'success': True,
                    'message': f"PDF con OCR generado: {pdf_path}",
                    'pdf_path': pdf_path,
                    'folder_id': folder_id,
                    'ocr_applied': True,
                    'processing_time': f"{minutes}m {seconds}s"
                }
            else:
                print(f"Error: El archivo OCR no existe después del procesamiento: {ocr_pdf_path}")
                logger.warning(f"El archivo OCR no existe después del procesamiento: {ocr_pdf_path}")
                return {
                    'success': True,
                    'message': f"PDF generado sin OCR: {pdf_path}",
                    'pdf_path': pdf_path,
                    'folder_id': folder_id,
                    'ocr_applied': False
                }
        else:
            print(f"Error al aplicar OCR. Se utilizará el PDF básico.")
            logger.error(f"Error al aplicar OCR al PDF {pdf_path}")
            return {
                'success': True,  # Consideramos éxito parcial ya que el PDF básico se generó
                'message': f"PDF generado sin OCR: {pdf_path}",
                'pdf_path': pdf_path,
                'folder_id': folder_id,
                'ocr_applied': False,
                'ocr_error': "Error al procesar OCR. Se mantiene el PDF básico."
            }
            
    except Exception as e:
        error_msg = f"Error al generar PDF con OCR para carpeta {folder_id}: {str(e)}"
        logger.error(error_msg)
        print(f"Error: {error_msg}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        print(error_trace)
        return {
            'success': False,
            'error': error_msg
        }

def check_ocrmypdf_installed():
    """Verifica si ocrmypdf está instalado en el sistema."""
    try:
        subprocess.run(["ocrmypdf", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_ocrmypdf():
    """Intenta instalar ocrmypdf si no está disponible."""
    system = platform.system()
    logger.info(f"Intentando instalar ocrmypdf en sistema {system}...")
    
    try:
        if system == "Windows":
            subprocess.run(["pip", "install", "ocrmypdf"], check=True)
            logger.info("Se ha instalado ocrmypdf correctamente.")
            return True
        elif system == "Linux":
            # En entornos de producción, es mejor instalar con apt
            try:
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "ocrmypdf"], check=True)
                logger.info("Se ha instalado ocrmypdf correctamente con apt.")
                return True
            except subprocess.SubprocessError:
                # Si falla apt, intentar con pip
                subprocess.run(["pip", "install", "ocrmypdf"], check=True)
                logger.info("Se ha instalado ocrmypdf correctamente con pip.")
                return True
        else:
            logger.error(f"Sistema operativo {system} no soportado directamente.")
            # Intentar con pip como último recurso
            subprocess.run(["pip", "install", "ocrmypdf"], check=True)
            logger.info("Se ha instalado ocrmypdf correctamente con pip.")
            return True
    except subprocess.SubprocessError:
        logger.error("Error al instalar ocrmypdf. Se requiere instalación manual.")
        return False

def process_pdf_with_ocr(input_file, output_file, language="spa", deskew=True, clean=True, optimize=True):
    """
    Procesa un archivo PDF y genera una versión con OCR utilizando múltiples núcleos.
    
    Args:
        input_file: Ruta del archivo PDF de entrada
        output_file: Ruta donde se guardará el PDF con OCR
        language: Idioma para el OCR (por defecto español)
        deskew: Si se debe enderezar el texto inclinado
        clean: Si se debe limpiar la imagen antes del OCR
        optimize: Si se debe optimizar el PDF resultante
        
    Returns:
        bool: True si el proceso fue exitoso, False en caso contrario
    """
    if not os.path.exists(input_file):
        logger.error(f"Error: El archivo {input_file} no existe.")
        return False
    
    # Determinar el número de núcleos a utilizar (todos menos uno)
    cpu_count = max(1, multiprocessing.cpu_count() - 1)
    logger.info(f"Utilizando {cpu_count} núcleos para el procesamiento OCR")
    print(f"Utilizando {cpu_count} núcleos para el procesamiento OCR")
    
    # Preparar comando con opciones
    cmd = ["ocrmypdf"]
    
    if deskew:
        cmd.append("--deskew")
    
    if clean:
        cmd.append("--clean")
    
    if optimize:
        cmd.append("--optimize")
        cmd.append("3")
    
    # Forzar OCR aunque el PDF ya tenga texto
    cmd.append("--force-ocr")
    
    # Configurar procesamiento paralelo
    cmd.append("--jobs")
    cmd.append(str(cpu_count))
    
    # Especificar idioma
    cmd.extend(["-l", language])
    
    # Agregar archivos de entrada y salida
    cmd.extend([str(input_file), str(output_file)])
    
    try:
        logger.info(f"Iniciando procesamiento OCR para {input_file}...")
        print(f"Iniciando procesamiento OCR para {input_file}...")
        
        # Iniciar proceso
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Función para monitorear el progreso
        def monitor_progress():
            print(f"Monitoreando proceso OCR (PID: {process.pid})...")
            start_time = time.time()
            last_output_time = start_time
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                time_since_last_output = time.time() - last_output_time
                
                # Mostrar tiempo transcurrido cada 30 segundos o si no hay salida por más de 1 minuto
                if elapsed % 30 < 1 or time_since_last_output > 60:
                    minutes, seconds = divmod(int(elapsed), 60)
                    print(f"OCR en progreso: {minutes}m {seconds}s transcurridos...")
                    last_output_time = time.time()
                
                time.sleep(1)
        
        # Iniciar monitoreo en un hilo separado
        monitor_thread = threading.Thread(target=monitor_progress)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Leer salida del proceso en tiempo real
        for line in process.stdout:
            line = line.strip()
            if line:
                print(f"OCR: {line}")
                last_output_time = time.time()
        
        # Esperar a que termine el proceso
        stdout, stderr = process.communicate()
        
        # Analizar resultado
        if process.returncode != 0:
            logger.error(f"Error en el procesamiento OCR (código {process.returncode})")
            if stderr:
                logger.error(f"Detalles del error: {stderr}")
                print(f"Error OCR: {stderr}")
            return False
        
        # Verificar que el archivo existe
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"OCR aplicado exitosamente. PDF generado: {output_file} ({file_size} bytes)")
            print(f"OCR aplicado exitosamente. PDF generado: {output_file} ({file_size} bytes)")
            return True
        else:
            logger.error(f"El archivo de salida {output_file} no fue creado")
            print(f"Error: El archivo de salida {output_file} no fue creado")
            return False
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error al ejecutar ocrmypdf: {str(e)}")
        print(f"Error al ejecutar ocrmypdf: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado en el procesamiento OCR: {str(e)}")
        print(f"Error inesperado en el procesamiento OCR: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(traceback.format_exc())
        return False

def is_mostly_white(image_path, threshold=99.6):
    """
    Determina si una imagen es principalmente blanca.
    
    Args:
        image_path (str): Ruta a la imagen a analizar
        threshold (float): Porcentaje de píxeles blancos para considerar una imagen como blanca (0-100)
        
    Returns:
        bool: True si la imagen es principalmente blanca, False en caso contrario
    """
    try:
        with Image.open(image_path) as img:
            # Convertir a escala de grises para simplificar el análisis
            img_gray = img.convert('L')
            
            # Obtener histograma (distribución de niveles de gris)
            hist = img_gray.histogram()
            
            # Calcular total de píxeles
            total_pixels = img.width * img.height
            
            # Contar píxeles muy claros (valores cercanos a 255)
            # Consideramos los valores de 240-255 como "casi blancos"
            white_pixels = sum(hist[240:])
            
            # Calcular porcentaje de píxeles blancos
            white_percentage = (white_pixels / total_pixels) * 100
            
            # Verificar si excede el umbral
            is_white = white_percentage >= threshold
            
            if is_white:
                logger.info(f"Imagen {os.path.basename(image_path)} detectada como página en blanco ({white_percentage:.2f}% blanco)")
                print(f"Imagen {os.path.basename(image_path)} detectada como página en blanco ({white_percentage:.2f}% blanco)")
            
            return is_white
            
    except Exception as e:
        logger.error(f"Error al analizar si la imagen {image_path} es blanca: {str(e)}")
        # En caso de error, asumimos que no es blanca para procesarla
        return False

if __name__ == "__main__":
    # Probar la función si se ejecuta directamente
    import sys
    
    if len(sys.argv) > 1:
        folder_id = sys.argv[1]
        print(f"Procesando carpeta: {folder_id}")
        result = generar_ocr_carpeta(folder_id)
        print(result)
    else:
        print("Procesando todas las carpetas pendientes")
        result = procesar_todas_carpetas()
        print(result)
