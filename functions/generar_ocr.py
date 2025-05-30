import os
import glob
import logging
import subprocess
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
import io
import shutil

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        
        # Nombre del archivo PDF de salida
        output_pdf = os.path.join(output_dir, f"{folder_id}.pdf")
        
        # Crear un PDF básico con las imágenes
        logger.info(f"Generando PDF para la carpeta {folder_id} con {len(image_files)} imágenes")
        
        c = canvas.Canvas(output_pdf, pagesize=letter)
        
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
        logger.info(f"PDF generado exitosamente: {output_pdf}")
        
        # Registrar la carpeta procesada en carpetas.csv en la columna ocr_generado
        try:
            import csv
            
            carpetas_csv = 'carpetas.csv'
            carpetas_rows = []
            carpeta_found = False
            
            # Verificar si el archivo existe y tiene contenido
            if os.path.exists(carpetas_csv) and os.path.getsize(carpetas_csv) > 0:
                with open(carpetas_csv, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    carpetas_headers = next(reader)  # Guardar encabezados
                    
                    # Asegurarse de que existe la columna ocr_generado
                    if 'ocr_generado' not in carpetas_headers:
                        carpetas_headers.append('ocr_generado')
                    
                    ocr_generado_index = carpetas_headers.index('ocr_generado')
                    
                    # Leer filas existentes y buscar si la carpeta ya está registrada
                    for row in reader:
                        if row and len(row) > 0:
                            if row[0] == folder_id:
                                carpeta_found = True
                                # Asegurarse de que la fila tiene suficientes columnas
                                while len(row) <= ocr_generado_index:
                                    row.append('')
                                # Actualizar el valor de ocr_generado
                                row[ocr_generado_index] = folder_id
                            
                            # Guardar la fila (actualizada o no)
                            carpetas_rows.append(row)
            else:
                # Si el archivo no existe o está vacío, crear encabezados
                carpetas_headers = ['carpeta_indexada', 'ocr_generado']
                ocr_generado_index = 1
            
            # Si la carpeta no está registrada, añadirla con ocr_generado
            if not carpeta_found:
                new_row = [''] * len(carpetas_headers)
                new_row[ocr_generado_index] = folder_id
                carpetas_rows.append(new_row)
            
            # Escribir el archivo carpetas.csv actualizado
            with open(carpetas_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(carpetas_headers)
                writer.writerows(carpetas_rows)
                
            logger.info(f"Carpeta {folder_id} registrada en carpetas.csv como ocr_generado")
            
        except Exception as csv_err:
            logger.error(f"Error al actualizar carpetas.csv: {str(csv_err)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return {
            'success': True,
            'message': f"PDF generado: {output_pdf}",
            'pdf_path': output_pdf,
            'folder_id': folder_id
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
