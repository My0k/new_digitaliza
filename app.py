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
import hashlib
from functions.boton_indexacion import generate_folder_name, create_new_folder
import re

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
        # Si se especificó un límite, devolver solo ese número de archivos
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
        
        # Verificar si han pasado al menos 10 segundos desde la creación de la imagen
        current_time = time.time()
        time_since_creation = current_time - modified_time
        
        # Codificar la imagen en base64 para enviarla, opcionalmente generando thumbnail
        try:
            if thumbnail:
                # Definir carpeta de miniaturas y asegurar que existe
                thumbnails_folder = 'miniaturas'
                os.makedirs(thumbnails_folder, exist_ok=True)
                
                # Crear nombre para la miniatura (mismo nombre con prefijo 'thumb_')
                thumb_name = f"thumb_{name}"
                thumb_path = os.path.join(thumbnails_folder, thumb_name)
                
                # Verificar si la miniatura ya existe
                thumb_exists = os.path.exists(thumb_path)
                
                # Si han pasado menos de 10 segundos desde la creación de la imagen
                # y la miniatura aún no existe, devolver placeholder
                if time_since_creation < 10 and not thumb_exists:
                    logger.info(f"Imagen {name} es demasiado reciente ({time_since_creation:.1f}s), mostrando placeholder")
                    return {
                        'name': name,
                        'path': image_path,
                        'data': None,  # El frontend usará un placeholder
                        'modified': modified,
                        'is_thumbnail': False,
                        'pending_thumbnail': True,
                        'seconds_remaining': max(0, 10 - time_since_creation)
                    }
                
                if thumb_exists:
                    thumb_modified_time = os.path.getmtime(thumb_path)
                    # Si la imagen original es más reciente que la miniatura, recrearla
                    # pero solo si han pasado al menos 10 segundos desde la modificación
                    if modified_time > thumb_modified_time:
                        if time_since_creation < 10:
                            logger.info(f"Imagen {name} modificada recientemente ({time_since_creation:.1f}s), usando miniatura antigua")
                        else:
                            thumb_exists = False
                
                # Si la miniatura no existe o debe ser actualizada, crearla
                # siempre y cuando hayan pasado al menos 10 segundos
                if not thumb_exists and time_since_creation >= 10:
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
                
                # Si la miniatura existe, usarla
                if os.path.exists(thumb_path):
                    with open(thumb_path, "rb") as img_file:
                        encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                        data_url = f"data:image/jpeg;base64,{encoded_string}"
                else:
                    # Si la miniatura aún no se ha creado, devolver placeholder
                    return {
                        'name': name,
                        'path': image_path,
                        'data': None,
                        'modified': modified,
                        'is_thumbnail': False,
                        'pending_thumbnail': True,
                        'seconds_remaining': max(0, 10 - time_since_creation)
                    }
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
            'thumb_path': thumb_path if thumbnail and 'thumb_path' in locals() else None,
            'pending_thumbnail': False
        }
    except Exception as e:
        logger.error(f"Error al procesar imagen {image_path}: {str(e)}")
        return {
            'name': os.path.basename(image_path),
            'path': image_path,
            'data': None,
            'modified': 'Error',
            'is_thumbnail': False,
            'pending_thumbnail': False
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
                    
                    # RENOMBRADO DESACTIVADO
                    # Aquí estaba el código de renombrado que ha sido comentado/eliminado
                    
                    if mod_time > latest_mod_time:
                        latest_mod_time = mod_time
            
            # RENOMBRADO DESACTIVADO
            # Aquí estaba el código para procesar los archivos a renombrar
            
            # Si hay cambios, actualizar la variable global
            if latest_mod_time > last_folder_modification:
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
    """Ruta principal que redirige a la vista de digitalización por defecto."""
    return redirect(url_for('digitalizacion'))

@app.route('/digitalizacion')
@login_required
def digitalizacion():
    """Vista de digitalización de documentos."""
    try:
        # No enviamos imágenes iniciales desde el servidor, dejaremos que el cliente las solicite
        # para asegurar consistencia
        return render_template('digitalizacion.html', active_page='digitalizacion')
    except Exception as e:
        logger.error(f"Error al cargar digitalización: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template('error.html', error=str(e))

@app.route('/indexacion')
@app.route('/indexacion/<folder_id>/')
@login_required
def indexacion(folder_id=None):
    """Vista de indexación de documentos."""
    try:
        return render_template('indexacion.html', active_page='indexacion', folder_id=folder_id)
    except Exception as e:
        logger.error(f"Error al cargar indexación: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template('error.html', error=str(e))

@app.route('/exportar')
@login_required
def exportar():
    """Vista de exportación de documentos."""
    try:
        return render_template('exportar.html', active_page='exportar')
    except Exception as e:
        logger.error(f"Error al cargar exportación: {str(e)}")
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
def refresh_images():
    """Obtiene las imágenes más recientes en la carpeta de entrada."""
    try:
        # Obtener parámetro de límite (cuántas imágenes mostrar)
        limit = request.args.get('limit', type=int)
        
        # Obtener parámetro de ordenación (creación vs modificación)
        sort_by = request.args.get('sort_by', 'modification')
        
        # Obtener todas las imágenes de la carpeta input
        folder = app.config['UPLOAD_FOLDER']
        files = glob.glob(os.path.join(folder, '*.jpg')) + glob.glob(os.path.join(folder, '*.jpeg'))
        
        # Obtener el total de imágenes antes de aplicar límites
        total_images = len(files)
        
        # Log para depuración
        logger.debug(f"Refresh: Encontradas {total_images} imágenes, limit={limit}, sort_by={sort_by}")
        
        # Ordenar archivos según el criterio especificado
        if sort_by == 'creation':
            files.sort(key=os.path.getctime, reverse=True)
        else:
            files.sort(key=os.path.getmtime, reverse=True)
        
        # Aplicar límite si se especificó
        if limit and limit > 0:
            limited_files = files[:limit]
            logger.debug(f"Aplicando límite: mostrando {len(limited_files)} de {total_images} imágenes")
            files = limited_files
        else:
            logger.debug(f"Sin límite: mostrando todas las {total_images} imágenes")
        
        # Imprimir los nombres de archivos y sus tiempos de modificación para depuración
        debug_info = []
        for f in files:
            mtime = os.path.getmtime(f)
            debug_info.append(f"{os.path.basename(f)}: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.debug(f"Imágenes ordenadas por mtime (más reciente primero): {debug_info}")
        
        # Obtener datos para cada imagen
        image_data = []
        for img_path in files:
            img_data = get_image_data(img_path)
            if img_data:
                image_data.append(img_data)
        
        # Obtener timestamp actual para indicar cuándo se actualizó
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        return jsonify({
            'success': True,
            'images': image_data,
            'timestamp': timestamp,
            'total': total_images
        })
    except Exception as e:
        error_msg = f"Error al refrescar imágenes: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

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
            base_dir = os.path.join('proceso/carpetas', folder_id)
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

@app.route('/generar_carpeta', methods=['POST'])
@login_required
def generar_carpeta():
    """Crea una carpeta con hash MD5 y mueve las imágenes actuales a ella."""
    try:
        # Crear carpeta con nombre hash MD5
        result = create_new_folder()
        
        if not result['success']:
            return jsonify(result), 500
            
        folder_name = result['folder_name']
        folder_path = result['folder_path']
        
        # Mover imágenes a la carpeta
        moved_count = move_images_to_folder(folder_path)
        
        return jsonify({
            'success': True, 
            'folder_name': folder_name,
            'image_count': moved_count
        }), 200
    except Exception as e:
        error_msg = f"Error al generar carpeta: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/get_folders')
@login_required
def get_folders():
    """Obtiene las carpetas disponibles para indexación."""
    try:
        # Crear el directorio base si no existe
        base_dir = 'proceso/carpetas'
        os.makedirs(base_dir, exist_ok=True)
        
        # Obtener lista de carpetas (solo directorios, ordenados numéricamente)
        folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
        folders.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))
        
        # Verificar si debemos excluir carpetas ya indexadas
        exclude_indexed = request.args.get('exclude_indexed', 'false').lower() == 'true'
        
        # Si se solicita excluir carpetas indexadas, cargar la lista de carpetas indexadas
        if exclude_indexed:
            indexed_folders = []
            ocr_generated_folders = []
            carpetas_csv = 'carpetas.csv'
            
            if os.path.exists(carpetas_csv) and os.path.getsize(carpetas_csv) > 0:
                try:
                    with open(carpetas_csv, 'r', newline='', encoding='utf-8') as csvfile:
                        reader = csv.reader(csvfile)
                        headers = next(reader)  # Saltar encabezados
                        
                        # Obtener índices de las columnas relevantes
                        carpeta_indexada_idx = headers.index('carpeta_indexada') if 'carpeta_indexada' in headers else -1
                        ocr_generado_idx = headers.index('ocr_generado') if 'ocr_generado' in headers else -1
                        
                        for row in reader:
                            if not row:  # Saltar filas vacías
                                continue
                                
                            # Recopilar carpetas indexadas
                            if carpeta_indexada_idx >= 0 and len(row) > carpeta_indexada_idx and row[carpeta_indexada_idx].strip():
                                indexed_folders.append(row[carpeta_indexada_idx].strip())
                            
                            # Recopilar carpetas con OCR generado
                            if ocr_generado_idx >= 0 and len(row) > ocr_generado_idx and row[ocr_generado_idx].strip():
                                ocr_generated_folders.append(row[ocr_generado_idx].strip())
                except Exception as csv_err:
                    logger.error(f"Error al leer carpetas.csv: {str(csv_err)}")
            
            # Mostrar solo carpetas que tienen OCR generado pero no están indexadas
            pending_folders = [f for f in ocr_generated_folders if f not in indexed_folders]
            
            # Filtrar carpetas que existen físicamente y están pendientes de indexar
            folders = [f for f in folders if f in pending_folders]
            
            logger.info(f"Mostrando {len(folders)} carpetas con OCR pendientes de indexar")
        
        # Determinar la carpeta actual (del parámetro o la primera disponible)
        folder_id = request.args.get('folder', folders[0] if folders else None)
        
        # Si no hay carpeta especificada o la carpeta no existe, usar la primera disponible
        if not folder_id or folder_id not in folders:
            folder_id = folders[0] if folders else None
        
        # Preparar datos de respuesta
        images = []
        
        # Si hay una carpeta seleccionada, obtener sus imágenes
        if folder_id:
            folder_path = os.path.join(base_dir, folder_id)
            
            # Obtener las imágenes de la carpeta
            image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
            
            # Ordenar por fecha de modificación (más antiguas primero)
            image_files.sort(key=os.path.getmtime)
            
            # Procesar cada imagen para obtener los datos
            try:
                for img_path in image_files:
                    img_data = get_image_data(img_path)
                    if img_data['data']:  # Solo incluir si se pudo cargar la imagen
                        images.append(img_data)
                    else:
                        logger.warning(f"No se pudo cargar la imagen: {img_path}")
            except Exception as img_error:
                logger.error(f"Error al procesar imágenes: {str(img_error)}")
                import traceback
                logger.error(traceback.format_exc())
        
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

@app.route('/actualizar_indexacion', methods=['POST'])
@login_required
def actualizar_indexacion():
    """Actualiza los archivos CSV con la información de indexación."""
    try:
        # Obtener datos del formulario
        data = request.json
        project_code = data.get('projectCode')
        box_number = data.get('boxNumber')
        document_present = data.get('documentPresent')
        observation = data.get('observation')
        folder_id = data.get('folderId')
        
        if not project_code:
            return jsonify({
                'success': False,
                'error': 'Falta código de proyecto'
            }), 400
        
        if not folder_id:
            return jsonify({
                'success': False,
                'error': 'Falta ID de carpeta'
            }), 400
        
        # Definir rutas de archivos
        db_input_path = 'db_input.csv'
        carpetas_path = 'carpetas.csv'
        ocr_pdf_path = f'ocr_generado/{folder_id}.pdf'
        
        # Verificar si el archivo PDF existe
        if not os.path.exists(ocr_pdf_path):
            # Intentar otras ubicaciones
            alt_paths = [
                f'pdf_procesado/{folder_id}.pdf',
                f'proceso/ocr_generado/{folder_id}.pdf'
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    ocr_pdf_path = path
                    break
            else:
                # No se encontró el PDF en ninguna ubicación
                logger.warning(f"No se encontró el PDF para la carpeta {folder_id}")
                # Continuar de todos modos, pero registrar la advertencia
        
        # Actualizar db_input.csv
        db_input_updated = False
        
        # Crear el archivo si no existe
        if not os.path.exists(db_input_path):
            with open(db_input_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['YEAR', 'TIPO_SUBVENCION', 'CODIGO', 'NOMBRE_INICIATIVA', 
                               'PROVINCIA', 'COMUNA', 'RUT_INSTITUCION', 'NOMBRE_INSTITUCION', 
                               'ID', 'CAJA', 'UBICACION', 'DOC_PRESENTE', 'OBSERVACION', 
                               'PDF_PATH', 'INDEXADO', 'CARPETA'])
        
        # Leer el archivo
        rows = []
        with open(db_input_path, 'r', newline='') as file:
            reader = csv.reader(file)
            header = next(reader)  # Guardar el encabezado
            
            # Buscar el índice de las columnas necesarias
            codigo_idx = header.index('CODIGO') if 'CODIGO' in header else -1
            caja_idx = header.index('CAJA') if 'CAJA' in header else -1
            doc_presente_idx = header.index('DOC_PRESENTE') if 'DOC_PRESENTE' in header else -1
            observacion_idx = header.index('OBSERVACION') if 'OBSERVACION' in header else -1
            pdf_path_idx = header.index('PDF_PATH') if 'PDF_PATH' in header else -1
            indexado_idx = header.index('INDEXADO') if 'INDEXADO' in header else -1
            carpeta_idx = header.index('CARPETA') if 'CARPETA' in header else -1
            
            if codigo_idx == -1 or caja_idx == -1 or doc_presente_idx == -1 or observacion_idx == -1 or pdf_path_idx == -1 or indexado_idx == -1 or carpeta_idx == -1:
                return jsonify({
                    'success': False,
                    'error': 'Estructura de archivo db_input.csv incorrecta'
                }), 500
            
            # Leer todas las filas
            for row in reader:
                if len(row) > codigo_idx and row[codigo_idx] == project_code:
                    # Actualizar fila existente
                    row[caja_idx] = box_number
                    row[doc_presente_idx] = document_present
                    row[observacion_idx] = observation
                    row[pdf_path_idx] = ocr_pdf_path
                    row[indexado_idx] = 'SI'
                    row[carpeta_idx] = folder_id
                    db_input_updated = True
                rows.append(row)
        
        # Si no se encontró el código, agregar una nueva fila
        if not db_input_updated:
            new_row = [''] * len(header)
            new_row[codigo_idx] = project_code
            new_row[caja_idx] = box_number
            new_row[doc_presente_idx] = document_present
            new_row[observacion_idx] = observation
            new_row[pdf_path_idx] = ocr_pdf_path
            new_row[indexado_idx] = 'SI'
            new_row[carpeta_idx] = folder_id
            rows.append(new_row)
        
        # Escribir los cambios
        with open(db_input_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)
        
        # Actualizar carpetas.csv
        carpetas_updated = False
        
        # Crear el archivo si no existe
        if not os.path.exists(carpetas_path):
            with open(carpetas_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['carpeta_indexada', 'ocr_generado'])
        
        # Leer el archivo
        carpetas_rows = []
        folder_in_list = False
        with open(carpetas_path, 'r', newline='') as file:
            reader = csv.reader(file)
            carpetas_header = next(reader)  # Guardar el encabezado
            
            # Buscar el índice de las columnas necesarias
            indexada_idx = carpetas_header.index('carpeta_indexada') if 'carpeta_indexada' in carpetas_header else -1
            ocr_generado_idx = carpetas_header.index('ocr_generado') if 'ocr_generado' in carpetas_header else -1
            
            if indexada_idx == -1 or ocr_generado_idx == -1:
                return jsonify({
                    'success': False,
                    'error': 'Estructura de archivo carpetas.csv incorrecta'
                }), 500
            
            # Leer todas las filas
            for row in reader:
                if len(row) > ocr_generado_idx and row[ocr_generado_idx] == folder_id:
                    # Actualizar fila existente: poner el ID de carpeta en carpeta_indexada
                    row[indexada_idx] = folder_id  # Aquí cambiamos project_code por folder_id
                    folder_in_list = True
                    carpetas_updated = True
                carpetas_rows.append(row)
        
        # Si no se encontró la carpeta, agregar una nueva fila (aunque esto no debería ocurrir)
        if not folder_in_list:
            new_row = [''] * len(carpetas_header)
            new_row[indexada_idx] = folder_id  # Aquí cambiamos project_code por folder_id
            new_row[ocr_generado_idx] = folder_id
            carpetas_rows.append(new_row)
            carpetas_updated = True
        
        # Escribir los cambios
        with open(carpetas_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(carpetas_header)
            writer.writerows(carpetas_rows)
        
        # Registrar información
        logger.info(f"Indexación completada para carpeta {folder_id}")
        logger.info(f"Código de Proyecto: {project_code}")
        logger.info(f"Número de Caja: {box_number}")
        logger.info(f"Documento Presente: {document_present}")
        logger.info(f"Observación: {observation}")
        logger.info(f"Archivo db_input.csv {'actualizado' if db_input_updated else 'con nueva entrada'}")
        logger.info(f"Archivo carpetas.csv actualizado: ID carpeta {folder_id} registrado como indexado")
        
        return jsonify({
            'success': True,
            'message': 'Documento indexado correctamente'
        })
    except Exception as e:
        error_msg = f"Error al actualizar indexación: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/procesar')
@login_required
def procesar():
    """Vista de procesamiento de carpetas."""
    try:
        # Directorio base de carpetas
        base_dir = os.path.join('proceso', 'carpetas')
        os.makedirs(base_dir, exist_ok=True)
        
        # Obtener todas las carpetas (directorios)
        all_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
        
        # Obtener carpetas que ya tienen OCR generado
        ocr_generated_folders = []
        carpetas_csv = 'carpetas.csv'
        
        if os.path.exists(carpetas_csv) and os.path.getsize(carpetas_csv) > 0:
            try:
                with open(carpetas_csv, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)  # Leer encabezados
                    
                    # Verificar si existe la columna ocr_generado
                    if 'ocr_generado' in headers:
                        ocr_index = headers.index('ocr_generado')
                        
                        # Leer valores de la columna ocr_generado
                        for row in reader:
                            if row and len(row) > ocr_index and row[ocr_index].strip():
                                ocr_generated_folders.append(row[ocr_index].strip())
            except Exception as e:
                logger.error(f"Error al leer carpetas.csv: {str(e)}")
        
        # Filtrar carpetas ya procesadas
        folders = [f for f in all_folders if f not in ocr_generated_folders]
        
        # Crear una clase para representar una carpeta con un __str__ adecuado
        class FolderInfo:
            def __init__(self, id, created_at, image_count):
                self.id = id
                self.name = id
                self.created_at = created_at
                self.image_count = image_count
            
            def __str__(self):
                return self.id
        
        # Filtrar carpetas sin imágenes y crear objetos FolderInfo
        folders_with_info = []
        for folder in folders:
            folder_path = os.path.join(base_dir, folder)
            image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
            
            # Solo incluir carpetas con imágenes
            if image_files:
                # Obtener información de la carpeta
                creation_time = datetime.fromtimestamp(os.path.getctime(folder_path)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Crear objeto de carpeta con información adicional
                folder_info = FolderInfo(
                    id=folder,
                    created_at=creation_time,
                    image_count=len(image_files)
                )
                
                # Agregar a la lista de carpetas
                folders_with_info.append(folder_info)
        
        return render_template('procesar.html', folders=folders_with_info)
    except Exception as e:
        logger.error(f"Error en la vista procesar: {str(e)}")
        return render_template('error.html', message="Error al cargar la página de procesamiento.")

@app.route('/get_original_image')
@login_required
def get_original_image():
    """Sirve la imagen original en lugar de la miniatura."""
    image_path = request.args.get('path')
    
    if not image_path or not os.path.exists(image_path):
        return "Imagen no encontrada", 404
    
    # Servir la imagen directamente (sin procesamiento)
    return send_file(image_path, mimetype='image/jpeg')

@app.route('/create_new_folder', methods=['POST'])
@login_required
def create_new_folder_route():
    """Endpoint para crear una nueva carpeta."""
    result = create_new_folder()
    return jsonify(result), 200 if result['success'] else 500

def move_images_to_folder(folder_path):
    """
    Mueve todas las imágenes de la carpeta de entrada a la carpeta especificada.
    
    Args:
        folder_path (str): Ruta a la carpeta de destino
        
    Returns:
        int: Número de archivos movidos
    """
    try:
        # Verificar que hay imágenes para mover
        images = get_latest_images()
        if not images:
            logger.info("No hay imágenes para mover")
            return 0
        
        # Mover las imágenes a la carpeta destino
        moved_count = 0
        for img_path in images:
            filename = os.path.basename(img_path)
            dest_path = os.path.join(folder_path, filename)
            shutil.move(img_path, dest_path)
            moved_count += 1
            logger.debug(f"Movida imagen {img_path} a {dest_path}")
        
        logger.info(f"Se movieron {moved_count} imágenes a {folder_path}")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error al mover imágenes a {folder_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

@app.route('/process_folder', methods=['POST'])
@login_required
def process_folder():
    """Procesa una carpeta específica con OCR."""
    try:
        # Obtener el ID de la carpeta del body JSON
        data = request.json
        folder_id = data.get('folder_id')
        
        if not folder_id:
            return jsonify({
                'success': False,
                'error': "No se especificó una carpeta para procesar"
            }), 400
        
        # Importar la función desde el módulo
        from functions.generar_ocr import generar_pdf_con_ocr
        
        # Procesar la carpeta con OCR
        result = generar_pdf_con_ocr(folder_id)
        
        return jsonify(result)
    except Exception as e:
        error_msg = f"Error al procesar carpeta: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/process_all_folders', methods=['POST'])
@login_required
def process_all_folders():
    """Procesa todas las carpetas pendientes generando PDFs."""
    try:
        # Obtener lista de carpetas
        base_dir = os.path.join('proceso', 'carpetas')
        os.makedirs(base_dir, exist_ok=True)
        
        folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
        
        if not folders:
            return jsonify({
                'success': False,
                'error': "No hay carpetas para procesar"
            }), 404
        
        # Cargar carpetas que ya tienen OCR generado desde carpetas.csv
        ocr_generated_folders = []
        carpetas_csv = 'carpetas.csv'
        
        if os.path.exists(carpetas_csv) and os.path.getsize(carpetas_csv) > 0:
            try:
                import csv
                with open(carpetas_csv, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)  # Leer encabezados
                    
                    # Verificar si existe la columna ocr_generado
                    if 'ocr_generado' in headers:
                        ocr_index = headers.index('ocr_generado')
                        
                        # Leer valores de la columna ocr_generado
                        for row in reader:
                            if row and len(row) > ocr_index and row[ocr_index].strip():
                                ocr_generated_folders.append(row[ocr_index].strip())
                                
                logger.info(f"Se encontraron {len(ocr_generated_folders)} carpetas ya procesadas en carpetas.csv")
            except Exception as csv_err:
                logger.error(f"Error al leer carpetas.csv: {str(csv_err)}")
        
        # Filtrar carpetas ya procesadas
        folders_to_process = [f for f in folders if f not in ocr_generated_folders]
        
        if not folders_to_process:
            return jsonify({
                'success': False,
                'error': "Todas las carpetas ya han sido procesadas"
            }), 200
        
        # Importar la función desde el módulo
        from functions.generar_ocr import generar_pdf_simple
        
        # Procesar cada carpeta, verificando que tengan imágenes
        results = []
        processed_count = 0
        skipped_no_images = 0
        
        for folder in folders_to_process:
            # Verificar si la carpeta tiene imágenes JPG
            folder_path = os.path.join(base_dir, folder)
            image_files = glob.glob(os.path.join(folder_path, '*.jpg')) + glob.glob(os.path.join(folder_path, '*.jpeg'))
            
            if not image_files:
                logger.info(f"Carpeta {folder} no tiene imágenes JPG, se omite")
                skipped_no_images += 1
                continue
            
            # Procesar carpeta
            result = generar_pdf_simple(folder)
            results.append(result)
            
            if result['success']:
                processed_count += 1
        
        # Preparar respuesta
        return jsonify({
            'success': True,
            'total_folders': len(folders),
            'already_processed': len(ocr_generated_folders),
            'eligible_for_processing': len(folders_to_process),
            'skipped_no_images': skipped_no_images,
            'processed_successfully': processed_count,
            'error_count': len(results) - processed_count,
            'details': results
        })
        
    except Exception as e:
        error_msg = f"Error al procesar todas las carpetas: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/view_pdf')
@login_required
def view_pdf():
    """Muestra un archivo PDF."""
    try:
        pdf_path = request.args.get('path')
        
        if not pdf_path or not os.path.exists(pdf_path):
            return "PDF no encontrado", 404
        
        return send_file(pdf_path, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error al mostrar PDF: {str(e)}")
        return "Error al mostrar el PDF", 500

@app.route('/extract_project_code')
@login_required
def extract_project_code():
    """Extrae el código de proyecto del PDF OCR de una carpeta."""
    try:
        folder_id = request.args.get('folder')
        if not folder_id:
            return jsonify({
                'success': False,
                'error': 'No se especificó ninguna carpeta'
            }), 400
        
        # Importar la función desde el módulo
        from functions.boton_indexacion import extract_project_code_from_ocr
        
        # Llamar a la función para extraer el código
        result = extract_project_code_from_ocr(folder_id)
        
        return jsonify(result)
    except Exception as e:
        error_msg = f"Error al extraer código de proyecto: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def extract_project_code_from_ocr(folder_name):
    """
    Extrae el código de proyecto del PDF OCR usando una expresión regular.
    
    Args:
        folder_name (str): Nombre de la carpeta
        
    Returns:
        dict: Resultado de la operación con el código encontrado o un error
    """
    try:
        # Verificar que el archivo PDF existe
        pdf_path = f"pdf_procesado/{folder_name}.pdf"
        if not os.path.exists(pdf_path):
            return {
                'success': False,
                'error': f"No se encontró el archivo PDF con OCR: {pdf_path}"
            }
        
        # Abrir el PDF y extraer el texto
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text()
        
        # Buscar el código de proyecto con la expresión regular
        pattern = r'\b23\d{2}[A-Z]{1,2}\d{4}\b'
        matches = re.findall(pattern, text)
        
        if matches:
            # Devolver el primer código encontrado
            return {
                'success': True,
                'project_code': matches[0],
                'message': f"Código de proyecto encontrado: {matches[0]}"
            }
        else:
            return {
                'success': False,
                'error': "No se encontró ningún código de proyecto en el documento"
            }
    
    except Exception as e:
        logger.error(f"Error al extraer código de proyecto: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        
        return {
            'success': False,
            'error': str(e),
            'traceback': error_trace,
            'message': f"Error al procesar el PDF: {str(e)}"
        }

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
