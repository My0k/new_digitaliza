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

def get_image_data(image_path, thumbnail=True, max_size=800):
    """Obtiene los datos de una imagen para enviar al frontend.
    Si thumbnail es True, genera una versión comprimida de la imagen y la guarda en disco."""
    try:
        name = os.path.basename(image_path)
        modified_time = os.path.getmtime(image_path)
        modified = datetime.fromtimestamp(modified_time).strftime('%d/%m/%Y %H:%M:%S')
        
        # Codificar la imagen en base64 para enviarla, opcionalmente generando thumbnail
        try:
            if thumbnail:
                # Definir carpeta de miniaturas y asegurar que existe
                thumbnails_folder = 'miniaturas'
                os.makedirs(thumbnails_folder, exist_ok=True)
                
                # Crear nombre para la miniatura (mismo nombre con prefijo 'thumb_')
                thumb_name = f"thumb_{name}"
                thumb_path = os.path.join(thumbnails_folder, thumb_name)
                
                # Verificar si la miniatura ya existe y es más reciente que la imagen original
                thumb_exists = os.path.exists(thumb_path)
                
                if thumb_exists:
                    thumb_modified_time = os.path.getmtime(thumb_path)
                    # Si la imagen original es más reciente que la miniatura, recrearla
                    if modified_time > thumb_modified_time:
                        thumb_exists = False
                
                # Si la miniatura no existe o debe ser actualizada, crearla
                if not thumb_exists:
                    with Image.open(image_path) as img:
                        # Conservar la proporción de aspecto pero limitar tamaño máximo
                        img.thumbnail((max_size, max_size), Image.LANCZOS)
                        
                        # Convertir a RGB si es necesario (en caso de imágenes RGBA)
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                            background.paste(img, img.split()[-1])
                            img = background
                        
                        # Guardar la miniatura en disco
                        img.save(thumb_path, format="JPEG", quality=70, optimize=True)
                        logger.info(f"Miniatura creada: {thumb_path}")
                
                # Leer la miniatura desde el disco y codificarla
                with open(thumb_path, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                    data_url = f"data:image/jpeg;base64,{encoded_string}"
            else:
                # Usar la imagen original
                with open(image_path, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                    data_url = f"data:image/jpeg;base64,{encoded_string}"
        except Exception as e:
            logger.error(f"Error al codificar imagen {name}: {str(e)}")
            data_url = None
        
        # Forzar recolección de basura después de procesar la imagen
        import gc
        gc.collect()
        
        return {
            'name': name,
            'path': image_path,
            'data': data_url,
            'modified': modified,
            'is_thumbnail': thumbnail,
            'thumb_path': thumb_path if thumbnail and 'thumb_path' in locals() else None
        }
    except Exception as e:
        logger.error(f"Error al procesar imagen {image_path}: {str(e)}")
        return {
            'name': os.path.basename(image_path),
            'path': image_path,
            'data': None,
            'modified': 'Error',
            'is_thumbnail': False
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
    
    # Diccionario para rastrear archivos nuevos y sus tiempos de detección
    new_files_detected = {}
    
    while folder_monitor_active:
        try:
            # Verificar si la carpeta existe
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                ensure_input_folder()
                
            # Obtener la última modificación de la carpeta y verificar archivos nuevos
            latest_mod_time = 0
            current_time = time.time()
            
            # Verificar archivos en la carpeta
            for file in os.listdir(app.config['UPLOAD_FOLDER']):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                
                # Solo procesar archivos JPG
                if file.lower().endswith(('.jpg', '.jpeg')) and os.path.isfile(file_path):
                    mod_time = os.path.getmtime(file_path)
                    
                    # Verificar si el nombre del archivo ya tiene formato de timestamp+letras
                    filename_without_ext = os.path.splitext(file)[0]
                    # Verificar si el nombre tiene al menos 13 caracteres (timestamp) y los primeros 10+ son dígitos
                    is_correct_format = len(filename_without_ext) >= 13 and filename_without_ext[:-3].isdigit()
                    
                    if not is_correct_format:
                        # Si el archivo no está en el registro, añadirlo con el tiempo actual
                        if file_path not in new_files_detected:
                            new_files_detected[file_path] = current_time
                            logger.info(f"Nuevo archivo detectado: {file} - esperando 20 segundos antes de renombrar")
                    
                    if mod_time > latest_mod_time:
                        latest_mod_time = mod_time
            
            # Procesar los archivos que llevan más de 20 segundos detectados
            files_to_rename = []
            files_to_remove = []
            
            for file_path, detected_time in new_files_detected.items():
                # Verificar si aún existe (podría haber sido eliminado)
                if not os.path.exists(file_path):
                    files_to_remove.append(file_path)
                    continue
                
                # Si han pasado 20 segundos desde la detección, renombrar
                if current_time - detected_time >= 20:
                    files_to_rename.append(file_path)
                    files_to_remove.append(file_path)  # Remover de la lista después de renombrar
            
            # Eliminar archivos que ya no existen o van a ser renombrados de la lista de seguimiento
            for file_path in files_to_remove:
                new_files_detected.pop(file_path, None)
            
            # Renombrar archivos que han esperado 20 segundos
            for file_path in files_to_rename:
                try:
                    old_filename = os.path.basename(file_path)
                    new_filename = generate_unique_filename()
                    new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    
                    # Renombrar el archivo
                    os.rename(file_path, new_path)
                    logger.info(f"Archivo renombrado después de 20 segundos: {old_filename} -> {new_filename}")
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

def login_required(func):
    """Decorador para asegurar que el usuario está autenticado."""
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        # Para simplificar, siempre permitimos el acceso
        # En una aplicación real, verificaríamos la sesión
        return func(*args, **kwargs)
    return secure_function

def start_folder_monitor():
    """Inicia el monitoreo de la carpeta en un hilo separado."""
    monitor_thread = threading.Thread(target=check_folder_changes, daemon=True)
    monitor_thread.start()
    return monitor_thread

@app.route('/')
@login_required
def index():
    """Ruta principal que muestra la interfaz de usuario."""
    try:
        # Obtener las imágenes más recientes
        images = get_latest_images()
        
        # Transformar imágenes para la interfaz
        image_data = []
        for img_path in images:
            image_data.append(get_image_data(img_path))
        
        return render_template('index.html', images=image_data)
    except Exception as e:
        logger.error(f"Error al cargar índice: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template('error.html', error=str(e))

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
def refresh():
    """Obtiene las imágenes actuales de la carpeta input."""
    try:
        # Determinar si debemos mostrar las imágenes en orden inverso
        reverse = request.args.get('reverse', 'false').lower() == 'true'
        
        # Parámetro para decidir si usar miniaturas (por defecto, sí)
        use_thumbnails = request.args.get('thumbnails', 'true').lower() == 'true'
        
        # Obtener tamaño máximo de miniaturas (por defecto 800px)
        try:
            max_size = int(request.args.get('max_size', '800'))
        except ValueError:
            max_size = 800
        
        # Obtener imágenes de la carpeta input
        image_paths = get_latest_images()
        
        # Ordenar según la preferencia
        if reverse:
            image_paths.sort(key=os.path.getmtime)  # Más antiguas primero
        else:
            image_paths.sort(key=os.path.getmtime, reverse=True)  # Más recientes primero
        
        # Convertir a formato para UI, usando miniaturas
        image_data = [get_image_data(img, thumbnail=use_thumbnails, max_size=max_size) for img in image_paths]
        
        # Forzar recolección de basura después de procesar todas las imágenes
        import gc
        gc.collect()
        
        return jsonify(image_data)
    except Exception as e:
        error_msg = f"Error al refrescar imágenes: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

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
            return jsonify({'success': True, 'message': f'Archivo {filename} eliminado correctamente'}), 200
        
        logger.warning(f"Archivo no encontrado para eliminar: {file_path}")
        return jsonify({'error': 'Archivo no encontrado', 'path': file_path}), 404
    except Exception as e:
        logger.error(f"Error al eliminar archivo {filename}: {str(e)}")
        return jsonify({'error': str(e), 'path': os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))}), 500

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
        import win32con
        import re
        import pyautogui
        import time
        import ctypes
        
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
            
            # Intentar activar la ventana usando múltiples métodos en secuencia
            activation_success = False
            error_messages = []
            
            # Método 1: Usar ShowWindow y SetForegroundWindow con manejo de errores
            try:
                # Primero asegurarnos que la ventana esté visible
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.5)  # Dar tiempo para que la ventana se restaure
                win32gui.SetForegroundWindow(hwnd)
                activation_success = True
                logger.info(f"Método 1 exitoso para activar ventana '{title}'")
            except Exception as e1:
                error_messages.append(f"Método 1 fallido: {str(e1)}")
                logger.warning(f"Método 1 fallido: {str(e1)}")
                
                # Método 2: Usar AttachThreadInput
                try:
                    foreground_hwnd = win32gui.GetForegroundWindow()
                    foreground_thread = win32gui.GetWindowThreadProcessId(foreground_hwnd)[0]
                    target_thread = win32gui.GetWindowThreadProcessId(hwnd)[0]
                    
                    if foreground_thread != target_thread:
                        ctypes.windll.user32.AttachThreadInput(foreground_thread, target_thread, True)
                        win32gui.SetForegroundWindow(hwnd)
                        ctypes.windll.user32.AttachThreadInput(foreground_thread, target_thread, False)
                    else:
                        win32gui.SetForegroundWindow(hwnd)
                    
                    activation_success = True
                    logger.info(f"Método 2 exitoso para activar ventana '{title}'")
                except Exception as e2:
                    error_messages.append(f"Método 2 fallido: {str(e2)}")
                    logger.warning(f"Método 2 fallido: {str(e2)}")
                    
                    # Método 3: Simular Alt+Tab o usar BringWindowToTop
                    try:
                        # Obtener dimensiones de la pantalla para el método 3
                        screen_width, screen_height = pyautogui.size()
                        
                        # Intento usando BringWindowToTop
                        win32gui.BringWindowToTop(hwnd)
                        pyautogui.press('alt')  # A veces ayuda a activar la ventana
                        time.sleep(0.5)
                        
                        activation_success = True
                        logger.info(f"Método 3 exitoso para activar ventana '{title}'")
                    except Exception as e3:
                        error_messages.append(f"Método 3 fallido: {str(e3)}")
                        logger.warning(f"Método 3 fallido: {str(e3)}")
            
            # Si ningún método funcionó para activar la ventana, intentar hacer clic de todas formas
            if not activation_success:
                logger.warning("No se pudo activar la ventana, pero se intentará hacer clic de todas formas")
            
            # Obtener la posición y tamaño de la ventana
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            
            # Añadir un pequeño retraso 
            time.sleep(1.0)
            
            # Las coordenadas relativas para el clic (las mismas que en test_ubicacion.py)
            x_rel, y_rel = 47, 61
            
            # Convertir a coordenadas absolutas
            x_abs = left + x_rel
            y_abs = top + y_rel
            
            # Obtener dimensiones de la pantalla
            screen_width, screen_height = pyautogui.size()
            
            # Verificar que las coordenadas estén dentro de la pantalla
            if 0 <= x_abs < screen_width and 0 <= y_abs < screen_height:
                # Hacer clic en las coordenadas calculadas
                pyautogui.click(x_abs, y_abs)
                logger.info(f"Clic realizado en posición relativa ({x_rel}, {y_rel}) de la ventana '{title}'")
                
                return jsonify({
                    'success': True, 
                    'output': f"Ventana '{title}' encontrada y clic realizado en ({x_rel}, {y_rel})"
                }), 200
            else:
                logger.error(f"Coordenadas calculadas fuera de la pantalla: ({x_abs}, {y_abs})")
                return jsonify({
                    'success': False, 
                    'error': f"Coordenadas calculadas fuera de la pantalla: ({x_abs}, {y_abs})"
                }), 400
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
def ocr():
    """Ejecuta OCR en las imágenes seleccionadas."""
    try:
        # Determinar si estamos en modo Indexación o Digitalización
        folder_id = request.args.get('folder', None)
        filename = request.args.get('filename', None)
        
        # Determinar el directorio de las imágenes
        if folder_id:
            # Modo Indexación - usar carpeta numerada
            base_dir = os.path.join('carpetas', folder_id)
            logger.info(f"Ejecutando OCR en modo Indexación, carpeta: {folder_id}")
        else:
            # Modo Digitalización - usar carpeta input
            base_dir = app.config['UPLOAD_FOLDER']
            logger.info("Ejecutando OCR en modo Digitalización")
        
        # Verificar que el directorio existe
        if not os.path.exists(base_dir):
            return jsonify({
                'success': False,
                'error': f"El directorio {base_dir} no existe"
            }), 400
        
        # Obtener la imagen a procesar
        if filename:
            # Procesar solo el archivo específico
            image_path = os.path.join(base_dir, filename)
            if not os.path.exists(image_path):
                return jsonify({
                    'success': False,
                    'error': f"Archivo {filename} no encontrado"
                }), 404
                
            image_paths = [image_path]
        else:
            # Procesar todas las imágenes de la carpeta
            image_paths = glob.glob(os.path.join(base_dir, '*.jpg')) + glob.glob(os.path.join(base_dir, '*.jpeg'))
            
        # Si no hay imágenes, devolver error
        if not image_paths:
            return jsonify({
                'success': False,
                'error': "No hay imágenes para procesar"
            }), 400
            
        # Ordenar imágenes por fecha de modificación (más antiguas primero)
        image_paths.sort(key=os.path.getmtime)
        
        # Ejecutar OCR en cada imagen
        ocr_results = []
        extracted_info = {
            'project_code': None,
            'box_number': None,
            'observation': None
        }
        
        for img_path in image_paths:
            # Ejecutar OCR en la imagen
            try:
                # Usar Tesseract para extraer texto
                img_filename = os.path.basename(img_path)
                
                # Comando Tesseract (ajustar según la instalación y configuración)
                cmd = ['tesseract', img_path, 'stdout', '-l', 'spa']
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error en Tesseract: {stderr.decode('utf-8', errors='ignore')}")
                    text = ""
                else:
                    text = stdout.decode('utf-8', errors='ignore')
                
                # Actualizar el regex para buscar solamente el formato específico
                import re
                project_code_match = re.search(r'2301[A-Z]{1,2}\d{4}', text)
                if project_code_match and not extracted_info['project_code']:
                    extracted_info['project_code'] = project_code_match.group(0).strip()
                
                # Buscar número de caja (formato: números)
                box_number_match = re.search(r'[Cc]aja\s*(?:N[°º]?)?\s*:?\s*(\d+)', text)
                if box_number_match and not extracted_info['box_number']:
                    extracted_info['box_number'] = box_number_match.group(1).strip()
                
                # Buscar observaciones (cualquier texto después de "Observación" o "Observaciones")
                obs_match = re.search(r'[Oo]bservaci[oóe]n(?:es)?:?\s*(.+)', text)
                if obs_match and not extracted_info['observation']:
                    extracted_info['observation'] = obs_match.group(1).strip()
                
                # Agregar resultado a la lista
                ocr_results.append({
                    'filename': img_filename,
                    'text': text,
                    'project_code': project_code_match.group(0).strip() if project_code_match else None,
                    'box_number': box_number_match.group(1).strip() if box_number_match else None,
                    'observation': obs_match.group(1).strip() if obs_match else None
                })
                
            except Exception as e:
                logger.error(f"Error en OCR para {img_path}: {str(e)}")
                ocr_results.append({
                    'filename': os.path.basename(img_path),
                    'text': "",
                    'error': str(e)
                })
        
        # Devolver resultados del OCR y la información extraída
        return jsonify({
            'success': True, 
            'ocr_results': ocr_results,
            'extracted_info': extracted_info,
            'images_processed': len(ocr_results)
        })
        
    except Exception as e:
        error_msg = f"Error en OCR: {str(e)}"
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

@app.route('/generate_pdf', methods=['POST'])
@login_required
def generate_pdf():
    """Genera un PDF con las imágenes de la carpeta seleccionada."""
    try:
        # Obtener el código de proyecto
        project_code = request.form.get('projectCode', '').strip()
        
        if not project_code:
            return jsonify({
                'success': False,
                'error': "Se requiere un código de proyecto"
            }), 400
        
        # Determinar si estamos en modo Indexación o Digitalización
        folder_id = request.args.get('folder', None)
        
        # Determinar el directorio de las imágenes
        if folder_id:
            # Modo Indexación - usar carpeta numerada
            base_dir = os.path.join('carpetas', folder_id)
            logger.info(f"Generando PDF en modo Indexación, carpeta: {folder_id}")
        else:
            # Modo Digitalización - usar carpeta input
            base_dir = app.config['UPLOAD_FOLDER']
            logger.info("Generando PDF en modo Digitalización")
        
        # Verificar que el directorio existe
        if not os.path.exists(base_dir):
            return jsonify({
                'success': False,
                'error': f"El directorio {base_dir} no existe"
            }), 400
        
        # Obtener las imágenes ordenadas
        image_paths = glob.glob(os.path.join(base_dir, '*.jpg')) + glob.glob(os.path.join(base_dir, '*.jpeg'))
        
        # Si no hay imágenes, devolver error
        if not image_paths:
            return jsonify({
                'success': False,
                'error': "No hay imágenes para procesar"
            }), 400
        
        # Ordenar imágenes por fecha de modificación (más antiguas primero)
        image_paths.sort(key=os.path.getmtime)
        
        # Crear directorio para PDFs si no existe
        pdf_dir = 'pdf_procesado'
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Nombre del archivo PDF
        pdf_filename = f"{project_code}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # Manejar la generación del PDF con un límite de tiempo y control de errores
        try:
            # Crear el PDF con las imágenes
            from PIL import Image
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            
            # Verificar que todas las imágenes son válidas antes de procesarlas
            valid_images = []
            for img_path in image_paths:
                try:
                    with Image.open(img_path) as img:
                        # Verificar que la imagen puede ser abierta
                        img.verify()
                        valid_images.append(img_path)
                except Exception as img_err:
                    logger.error(f"Imagen inválida {img_path}: {str(img_err)}")
            
            if not valid_images:
                return jsonify({
                    'success': False,
                    'error': "No hay imágenes válidas para procesar"
                }), 400
            
            # Crear el PDF solo con imágenes válidas
            c = canvas.Canvas(pdf_path, pagesize=letter)
            
            # Añadir cada imagen como una página del PDF
            for img_path in valid_images:
                try:
                    with Image.open(img_path) as img:
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
                except Exception as page_err:
                    logger.error(f"Error al procesar página de imagen {img_path}: {str(page_err)}")
                    # Continuar con la siguiente imagen en caso de error
            
            # Guardar el PDF
            c.save()
            
        except Exception as pdf_err:
            logger.error(f"Error al generar PDF: {str(pdf_err)}")
            return jsonify({
                'success': False,
                'error': f"Error al generar PDF: {str(pdf_err)}"
            }), 500
        
        logger.info(f"PDF generado: {pdf_path}")
        
        return jsonify({
            'success': True,
            'filename': pdf_filename,
            'path': pdf_path
        })
    
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

@app.route('/process_and_finalize', methods=['POST'])
@login_required
def process_and_finalize():
    """Procesa las imágenes, genera un PDF y elimina la carpeta de origen."""
    try:
        # Obtener datos del formulario
        project_code = request.form.get('projectCode', '').strip()
        box_number = request.form.get('boxNumber', '').strip()
        document_present = request.form.get('documentPresent', 'SI')
        observation = request.form.get('observation', '').strip()
        folder_id = request.form.get('folder', '').strip()
        
        # Validar datos
        if not project_code:
            return jsonify({
                'success': False,
                'error': "Se requiere un código de proyecto"
            }), 400
            
        if not folder_id:
            return jsonify({
                'success': False,
                'error': "Se requiere especificar una carpeta"
            }), 400
        
        # Determinar el directorio de las imágenes
        base_dir = os.path.join('carpetas', folder_id)
        logger.info(f"Procesando carpeta: {folder_id}")
        
        # Verificar que el directorio existe
        if not os.path.exists(base_dir):
            return jsonify({
                'success': False,
                'error': f"El directorio {base_dir} no existe"
            }), 400
        
        # Obtener las imágenes ordenadas
        image_paths = glob.glob(os.path.join(base_dir, '*.jpg')) + glob.glob(os.path.join(base_dir, '*.jpeg'))
        
        # Si no hay imágenes, devolver error
        if not image_paths and document_present == 'SI':
            return jsonify({
                'success': False,
                'error': "No hay imágenes para procesar y el documento está marcado como presente"
            }), 400
        
        # Ordenar imágenes por fecha de modificación (más antiguas primero)
        image_paths.sort(key=os.path.getmtime)
        
        # Crear directorio para PDFs si no existe
        pdf_dir = 'pdf_procesado'
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Nombre del archivo PDF
        pdf_filename = f"{project_code}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        pdf_generated = False
        
        # Generar PDF según si el documento está presente o no
        if document_present == 'SI' and image_paths:
            try:
                # Usar el método más simple y confiable posible
                from PIL import Image
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                
                # Crear un PDF directamente con reportlab
                c = canvas.Canvas(pdf_path, pagesize=letter)
                
                # Añadir cada imagen como una página del PDF
                for img_path in image_paths:
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
                pdf_generated = True
                logger.info(f"PDF básico generado correctamente: {pdf_path}")
                
                # Opcionalmente, podemos registrar que no se aplicó OCR en esta versión
                logger.info("PDF generado sin capa OCR")
                
            except Exception as pdf_err:
                logger.error(f"Error al generar PDF: {str(pdf_err)}")
                return jsonify({
                    'success': False,
                    'error': f"Error al generar PDF: {str(pdf_err)}"
                }), 500
        
        else:
            # Si el documento no está presente, crear un PDF simple con la observación
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                
                c = canvas.Canvas(pdf_path, pagesize=letter)
                c.setFont("Helvetica-Bold", 14)
                c.drawCentredString(letter[0]/2, letter[1]/2 + 40, "DOCUMENTO NO PRESENTE")
                
                if observation:
                    c.setFont("Helvetica", 12)
                    c.drawCentredString(letter[0]/2, letter[1]/2, "Observación:")
                    # Dividir la observación en líneas si es muy larga
                    c.setFont("Helvetica", 10)
                    text_object = c.beginText(letter[0]/4, letter[1]/2 - 20)
                    for line in observation.split('\n'):
                        text_object.textLine(line)
                    c.drawText(text_object)
                    
                if box_number:
                    c.setFont("Helvetica", 12)
                    c.drawCentredString(letter[0]/2, letter[1]/2 - 80, f"Caja: {box_number}")
                
                c.save()
                pdf_generated = True
                
            except Exception as no_doc_err:
                logger.error(f"Error al generar PDF para documento no presente: {str(no_doc_err)}")
                return jsonify({
                    'success': False,
                    'error': f"Error al generar PDF: {str(no_doc_err)}"
                }), 500
        
        # Verificar que el PDF se generó correctamente
        if not pdf_generated or not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'error': "No se pudo generar el PDF"
            }), 500
        
        # Actualizar CSV con los datos del documento
        try:
            csv_path = 'db_input.csv'
            
            # Verificar si el archivo CSV existe, si no, crearlo con los encabezados
            if not os.path.exists(csv_path):
                with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['CODIGO', 'NOMBRE_INICIATIVA', 'CAJA', 'DOC_PRESENTE', 'OBSERVACION', 'PDF_PATH'])
            
            # Leer el CSV actual
            rows = []
            codigo_encontrado = False
            headers = None
            
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    headers = reader.fieldnames
                    
                    # Asegurarse de que todos los encabezados necesarios estén presentes
                    required_headers = ['CODIGO', 'DOC_PRESENTE', 'OBSERVACION', 'PDF_PATH', 'CAJA']
                    for header in required_headers:
                        if header not in headers:
                            headers.append(header)
                    
                    # Leer todas las filas
                    for row in reader:
                        if row.get('CODIGO') == project_code:
                            # Actualizar la fila existente
                            row['DOC_PRESENTE'] = document_present
                            row['OBSERVACION'] = observation
                            row['PDF_PATH'] = pdf_path
                            row['CAJA'] = box_number
                            codigo_encontrado = True
                        rows.append(row)
            except Exception as csv_read_err:
                logger.error(f"Error al leer CSV: {str(csv_read_err)}")
                # Si hay error al leer, crear una nueva fila sin preocuparse por duplicados
                codigo_encontrado = False
                # Usar encabezados por defecto si no se pudieron leer
                headers = ['CODIGO', 'NOMBRE_INICIATIVA', 'CAJA', 'DOC_PRESENTE', 'OBSERVACION', 'PDF_PATH']
            
            # Si el código no existe, agregar una nueva fila
            if not codigo_encontrado:
                new_row = {
                    'CODIGO': project_code,
                    'NOMBRE_INICIATIVA': '',  # Campo vacío para nombre de iniciativa
                    'CAJA': box_number,
                    'DOC_PRESENTE': document_present,
                    'OBSERVACION': observation,
                    'PDF_PATH': pdf_path
                }
                rows.append(new_row)
            
            # Escribir el CSV actualizado
            with open(csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"CSV actualizado con datos del documento {project_code}")
            
        except Exception as csv_err:
            logger.error(f"Error al actualizar CSV: {str(csv_err)}")
            return jsonify({
                'success': False,
                'error': f"Se generó el PDF pero no se pudo actualizar el CSV: {str(csv_err)}"
            }), 500
        
        # AHORA SÍ: Eliminar la carpeta después de que todo esté listo
        folder_removed = False
        try:
            if os.path.exists(base_dir):
                shutil.rmtree(base_dir)
                folder_removed = True
                logger.info(f"Carpeta eliminada: {base_dir}")
        except Exception as rm_err:
            logger.error(f"Error al eliminar carpeta {base_dir}: {str(rm_err)}")
            # No interrumpimos el proceso si falla la eliminación de la carpeta
        
        return jsonify({
            'success': True, 
            'filename': pdf_filename,
            'folder': folder_id,
            'path': pdf_path,
            'document_present': document_present,
            'box_number': box_number,
            'observation': observation,
            'folder_removed': folder_removed
        })
        
    except Exception as e:
        error_msg = f"Error al procesar documento: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/generate_cuadratura')
@login_required
def generate_cuadratura():
    """Genera un archivo de cuadratura."""
    try:
        # Determinar si estamos en modo Indexación o Digitalización
        folder_id = request.args.get('folder', None)
        
        # Determinar el directorio de las imágenes
        if folder_id:
            # Modo Indexación - usar carpeta numerada
            base_dir = os.path.join('carpetas', folder_id)
            logger.info(f"Generando cuadratura en modo Indexación, carpeta: {folder_id}")
        else:
            # Modo Digitalización - usar carpeta input
            base_dir = app.config['UPLOAD_FOLDER']
            logger.info("Generando cuadratura en modo Digitalización")
        
        # Verificar que el directorio existe
        if not os.path.exists(base_dir):
            return jsonify({
                'success': False,
                'error': f"El directorio {base_dir} no existe"
            }), 400
            
        # Aquí iría el código para generar la cuadratura
        # Por ahora simplemente simularemos un resultado exitoso
        
        # Crear un archivo Excel de muestra
        output = BytesIO()
        
        # Crear un DataFrame de pandas con datos de muestra
        data = {
            'Documento': ['Doc1', 'Doc2', 'Doc3'],
            'Estado': ['Procesado', 'Procesado', 'Procesado'],
            'Fecha': ['2023-01-01', '2023-01-02', '2023-01-03']
        }
        df = pd.DataFrame(data)
        
        # Guardar DataFrame en Excel
        df.to_excel(output, index=False)
        output.seek(0)
        
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"cuadratura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    except Exception as e:
        error_msg = f"Error al generar cuadratura: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/generar_carpeta')
@login_required
def generar_carpeta():
    """Crea una carpeta numerada y mueve las imágenes actuales a esa carpeta."""
    try:
        # Asegurar que la carpeta base existe
        base_folder = 'carpetas'
        os.makedirs(base_folder, exist_ok=True)
        
        # Determinar el siguiente número de carpeta
        existing_folders = [d for d in os.listdir(base_folder) 
                          if os.path.isdir(os.path.join(base_folder, d)) 
                          and d.isdigit()]
        
        if existing_folders:
            # Obtener el número más alto y agregar 1
            next_number = max([int(folder) for folder in existing_folders]) + 1
        else:
            # Si no hay carpetas, empezar desde 1
            next_number = 1
        
        # Formato con ceros a la izquierda (0001, 0002, etc.)
        folder_name = f"{next_number:04d}"
        folder_path = os.path.join(base_folder, folder_name)
        
        # Crear la nueva carpeta
        os.makedirs(folder_path, exist_ok=True)
        
        # Obtener todas las imágenes de la carpeta input
        input_folder = app.config['UPLOAD_FOLDER']
        image_files = get_latest_images(input_folder)
        
        # Mover archivos a la nueva carpeta
        moved_files = []
        for file_path in image_files:
            file_name = os.path.basename(file_path)
            destination = os.path.join(folder_path, file_name)
            shutil.move(file_path, destination)
            moved_files.append(file_name)
        
        # Liberar memoria explícitamente
        image_files = None
        moved_files_count = len(moved_files)
        moved_files = None
        
        # Forzar la recolección de basura
        import gc
        gc.collect()
        
        logger.info(f"Carpeta generada: {folder_path} con {moved_files_count} imágenes. Memoria liberada.")
        
        return jsonify({
            'success': True, 
            'folder': folder_name, 
            'path': folder_path,
            'files_moved': moved_files_count
        }), 200
        
    except Exception as e:
        error_msg = f"Error al generar carpeta: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        
        # También forzar la recolección de basura en caso de error
        import gc
        gc.collect()
        
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/get_folders')
@login_required
def get_folders():
    """Obtiene la lista de carpetas numeradas y opcionalmente el contenido de una carpeta específica"""
    try:
        # Añadir registro de depuración
        logger.info("Accediendo a get_folders")
        
        # Obtener la carpeta solicitada (si hay)
        folder_id = request.args.get('folder', None)
        logger.info(f"Carpeta solicitada: {folder_id}")
        
        # Obtener todas las carpetas numeradas
        base_folder = 'carpetas'
        if not os.path.exists(base_folder):
            logger.info(f"Creando directorio base: {base_folder}")
            os.makedirs(base_folder, exist_ok=True)
            
        # Listar todas las carpetas y registrar para depuración
        all_items = os.listdir(base_folder)
        logger.info(f"Todos los elementos en {base_folder}: {all_items}")
        
        folders = [d for d in all_items 
                 if os.path.isdir(os.path.join(base_folder, d)) 
                 and d.isdigit()]
        
        logger.info(f"Carpetas filtradas: {folders}")
        
        # Ordenar carpetas numéricamente
        folders.sort(key=int)
        
        # Si no hay carpetas, devolver una lista vacía
        if not folders:
            logger.info("No se encontraron carpetas numeradas")
            return jsonify({
                'folders': [],
                'current_folder': None,
                'images': []
            })
        
        # Si no se especificó una carpeta, usar la primera
        if not folder_id and folders:
            folder_id = folders[0]
            logger.info(f"Usando primera carpeta: {folder_id}")
        
        # Si la carpeta especificada no existe, usar la primera
        if folder_id not in folders and folders:
            logger.info(f"Carpeta {folder_id} no existe, usando {folders[0]}")
            folder_id = folders[0]
        
        # Obtener imágenes de la carpeta seleccionada
        images = []
        if folder_id:
            folder_path = os.path.join(base_folder, folder_id)
            logger.info(f"Buscando imágenes en: {folder_path}")
            
            # Verificar si el directorio existe
            if not os.path.exists(folder_path):
                logger.error(f"¡Error! El directorio {folder_path} no existe")
                return jsonify({
                    'folders': folders,
                    'current_folder': folder_id,
                    'images': [],
                    'error': f"El directorio {folder_path} no existe"
                })
            
            # Parámetro para decidir si usar miniaturas (por defecto, sí)
            use_thumbnails = request.args.get('thumbnails', 'true').lower() == 'true'
            
            # Obtener tamaño máximo de miniaturas (por defecto 800px)
            try:
                max_size = int(request.args.get('max_size', '800'))
            except ValueError:
                max_size = 800
            
            # Buscar archivos jpg/jpeg
            image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
            logger.info(f"Archivos de imágenes encontrados: {len(image_files)}")
            
            if image_files:
                image_files.sort(key=os.path.getmtime)  # Ordenar por fecha de modificación
                
                # Convertir imágenes a formato para la UI, usando miniaturas
                try:
                    images = [get_image_data(img, thumbnail=use_thumbnails, max_size=max_size) for img in image_files]
                    logger.info(f"Imágenes procesadas: {len(images)}")
                except Exception as img_error:
                    logger.error(f"Error al procesar imágenes: {str(img_error)}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Forzar recolección de basura después de procesar todas las imágenes
                import gc
                gc.collect()
        
        return jsonify({
            'folders': folders,
            'current_folder': folder_id,
            'images': images
        })
    
    except Exception as e:
        error_msg = f"Error al obtener carpetas: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

@app.route('/list_pdfs')
@login_required
def list_pdfs():
    """Obtiene la lista de archivos PDF en la carpeta por_procesar."""
    try:
        # Asegurar que la carpeta existe
        pdf_folder = 'por_procesar'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Buscar archivos PDF
        pdf_files = glob.glob(os.path.join(pdf_folder, '*.pdf'))
        
        # Información de cada PDF
        pdf_data = []
        for pdf_path in pdf_files:
            name = os.path.basename(pdf_path)
            modified_time = os.path.getmtime(pdf_path)
            modified = datetime.fromtimestamp(modified_time).strftime('%d/%m/%Y %H:%M:%S')
            size = os.path.getsize(pdf_path)
            size_formatted = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            
            pdf_data.append({
                'name': name,
                'path': pdf_path,
                'modified': modified,
                'size': size_formatted
            })
        
        # Ordenar por fecha de modificación (más reciente primero)
        pdf_data.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
        
        return jsonify(pdf_data)
    except Exception as e:
        error_msg = f"Error al listar PDFs: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

@app.route('/por_procesar/<filename>')
@login_required
def serve_pdf(filename):
    """Sirve un archivo PDF desde la carpeta por_procesar."""
    try:
        pdf_folder = 'por_procesar'
        return send_file(os.path.join(pdf_folder, secure_filename(filename)))
    except Exception as e:
        logger.error(f"Error al servir PDF {filename}: {str(e)}")
        return "Error al servir el archivo PDF", 500

@app.route('/generar_pdf_indexado', methods=['POST'])
@login_required
def generar_pdf_indexado():
    """Genera un PDF a partir de las imágenes indexadas y lo guarda en la carpeta 'por_procesar'."""
    try:
        # Obtener datos del formulario
        data = request.json
        folder_id = data.get('folder_id')
        project_code = data.get('project_code')
        box_number = data.get('box_number')
        document_present = data.get('document_present', 'SI')
        observation = data.get('observation', '')
        
        if not folder_id:
            return jsonify({'success': False, 'error': 'No se especificó una carpeta'}), 400
        
        # Validar código de proyecto (opcional)
        if project_code and not (len(project_code) >= 6 and project_code.startswith('23')):
            return jsonify({'success': False, 'error': 'Código de proyecto inválido'}), 400
        
        # Obtener las imágenes de la carpeta
        folder_path = os.path.join('carpetas', folder_id)
        if not os.path.exists(folder_path):
            return jsonify({'success': False, 'error': f'La carpeta {folder_id} no existe'}), 404
        
        image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
        
        if not image_files:
            return jsonify({'success': False, 'error': 'No hay imágenes en la carpeta'}), 400
        
        # Ordenar las imágenes por fecha de modificación
        image_files.sort(key=os.path.getmtime)
        
        # Crear carpeta de destino si no existe
        pdf_folder = 'por_procesar'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Generar nombre del PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{project_code or 'SIN_CODIGO'}_{timestamp}.pdf"
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        
        # Crear el PDF
        pdf_writer = PdfWriter()
        
        # Procesar cada imagen
        for img_path in image_files:
            try:
                # Convertir imagen a PDF
                with Image.open(img_path) as img:
                    # Convertir a RGB si es necesario
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                        background.paste(img, img.split()[-1])
                        img = background
                    
                    # Crear un PDF temporal con la imagen
                    img_pdf = BytesIO()
                    img.save(img_pdf, format='PDF')
                    img_pdf.seek(0)
                    
                    # Añadir página al PDF final
                    pdf_reader = PdfReader(img_pdf)
                    pdf_writer.add_page(pdf_reader.pages[0])
            except Exception as img_error:
                logger.error(f"Error al procesar imagen {img_path}: {str(img_error)}")
                continue
        
        # Guardar el PDF final
        with open(pdf_path, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)
        
        # Registrar en CSV
        csv_file = 'db_input.csv'
        csv_exists = os.path.exists(csv_file)
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not csv_exists:
                writer.writerow(['fecha', 'carpeta', 'codigo_proyecto', 'caja', 'documento_presente', 'observacion', 'pdf_generado'])
            
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                folder_id,
                project_code or 'N/A',
                box_number or 'N/A',
                document_present,
                observation,
                pdf_filename
            ])
        
        return jsonify({
            'success': True,
            'message': 'Documento indexado correctamente',
            'pdf_filename': pdf_filename,
            'pdf_path': pdf_path
        }), 200
        
    except Exception as e:
        error_msg = f"Error al generar PDF indexado: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

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
