from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
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

# Importar funciones personalizadas
from functions.procesar_documento import procesar_y_subir_documento, buscar_por_folio, actualizar_csv

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

@app.route('/switch_user')
def switch_user():
    """Cierra la sesión actual y redirecciona a login para cambiar de usuario."""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Selecciona un usuario diferente para iniciar sesión', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Página principal que muestra todas las imágenes disponibles."""
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
    
    return render_template('index.html', images=images_data, username=session.get('username', ''))

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
    latest_images = get_latest_images(folder=app.config['UPLOAD_FOLDER'])
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
    """Ejecuta el script de escaneo."""
    try:
        # Ruta al script de escaneo
        script_path = os.path.join('functions', 'gen_test_input.py')
        
        # Verificar si el script existe
        if not os.path.exists(script_path):
            logger.error(f"Script de escaneo no encontrado: {script_path}")
            return jsonify({'success': False, 'error': 'Script de escaneo no encontrado'}), 404
        
        # Ejecutar el script usando sys.executable (el python actual)
        import sys
        logger.info(f"Ejecutando script de escaneo: {script_path}")
        result = subprocess.run([sys.executable, script_path], 
                               capture_output=True, 
                               text=False)  # Cambiar a False para manejar bytes
        
        # Decodificar la salida manualmente con codificación adecuada para Windows
        stdout = ""
        stderr = ""
        try:
            if result.stdout:
                stdout = result.stdout.decode('cp1252', errors='replace')
            if result.stderr:
                stderr = result.stderr.decode('cp1252', errors='replace')
        except UnicodeDecodeError:
            # Fallback a otra codificación si cp1252 falla
            if result.stdout:
                stdout = result.stdout.decode('latin-1', errors='replace')
            if result.stderr:
                stderr = result.stderr.decode('latin-1', errors='replace')
        
        if result.returncode == 0:
            logger.info("Escaneo completado con éxito")
            return jsonify({'success': True, 'output': stdout}), 200
        else:
            logger.error(f"Error al ejecutar el script de escaneo: {stderr}")
            return jsonify({'success': False, 'error': stderr}), 500
    except Exception as e:
        logger.error(f"Error al ejecutar el escaneo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ocr')
@login_required
def execute_ocr():
    """Ejecuta el script de OCR para extraer texto de las imágenes."""
    try:
        # Verificar si se especificaron archivos específicos
        filename = request.args.get('filename')
        second_image = request.args.get('second_image')
        
        # Obtener las imágenes a procesar
        if filename:
            # Procesar las imágenes especificadas
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(image_path):
                return jsonify({'success': False, 'error': f'Archivo no encontrado: {filename}'}), 404
            
            # Obtener todas las imágenes y ordenarlas
            all_images = []
            for file in os.listdir(app.config['UPLOAD_FOLDER']):
                if file.lower().endswith(('.jpg', '.jpeg')):
                    all_images.append(os.path.join(app.config['UPLOAD_FOLDER'], file))
            
            # Ordenar por nombre de archivo
            all_images.sort()
            
            # Encontrar los índices de las imágenes actuales
            current_index = next((i for i, path in enumerate(all_images) if os.path.basename(path) == filename), -1)
            second_index = next((i for i, path in enumerate(all_images) if os.path.basename(path) == second_image), -1) if second_image else -1
            
            if current_index == -1:
                return jsonify({'success': False, 'error': f'No se pudo encontrar el archivo en la lista: {filename}'}), 404
            
            # Tomar las imágenes especificadas
            image_files = [all_images[current_index]]
            if second_index != -1:
                image_files.append(all_images[second_index])
                logger.info(f"Imagen actual: {filename}, segunda imagen: {second_image}")
            else:
                logger.info(f"No hay segunda imagen disponible para {filename}")
        else:
            # Si no se especificó, usar las dos imágenes más recientes
            image_files = get_latest_images(folder=app.config['UPLOAD_FOLDER'], count=2)
        
        if not image_files:
            return jsonify({'success': False, 'error': 'No hay imágenes disponibles para OCR'}), 400
        
        logger.info(f"Total de imágenes a procesar: {len(image_files)}")
        for img in image_files:
            logger.info(f"Imagen en lista: {os.path.basename(img)}")
        
        # Procesar las imágenes en orden
        final_student_data = {}
        processed_files = []
        all_ocr_texts = []
        
        # Procesar la primera imagen
        first_image_path = image_files[0]
        logger.info(f"Ejecutando OCR en primera imagen: {first_image_path}")
        
        try:
            # Procesamiento directo con pytesseract
            from PIL import Image as PILImage
            import pytesseract
            img = PILImage.open(first_image_path)
            ocr_text = pytesseract.image_to_string(img, lang='spa')
            
            # Importar la función para extraer datos del estudiante
            from functions.test_ocr import extract_student_data
            student_data = extract_student_data(ocr_text)
            
            # Guardar los datos encontrados
            if student_data:
                final_student_data.update(student_data)
                logger.info(f"Datos encontrados en primera imagen: {student_data}")
            else:
                logger.info("No se encontraron datos en la primera imagen")
            
            # Guardar el texto OCR de esta imagen
            all_ocr_texts.append({
                'file': os.path.basename(first_image_path),
                'text': ocr_text
            })
            processed_files.append(os.path.basename(first_image_path))
            
        except Exception as e:
            logger.error(f"Error en procesamiento de primera imagen {first_image_path}: {str(e)}")
        
        # Verificar si necesitamos procesar la segunda imagen
        needs_second_image = len(image_files) > 1 and (not final_student_data.get('rut') or not final_student_data.get('folio'))
        logger.info(f"¿Necesita segunda imagen? {needs_second_image}")
        logger.info(f"Datos actuales: {final_student_data}")
        
        if needs_second_image:
            second_image_path = image_files[1]
            logger.info(f"Ejecutando OCR en segunda imagen: {second_image_path}")
            
            try:
                # Procesamiento directo con pytesseract
                img = PILImage.open(second_image_path)
                ocr_text = pytesseract.image_to_string(img, lang='spa')
                
                # Extraer datos del estudiante
                student_data = extract_student_data(ocr_text)
                
                # Actualizar solo los campos que faltan
                if student_data:
                    logger.info(f"Datos encontrados en segunda imagen: {student_data}")
                    for key, value in student_data.items():
                        if key not in final_student_data or not final_student_data[key]:
                            final_student_data[key] = value
                            logger.info(f"Actualizando {key} con valor {value}")
                else:
                    logger.info("No se encontraron datos en la segunda imagen")
                
                # Guardar el texto OCR de esta imagen
                all_ocr_texts.append({
                    'file': os.path.basename(second_image_path),
                    'text': ocr_text
                })
                processed_files.append(os.path.basename(second_image_path))
                
            except Exception as e:
                logger.error(f"Error en procesamiento de segunda imagen {second_image_path}: {str(e)}")
        
        # Verificar y mostrar la respuesta antes de enviarla
        logger.info(f"Respuesta final OCR - Datos extraídos: {final_student_data}")
        logger.info(f"Imágenes procesadas: {processed_files}")
        
        return jsonify({
            'success': True, 
            'output': 'OCR ejecutado directamente',
            'ocr_texts': all_ocr_texts,
            'student_data': final_student_data,
            'processed_files': processed_files
        }), 200
            
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
        # Obtener el RUT de la solicitud (si está disponible)
        rut = request.args.get('rut', '')
        
        # Importar la función de verificación desde new_folio.py
        from functions.new_folio import verificar_folio_existe, buscar_actualizar_folio
        
        # Buscar el folio
        datos = buscar_por_folio(folio)
        
        if datos:
            # Si hay datos, obtener el RUT completo
            rut_completo = f"{datos.get('rut', '')}-{datos.get('dig_ver', '')}"
            
            # Importar y llamar a buscar_actualizar_folio para mostrar la alerta
            resultado_busqueda = buscar_actualizar_folio(rut_completo, folio)
            
            # Añadir el mensaje a los datos de respuesta
            datos['mensaje_alerta'] = resultado_busqueda.get('message', '')
            
            return jsonify({'success': True, 'datos': datos}), 200
        else:
            # Si no se encuentra localmente, intentar obtenerlo de la API
            logger.info(f"Folio '{folio}' no encontrado localmente. Intentando obtener de la API...")
            
            # Construir el RUT completo si está disponible
            rut_completo = rut if rut else ""
            
            # Llamar a la API para obtener los datos
            resultado_api = buscar_actualizar_folio(rut_completo, folio)
            
            if resultado_api.get('success', False):
                # Si la API devuelve datos, buscar nuevamente en el CSV local
                logger.info(f"Datos obtenidos de la API para folio '{folio}'. Buscando en CSV actualizado...")
                datos_actualizados = buscar_por_folio(folio)
                
                if datos_actualizados:
                    datos_actualizados['mensaje_alerta'] = resultado_api.get('message', 'Datos actualizados correctamente desde la API')
                    return jsonify({'success': True, 'datos': datos_actualizados}), 200
                else:
                    # Si por alguna razón no se encuentra en el CSV después de actualizar
                    return jsonify({
                        'success': False, 
                        'error': 'Error inesperado al recuperar los datos actualizados',
                        'message': 'La API devolvió datos pero no se pudieron recuperar del CSV'
                    }), 500
            
            # Si la API tampoco encuentra el folio, obtener algunos folios disponibles para ayudar en la depuración
            folios_disponibles = []
            try:
                csv_path = 'db_input.csv'
                with open(csv_path, 'r', encoding='utf-8') as file:
                    csv_reader = csv.DictReader(file)
                    folios_disponibles = [row.get('folio', '') for row in csv_reader][:5]
            except Exception as e:
                logger.error(f"Error al leer folios disponibles: {str(e)}")
            
            error_msg = f"Folio '{folio}' no encontrado. Ejemplos de folios disponibles: {folios_disponibles}"
            logger.warning(error_msg)
            
            # Devolver también el mensaje de la API para más información
            api_message = resultado_api.get('message', 'No se encontró el folio en el sistema')
            
            return jsonify({
                'success': False, 
                'error': 'Folio no encontrado',
                'message': error_msg,
                'api_message': api_message,
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
        
        if not rut_number or not rut_dv or not folio:
            return jsonify({'success': False, 'error': 'Faltan datos necesarios'}), 400
        
        # Construir el RUT completo
        rut_completo = f"{rut_number}-{rut_dv}"
        
        # Obtener el nombre de usuario de la sesión
        usuario = session.get('username', 'Sistema')
        
        logger.info(f"Iniciando generación de PDF para RUT: {rut_completo}, Folio: {folio}, Usuario: {usuario}")
        logger.info(f"Orden de imágenes proporcionado: {selected_images}")
        
        # Inicializar resultado_api como None
        resultado_api = None
        
        # Verificar primero si el folio existe en el sistema
        from functions.new_folio import verificar_folio_existe, buscar_actualizar_folio
        
        if not verificar_folio_existe(folio):
            logger.info(f"Folio {folio} no encontrado. Intentando actualizar desde API...")
            # Llamar a la función buscar_actualizar_folio para intentar obtener los datos de la API
            resultado_api = buscar_actualizar_folio(rut_completo, folio)
            
            if not resultado_api.get('success', False):
                # Crear un mensaje de error más descriptivo
                error_details = resultado_api.get('message', 'No se pudo obtener información de la API')
                error_type = resultado_api.get('error', 'UNKNOWN_ERROR')
                
                logger.error(f"Error al obtener datos de la API: {error_type} - {error_details}")
                
                return jsonify({
                    'success': False,
                    'error': f"El folio {folio} no existe en el sistema y no se pudo obtener de la API.",
                    'api_message': error_details,
                    'error_type': error_type
                }), 404
            
            logger.info(f"Folio {folio} actualizado exitosamente desde la API: {resultado_api.get('message')}")
        
        # 1. Usar la función procesar_y_subir_documento de procesar_documento.py
        resultado = procesar_y_subir_documento(rut_completo, folio, usuario, selected_images)
        
        if resultado.get('status') != 'success':
            logger.error(f"Error al procesar y subir documento: {resultado.get('message')}")
            return jsonify({
                'success': False, 
                'error': resultado.get('message', 'Error al procesar documento')
            }), 500
        
        # Agregar información adicional a la respuesta
        resultado['success'] = True
        resultado['rut'] = rut_completo
        resultado['folio'] = folio
        resultado['filename'] = os.path.basename(resultado.get('pdf_path', ''))
        
        # Agregar información sobre el formato de RUT usado si está disponible
        if resultado_api and 'data' in resultado_api and 'formato_rut_usado' in resultado_api['data']:
            resultado['formato_rut_usado'] = resultado_api['data']['formato_rut_usado']
        
        logger.info(f"PDF generado y enviado exitosamente: {resultado}")
        return jsonify(resultado), 200
    
    except Exception as e:
        error_msg = f"Error al generar PDF: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/exportar_gesdoc')
@login_required
def exportar_documentos_gesdoc():
    """Ejecuta la función de exportación a Gesdoc y devuelve los resultados."""
    try:
        # Obtener el nombre de usuario de la sesión
        usuario = session.get('username', 'Sistema')
        
        # Importar la función desde el módulo
        from functions.exportar_gesdoc import exportar_a_gesdoc
        
        # Ejecutar la función de exportación con el usuario actual
        resultado = exportar_a_gesdoc(usuario)
        
        # Retornar el resultado como JSON
        return jsonify(resultado), 200 if resultado['success'] else 400
    
    except Exception as e:
        error_msg = f"Error al exportar a Gesdoc: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'mensaje': error_msg
        }), 500

if __name__ == '__main__':
    # Verificar que existan las carpetas necesarias
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Asegurar que existe la carpeta para PDFs procesados
    os.makedirs('pdf_procesado', exist_ok=True)
    
    # Iniciar el monitoreo de la carpeta en un hilo separado
    monitor_thread = start_folder_monitor()
    
    # Iniciar la aplicación Flask
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    # Cuando la aplicación se cierre, detener el monitoreo
    folder_monitor_active = False
    if monitor_thread.is_alive():
        monitor_thread.join(timeout=1)
