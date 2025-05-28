from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, send_file
import os
import glob
from datetime import datetime
import shutil
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64
import threading
import time
import logging
import random
import string
import subprocess
import json
import csv
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import functools
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura'  # Cambiar en producción
app.config['UPLOAD_FOLDER'] = 'input'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 año en segundos

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variable para almacenar la última modificación de la carpeta
last_folder_modification = 0
folder_monitor_active = True

# Asegurar que la carpeta de entrada existe
def ensure_input_folder():
    """Asegura que la carpeta input existe y es accesible."""
    input_folder = app.config['UPLOAD_FOLDER']
    try:
        os.makedirs(input_folder, exist_ok=True)
        logger.info(f"Carpeta de entrada verificada: {os.path.abspath(input_folder)}")
        return True
    except Exception as e:
        logger.error(f"Error al crear la carpeta de entrada: {e}")
        return False

# Inicializar la carpeta de entrada
ensure_input_folder()

def get_latest_images(folder='input', count=None):
    """Obtiene las rutas de las imágenes en la carpeta especificada.
    Si count es None, devuelve todas las imágenes disponibles."""
    try:
        files = glob.glob(os.path.join(folder, '*.jpg')) + glob.glob(os.path.join(folder, '*.jpeg'))
        # Ordenar archivos por fecha de modificación (más reciente primero)
        files.sort(key=os.path.getmtime, reverse=True)
        return files[:count] if count is not None else files
    except Exception as e:
        logger.error(f"Error al obtener imágenes: {e}")
        return []

def get_image_data(image_path):
    """Convierte una imagen a base64 para mostrarla en HTML."""
    try:
        with Image.open(image_path) as img:
            # Redimensionar si es necesario
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {
                'name': os.path.basename(image_path),
                'path': image_path,
                'data': f'data:image/jpeg;base64,{img_str}',
                'modified': datetime.fromtimestamp(os.path.getmtime(image_path)).strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        logger.error(f"Error al procesar imagen {image_path}: {e}")
        return {
            'name': os.path.basename(image_path),
            'path': image_path,
            'data': None,
            'error': str(e),
            'modified': datetime.fromtimestamp(os.path.getmtime(image_path)).strftime('%Y-%m-%d %H:%M:%S')
        }

# Función para generar un nombre de archivo único basado en timestamp y letras aleatorias
def generate_unique_filename():
    """Genera un nombre de archivo único con timestamp y 3 letras aleatorias."""
    timestamp = int(datetime.now().timestamp())
    # Generar 3 letras aleatorias
    random_letters = ''.join(random.choices(string.ascii_lowercase, k=3))
    return f"{timestamp}{random_letters}.jpg"

def check_folder_changes():
    """Monitorea cambios en la carpeta input."""
    global last_folder_modification, folder_monitor_active
    
    logger.info("Iniciando monitoreo de la carpeta input...")
    
    while folder_monitor_active:
        try:
            # Verificar si la carpeta existe
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                ensure_input_folder()
                
            # Obtener la última modificación de la carpeta y renombrar archivos nuevos
            latest_mod_time = 0
            files_to_rename = []
            
            for file in os.listdir(app.config['UPLOAD_FOLDER']):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                
                # Solo procesar archivos JPG
                if file.lower().endswith(('.jpg', '.jpeg')) and os.path.isfile(file_path):
                    mod_time = os.path.getmtime(file_path)
                    
                    # Verificar si el nombre del archivo ya tiene formato de timestamp+letras
                    filename_without_ext = os.path.splitext(file)[0]
                    # Verificar si el nombre tiene al menos 13 caracteres (timestamp) y los primeros 10+ son dígitos
                    if len(filename_without_ext) < 13 or not filename_without_ext[:-3].isdigit():
                        files_to_rename.append(file_path)
                    
                    if mod_time > latest_mod_time:
                        latest_mod_time = mod_time
            
            # Renombrar archivos que no tienen formato correcto
            for file_path in files_to_rename:
                try:
                    old_filename = os.path.basename(file_path)
                    new_filename = generate_unique_filename()
                    new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    
                    # Renombrar el archivo
                    os.rename(file_path, new_path)
                    logger.info(f"Archivo renombrado automáticamente: {old_filename} -> {new_filename}")
                except Exception as e:
                    logger.error(f"Error al renombrar archivo {file_path}: {str(e)}")
            
            # Si hay cambios, actualizar la variable global
            if latest_mod_time > last_folder_modification or files_to_rename:
                last_folder_modification = latest_mod_time
                logger.info(f"Cambios detectados en la carpeta input: {datetime.fromtimestamp(latest_mod_time)}")
            
            # Esperar antes de la siguiente verificación
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error al monitorear la carpeta: {e}")
            time.sleep(5)  # Esperar más tiempo en caso de error

# Función decoradora para requerir login
def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return secure_function

# Función para verificar credenciales
def check_credentials(username, password):
    try:
        with open('users.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row['user'] == username and row['pass'] == password:
                    return True
        return False
    except Exception as e:
        logger.error(f"Error al verificar credenciales: {str(e)}")
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if check_credentials(username, password):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            flash('Has iniciado sesión correctamente', 'success')
            return redirect(url_for('index'))
        else:
            error = 'Usuario o contraseña incorrectos'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Ruta principal que muestra las imágenes de la carpeta de entrada."""
    images = get_images()
    username = session.get('username', '')
    return render_template('index.html', images=images, username=username)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Maneja la subida de nuevas imágenes."""
    if 'file' not in request.files:
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    files = request.files.getlist('file')
    
    uploaded_files = []
    for file in files:
        if file.filename == '':
            continue
        
        if file and file.filename.lower().endswith(('.jpg', '.jpeg')):
            # Generar un nombre de archivo único
            new_filename = generate_unique_filename()
            
            # Guardar el archivo con el nuevo nombre
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)
            uploaded_files.append(new_filename)
            logger.info(f"Archivo subido y renombrado: {file.filename} -> {new_filename}")
    
    if uploaded_files:
        return jsonify({'success': True, 'files': uploaded_files}), 200
    else:
        return jsonify({'error': 'No se subieron archivos válidos'}), 400

@app.route('/refresh')
@login_required
def refresh_images():
    """Endpoint para actualizar las imágenes sin recargar la página completa."""
    latest_images = get_latest_images(app.config['UPLOAD_FOLDER'])
    images_data = [get_image_data(img) for img in latest_images]
    
    # Si no hay imágenes, mostrar mensaje
    if not images_data:
        images_data.append({
            'name': 'No hay imágenes disponibles',
            'path': None,
            'data': None,
            'modified': 'N/A'
        })
    
    return jsonify(images_data)

@app.route('/check_updates')
def check_updates():
    """Endpoint para verificar si hay actualizaciones en la carpeta."""
    global last_folder_modification
    return jsonify({
        'last_modified': last_folder_modification,
        'timestamp': datetime.fromtimestamp(last_folder_modification).strftime('%Y-%m-%d %H:%M:%S') if last_folder_modification > 0 else 'N/A'
    })

@app.route('/delete/<filename>')
@login_required
def delete_image(filename):
    """Elimina una imagen específica."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        logger.info(f"Intentando eliminar archivo: {file_path}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Archivo eliminado exitosamente: {file_path}")
            return jsonify({'success': True}), 200
        
        logger.warning(f"Archivo no encontrado para eliminar: {file_path}")
        return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error al eliminar archivo {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/rotate/<filename>/<direction>')
@login_required
def rotate_image(filename, direction):
    """Rota una imagen en la dirección especificada."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        logger.info(f"Intentando rotar archivo: {file_path} en dirección: {direction}")
        
        if os.path.exists(file_path):
            with Image.open(file_path) as img:
                if direction == 'left':
                    rotated = img.rotate(90, expand=True)
                elif direction == 'right':
                    rotated = img.rotate(-90, expand=True)
                else:
                    logger.warning(f"Dirección de rotación inválida: {direction}")
                    return jsonify({'error': 'Dirección inválida'}), 400
                
                rotated.save(file_path)
                logger.info(f"Archivo rotado exitosamente: {file_path}")
                return jsonify({'success': True}), 200
        
        logger.warning(f"Archivo no encontrado para rotar: {file_path}")
        return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error al rotar archivo {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/scan')
@login_required
def scan_documents():
    """Ejecuta la acción de cambiar a ventana Scan Validation y hacer clic."""
    try:
        logger.info("Iniciando proceso de escaneo mediante cambio de ventana")
        
        # Importar módulos necesarios
        import win32gui
        import re
        import pyautogui
        import time
        
        # Función para encontrar ventana por título
        def find_window_with_title(title_pattern):
            """Encuentra ventanas que coinciden con un patrón en su título"""
            result = []
            
            def callback(hwnd, pattern):
                window_title = win32gui.GetWindowText(hwnd)
                if re.search(pattern, window_title, re.IGNORECASE) and win32gui.IsWindowVisible(hwnd):
                    result.append((hwnd, window_title))
                return True
            
            win32gui.EnumWindows(callback, title_pattern)
            return result
        
        # Buscar la ventana "Scan Validation"
        windows = find_window_with_title("Scan Validation")
        
        if windows:
            hwnd, title = windows[0]  # Tomar la primera ventana encontrada
            
            # Activar la ventana encontrada
            win32gui.SetForegroundWindow(hwnd)
            
            # Obtener la posición y tamaño de la ventana
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            
            # Añadir un pequeño retraso para asegurar que la ventana está activa
            time.sleep(0.5)
            
            # Las coordenadas relativas (47, 61) para el clic
            x_rel, y_rel = 47, 61
            
            # Convertir a coordenadas absolutas
            x_abs = left + x_rel
            y_abs = top + y_rel
            
            # Hacer clic en las coordenadas calculadas
            pyautogui.click(x_abs, y_abs)
            
            logger.info(f"Ventana '{title}' activada y clic realizado en posición relativa ({x_rel}, {y_rel})")
            return jsonify({
                'success': True, 
                'output': f"Ventana '{title}' activada y clic realizado en posición relativa ({x_rel}, {y_rel})"
            }), 200
        else:
            logger.error("No se encontró ninguna ventana con 'Scan Validation' en su título")
            return jsonify({
                'success': False, 
                'error': "No se encontró ninguna ventana con 'Scan Validation' en su título"
            }), 404
            
    except Exception as e:
        logger.error(f"Error al ejecutar acción de escaneo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ocr')
@login_required
def execute_ocr():
    """Ejecuta el script de OCR para extraer texto de las imágenes y busca Proyectos."""
    try:
        # Verificar si se especificó un archivo específico
        filename = request.args.get('filename')
        
        # Obtener las imágenes a procesar
        if filename:
            # Procesar solo la imagen especificada
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(image_path):
                return jsonify({'success': False, 'error': f'Archivo no encontrado: {filename}'}), 404
            image_files = [image_path]
        else:
            # Si no se especificó, usar todas las imágenes disponibles
            image_files = get_latest_images(folder=app.config['UPLOAD_FOLDER'])
        
        if not image_files:
            return jsonify({'success': False, 'error': 'No hay imágenes disponibles para OCR'}), 400
        
        logger.info(f"Ejecutando OCR en {len(image_files)} imágenes")
        
        try:
            # Importar pytesseract
            from PIL import Image as PILImage
            import pytesseract
            import re
            
            # Procesar todas las imágenes y recopilar texto
            all_ocr_text = ""
            processed_files = []
            
            for image_path in image_files:
                img = PILImage.open(image_path)
                current_text = pytesseract.image_to_string(img, lang='spa')
                all_ocr_text += current_text + "\n"
                processed_files.append(os.path.basename(image_path))
                logger.info(f"OCR completado para: {os.path.basename(image_path)}")
            
            # Buscar el patrón de Proyecto: 2301 seguido de 1-2 letras mayúsculas y 4 dígitos
            matricula_pattern = r'2301[A-Z]{1,2}\d{4}'
            matriculas_encontradas = re.findall(matricula_pattern, all_ocr_text)
            
            # Importar la función para extraer datos del estudiante si es necesario
            from functions.test_ocr import extract_student_data
            student_data = extract_student_data(all_ocr_text)
            
            # Añadir proyecto encontrada a los datos del estudiante
            if matriculas_encontradas and len(matriculas_encontradas) > 0:
                student_data['matricula'] = matriculas_encontradas[0]
                logger.info(f"Proyecto encontrada: {matriculas_encontradas[0]}")
            else:
                student_data['matricula'] = None
                logger.info("No se encontró ningun proyecto con el formato 2301[A-Z]{1,2}\\d{4}")
            
            # Si se encontraron múltiples coincidencias, guardarlas todas
            if len(matriculas_encontradas) > 1:
                student_data['todas_matriculas'] = matriculas_encontradas
            
            # Verificar y mostrar la respuesta antes de enviarla
            logger.info(f"Respuesta final OCR - Datos extraídos: {student_data}")
            
            return jsonify({
                'success': True, 
                'output': 'OCR ejecutado en todas las imágenes',
                'ocr_text': all_ocr_text,
                'student_data': student_data,
                'processed_files': processed_files,
                'matriculas_encontradas': matriculas_encontradas
            }), 200
            
        except Exception as inner_e:
            logger.error(f"Error en procesamiento directo: {str(inner_e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': f"Error en procesamiento OCR: {str(inner_e)}"}), 500
        
    except Exception as e:
        error_msg = f"Error al ejecutar OCR: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/clear_input')
@login_required
def clear_input():
    """Elimina todas las imágenes de la carpeta input."""
    try:
        input_folder = app.config['UPLOAD_FOLDER']
        
        # Contar archivos antes de eliminar
        files_count = 0
        for file in os.listdir(input_folder):
            if file.lower().endswith(('.jpg', '.jpeg')):
                file_path = os.path.join(input_folder, file)
                os.remove(file_path)
                files_count += 1
                logger.info(f"Archivo eliminado: {file_path}")
        
        logger.info(f"Se eliminaron {files_count} archivos de la carpeta input")
        return jsonify({'success': True, 'message': f'Se eliminaron {files_count} archivos'}), 200
    except Exception as e:
        logger.error(f"Error al limpiar la carpeta input: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def start_folder_monitor():
    """Inicia el hilo de monitoreo de la carpeta."""
    monitor_thread = threading.Thread(target=check_folder_changes, daemon=True)
    monitor_thread.start()
    return monitor_thread

@app.route('/buscar_folio/<folio>')
@login_required
def buscar_folio(folio):
    """Busca un folio en el CSV y devuelve los datos asociados."""
    try:
        # Importar la función desde el módulo
        from functions.procesar_documento import buscar_por_folio
        
        # Verificar que el archivo CSV existe
        csv_path = 'db_input.csv'
        if not os.path.exists(csv_path):
            error_msg = f"Archivo CSV no encontrado: {csv_path}"
            logger.error(error_msg)
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Buscar el folio
        datos = buscar_por_folio(folio)
        
        if datos:
            return jsonify({'success': True, 'datos': datos}), 200
        else:
            # Obtener algunos folios disponibles para ayudar en la depuración
            folios_disponibles = []
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    csv_reader = csv.DictReader(file)
                    folios_disponibles = [row.get('folio', '') for row in csv_reader][:5]
            except Exception as e:
                logger.error(f"Error al leer folios disponibles: {str(e)}")
            
            error_msg = f"Folio '{folio}' no encontrado. Ejemplos de folios disponibles: {folios_disponibles}"
            logger.warning(error_msg)
            return jsonify({
                'success': False, 
                'error': 'Folio no encontrado',
                'message': error_msg,
                'folios_ejemplo': folios_disponibles
            }), 404
    except Exception as e:
        error_msg = f"Error al buscar folio: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/generar_pdf', methods=['POST'])
@login_required
def generar_pdf():
    """Genera un PDF con las imágenes seleccionadas y actualiza el CSV."""
    try:
        # Obtener datos del request
        data = request.json
        rut_number = data.get('rutNumber', '')
        rut_dv = data.get('rutDV', '')
        folio = data.get('folio', '')
        selected_images = data.get('selectedImages', [])
        
        # Nuevos campos
        documento_presente = data.get('documentoPresente', 'SI')
        observacion = data.get('observacion', '')
        
        if not rut_number or not rut_dv or not folio:
            return jsonify({'success': False, 'error': 'Faltan datos necesarios'}), 400
        
        # Crear carpeta para PDFs si no existe
        pdf_folder = 'pdf_procesado'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Nombre del archivo PDF
        filename = f"{rut_number}{rut_dv}_{folio}.pdf"
        pdf_path = os.path.join(pdf_folder, filename)
        
        # Si no se especificaron imágenes, usar todas las disponibles
        if not selected_images:
            image_files = get_latest_images(folder=app.config['UPLOAD_FOLDER'])
        else:
            # Usar las imágenes seleccionadas
            image_files = [os.path.join(app.config['UPLOAD_FOLDER'], img) for img in selected_images]
        
        if not image_files and documento_presente == 'SI':
            return jsonify({'success': False, 'error': 'No hay imágenes para generar el PDF'}), 400
        
        # Crear el PDF con las imágenes si el documento está presente
        if documento_presente == 'SI' and image_files:
            from PIL import Image
            from reportlab.lib.utils import ImageReader
            
            # Crear un PDF con las imágenes
            c = canvas.Canvas(pdf_path, pagesize=letter)
            
            # Añadir cada imagen como una página del PDF
            for img_path in image_files:
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
        elif documento_presente == 'NO':
            # Si el documento no está presente, crear un PDF simple con la observación
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(letter[0]/2, letter[1]/2 + 40, "DOCUMENTO NO PRESENTE")
            
            if observacion:
                c.setFont("Helvetica", 12)
                c.drawCentredString(letter[0]/2, letter[1]/2, "Observación:")
                # Dividir la observación en líneas si es muy larga
                c.setFont("Helvetica", 10)
                text_object = c.beginText(letter[0]/4, letter[1]/2 - 20)
                for line in observacion.split('\n'):
                    text_object.textLine(line)
                c.drawText(text_object)
            
            c.save()
        
        # Actualizar el CSV con el nombre del documento, estado y observación
        actualizar_csv(folio, filename, documento_presente, observacion)
        
        logger.info(f"PDF generado correctamente: {pdf_path}")
        return jsonify({'success': True, 'filename': filename}), 200
    
    except Exception as e:
        error_msg = f"Error al generar PDF: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

def actualizar_csv(folio, nombre_documento, documento_presente='SI', observacion=''):
    """Actualiza el CSV con el nombre del documento, estado y observación."""
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
            
            # Añadir nuevos campos si no existen
            if 'documento_presente' not in fieldnames:
                fieldnames.append('documento_presente')
            if 'observacion' not in fieldnames:
                fieldnames.append('observacion')
            
            csv_writer = csv.DictWriter(file_out, fieldnames=fieldnames)
            csv_writer.writeheader()
            
            for row in csv_reader:
                if row.get('folio') == folio:
                    row['nombre_documento'] = nombre_documento
                    row['documento_presente'] = documento_presente
                    row['observacion'] = observacion
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

@app.route('/buscar_codigo/<codigo>')
@login_required
def buscar_codigo(codigo):
    """Busca un código en el CSV y devuelve los datos asociados."""
    try:
        csv_path = 'db_input.csv'
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': 'Archivo CSV no encontrado'}), 404
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row.get('CODIGO') == codigo:
                    # Asegurarse de que se incluye el campo CAJA en la respuesta
                    proyecto = {
                        'CODIGO': row.get('CODIGO', ''),
                        'NOMBRE_INICIATIVA': row.get('NOMBRE_INICIATIVA', ''),
                        'CAJA': row.get('CAJA', ''),
                        'DOC_PRESENTE': row.get('DOC_PRESENTE', 'SI'),
                        'OBSERVACION': row.get('OBSERVACION', '')
                    }
                    return jsonify({'success': True, 'proyecto': proyecto}), 200
        
        # Si llegamos aquí, el código no se encontró
        return jsonify({'success': False, 'error': 'Código no encontrado'}), 404
    
    except Exception as e:
        error_msg = f"Error al buscar código: {str(e)}"
        logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/procesar_documento', methods=['POST'])
@login_required
def procesar_documento():
    """Procesa el documento, genera PDF con texto seleccionable y actualiza CSV."""
    try:
        data = request.json
        codigo = data.get('codigo', '').strip()
        documento_presente = data.get('documentoPresente', 'SI')
        observacion = data.get('observacion', '')
        selected_images = data.get('selectedImages', [])
        box_number = data.get('boxNumber', '')  # Nuevo campo para número de caja
        
        if not codigo:
            return jsonify({'success': False, 'error': 'Falta el código del proyecto'}), 400
        
        # Crear carpeta para PDFs si no existe
        pdf_folder = 'pdf_procesado'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Nombre del archivo PDF (código del proyecto)
        pdf_filename = f"{codigo}.pdf"
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        
        # Obtener rutas completas de las imágenes seleccionadas
        image_files = []
        for img in selected_images:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], img)
            if os.path.exists(img_path):
                image_files.append(img_path)
        
        # Si documento presente = SI, verificar que hay imágenes
        if documento_presente == 'SI' and not image_files:
            return jsonify({'success': False, 'error': 'No hay imágenes para generar el PDF y el documento está marcado como presente'}), 400
        
        if documento_presente == 'SI' and image_files:
            # Crear PDF con OCR
            create_searchable_pdf(image_files, pdf_path, codigo)
            logger.info(f"PDF con texto seleccionable generado: {pdf_path}")
            
        else:  # documento_presente == 'NO'
            # Crear PDF simple con mensaje de documento no presente
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(letter[0]/2, letter[1]/2 + 40, "DOCUMENTO NO PRESENTE")
            
            if observacion:
                c.setFont("Helvetica", 12)
                c.drawCentredString(letter[0]/2, letter[1]/2, "Observación:")
                
                # Dividir la observación en líneas si es muy larga
                c.setFont("Helvetica", 10)
                text_object = c.beginText(letter[0]/4, letter[1]/2 - 20)
                for line in observacion.split('\n'):
                    text_object.textLine(line)
                c.drawText(text_object)
            
            c.save()
            logger.info(f"PDF de documento no presente generado: {pdf_path}")
        
        # Actualizar CSV con la información
        if actualizar_csv_proyecto(codigo, pdf_path, documento_presente, observacion, box_number):
            logger.info(f"CSV actualizado para código: {codigo}")
        else:
            logger.warning(f"No se pudo actualizar el CSV para código: {codigo}")
        
        # Limpiar la carpeta de entrada
        if limpiar_input_folder():
            logger.info("Carpeta input limpiada correctamente")
        else:
            logger.warning("No se pudo limpiar la carpeta input")
        
        return jsonify({
            'success': True, 
            'pdf_filename': pdf_filename,
            'message': 'Documento procesado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error al procesar documento: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

def actualizar_csv_proyecto(codigo, pdf_path, doc_presente='SI', observacion='', box_number=''):
    """Actualiza o añade una entrada en el CSV para el proyecto."""
    try:
        csv_path = 'db_input.csv'
        temp_file = 'db_input_temp.csv'
        
        # Verificar si el archivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV no encontrado: {csv_path}")
            return False
        
        # Leer el CSV y buscar si existe el código
        codigo_encontrado = False
        rows = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            fieldnames = csv_reader.fieldnames
            
            # Asegurarse de que los campos necesarios existan
            if 'DOC_PRESENTE' not in fieldnames:
                fieldnames.append('DOC_PRESENTE')
            if 'OBSERVACION' not in fieldnames:
                fieldnames.append('OBSERVACION')
            if 'PDF_PATH' not in fieldnames:
                fieldnames.append('PDF_PATH')
            
            # Guardar todas las filas
            for row in csv_reader:
                if row.get('CODIGO') == codigo:
                    row['DOC_PRESENTE'] = doc_presente
                    row['OBSERVACION'] = observacion
                    row['PDF_PATH'] = pdf_path
                    if box_number:  # Solo actualizar si se proporciona un valor
                        row['CAJA'] = box_number
                    codigo_encontrado = True
                rows.append(row)
        
        # Si el código no existe, añadir una nueva fila
        if not codigo_encontrado:
            new_row = {field: '' for field in fieldnames}
            new_row['CODIGO'] = codigo
            new_row['DOC_PRESENTE'] = doc_presente
            new_row['OBSERVACION'] = observacion
            new_row['PDF_PATH'] = pdf_path
            if box_number:
                new_row['CAJA'] = box_number
            rows.append(new_row)
        
        # Escribir todas las filas de vuelta al CSV
        with open(temp_file, 'w', newline='', encoding='utf-8') as file:
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(rows)
        
        # Reemplazar el archivo original con el temporal
        os.replace(temp_file, csv_path)
        logger.info(f"CSV actualizado correctamente para el código {codigo}")
        return True
    
    except Exception as e:
        logger.error(f"Error al actualizar CSV: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def limpiar_input_folder():
    """Elimina todos los archivos de la carpeta input."""
    try:
        input_folder = app.config['UPLOAD_FOLDER']
        for file in os.listdir(input_folder):
            file_path = os.path.join(input_folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        logger.info("Carpeta input limpiada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al limpiar carpeta input: {str(e)}")
        return False

def get_images():
    """Obtiene las imágenes de la carpeta de entrada y las prepara para mostrar."""
    latest_images = get_latest_images(app.config['UPLOAD_FOLDER'])
    
    # Preparar datos de imágenes
    images_data = []
    for img_path in latest_images:
        images_data.append(get_image_data(img_path))
    
    # Si no hay imágenes, mostrar mensaje
    if not images_data:
        images_data.append({
            'name': 'No hay imágenes disponibles',
            'path': None,
            'data': None,
            'modified': 'N/A'
        })
    
    return images_data

@app.route('/generar_cuadratura')
@login_required
def generar_cuadratura():
    """Genera un archivo Excel con los datos del CSV."""
    try:
        # Crear carpeta excel si no existe
        excel_folder = 'excel'
        os.makedirs(excel_folder, exist_ok=True)
        
        # Leer el CSV
        csv_path = 'db_input.csv'
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': 'Archivo CSV no encontrado'}), 404
        
        df = pd.read_csv(csv_path)
        
        # Crear un archivo Excel en memoria
        output = BytesIO()
        
        # Crear un writer de Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Convertir DataFrame a Excel
            df.to_excel(writer, sheet_name='Cuadratura', index=False)
            
            # Obtener el objeto workbook y worksheet
            workbook = writer.book
            worksheet = writer.sheets['Cuadratura']
            
            # Formato para los encabezados
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Aplicar formato a los encabezados
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Ancho de columna
            
            # Autoajustar columnas
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).map(len).max(), len(col))
                worksheet.set_column(i, i, column_len + 2)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"cuadratura_{timestamp}.xlsx"
        excel_path = os.path.join(excel_folder, excel_filename)
        
        # Guardar el Excel en el sistema de archivos
        with open(excel_path, 'wb') as f:
            f.write(output.getvalue())
        
        # Configurar la respuesta para descargar el archivo
        output.seek(0)
        
        logger.info(f"Cuadratura generada: {excel_filename}")
        
        # Devolver el archivo para descarga
        return send_file(
            BytesIO(output.getvalue()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=excel_filename
        )
        
    except Exception as e:
        logger.error(f"Error al generar cuadratura: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

# Nueva función para crear PDF con texto seleccionable
def create_searchable_pdf(image_files, output_path, codigo):
    """Crea un PDF con texto seleccionable a partir de las imágenes."""
    try:
        from PIL import Image
        import pytesseract
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from io import BytesIO
        from PyPDF2 import PdfWriter, PdfReader
        
        merger = PdfWriter()
        
        for img_path in image_files:
            try:
                # Abrir la imagen
                img = Image.open(img_path)
                
                # Realizar OCR para obtener texto
                ocr_data = pytesseract.image_to_data(img, lang='spa', output_type=pytesseract.Output.DICT)
                
                # Crear PDF temporal con la imagen
                temp_img_pdf = BytesIO()
                img_width, img_height = img.size
                
                # Crear PDF con la imagen
                c = canvas.Canvas(temp_img_pdf, pagesize=letter)
                page_width, page_height = letter
                
                # Ajustar tamaño para que quepa en la página
                ratio = min(page_width / img_width, page_height / img_height) * 0.9
                new_width = img_width * ratio
                new_height = img_height * ratio
                
                # Posicionar en el centro de la página
                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2
                
                c.drawImage(ImageReader(img), x, y, width=new_width, height=new_height)
                c.save()
                
                # Crear PDF temporal con el texto (invisible)
                temp_text_pdf = BytesIO()
                c = canvas.Canvas(temp_text_pdf, pagesize=letter)
                
                # Configurar texto invisible
                c.setFillColorRGB(0, 0, 0, 0)  # Texto totalmente transparente
                
                # Recorrer los resultados del OCR y colocar cada palabra en su posición
                for i in range(len(ocr_data['text'])):
                    text = ocr_data['text'][i].strip()
                    
                    if text and ocr_data['conf'][i] > 30:  # Solo texto con cierta confianza
                        # Calcular posición ajustada
                        orig_x = ocr_data['left'][i]
                        orig_y = ocr_data['top'][i]
                        
                        # Convertir a coordenadas de la página PDF
                        pdf_x = x + (orig_x * ratio)
                        # Invertir el eje Y ya que en PDF el origen está abajo
                        pdf_y = page_height - (y + (orig_y * ratio))
                        
                        # Ajustar por la altura del texto
                        pdf_y -= (ocr_data['height'][i] * ratio)
                        
                        # Dibujar el texto en su posición correspondiente
                        c.setFont("Helvetica", 10)
                        c.drawString(pdf_x, pdf_y, text)
                
                # Añadir código de proyecto como texto visible
                c.setFillColorRGB(0, 0, 0, 1)  # Negro normal
                c.setFont("Helvetica", 8)
                c.drawString(20, 20, f"Código: {codigo}")
                
                c.save()
                
                # Combinar ambos PDFs
                img_pdf = PdfReader(temp_img_pdf)
                text_pdf = PdfReader(temp_text_pdf)
                
                page = img_pdf.pages[0]
                page.merge_page(text_pdf.pages[0])
                
                merger.add_page(page)
                
            except Exception as e:
                logger.error(f"Error procesando imagen {img_path}: {str(e)}")
                # Si hay error con una imagen, continuar con las siguientes
        
        # Guardar el PDF final
        with open(output_path, 'wb') as f:
            merger.write(f)
        
        return True
        
    except Exception as e:
        logger.error(f"Error al crear PDF con texto seleccionable: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # En caso de error, intentar crear un PDF básico sin OCR
        try:
            from PIL import Image
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            
            c = canvas.Canvas(output_path, pagesize=letter)
            
            for img_path in image_files:
                try:
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
                except Exception as e2:
                    logger.error(f"Error en método alternativo para {img_path}: {str(e2)}")
            
            c.save()
            logger.warning("Se creó un PDF sin OCR debido a errores.")
            return False
            
        except Exception as e2:
            logger.error(f"Error en el método alternativo para crear PDF: {str(e2)}")
            raise e  # Re-lanzar la excepción original

if __name__ == '__main__':
    # Verificar que existan las carpetas necesarias
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Iniciar el monitoreo de la carpeta en un hilo separado
    monitor_thread = start_folder_monitor()
    
    # Iniciar la aplicación Flask
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    # Cuando la aplicación se cierre, detener el monitoreo
    folder_monitor_active = False
    if monitor_thread.is_alive():
        monitor_thread.join(timeout=1)
