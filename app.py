from flask import Flask, render_template, request, redirect, url_for, jsonify
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_para_la_aplicacion'
app.config['UPLOAD_FOLDER'] = 'input'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
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

def get_latest_images(folder='input', count=2):
    """Obtiene las rutas de las imágenes más recientes en la carpeta especificada."""
    try:
        files = glob.glob(os.path.join(folder, '*.jpg')) + glob.glob(os.path.join(folder, '*.jpeg'))
        # Ordenar archivos por fecha de modificación (más reciente primero)
        files.sort(key=os.path.getmtime, reverse=True)
        return files[:count]
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

@app.route('/')
def index():
    """Página principal que muestra las dos imágenes más recientes."""
    latest_images = get_latest_images(app.config['UPLOAD_FOLDER'])
    
    # Preparar datos de imágenes
    images_data = []
    for img_path in latest_images:
        images_data.append(get_image_data(img_path))
    
    # Si no hay suficientes imágenes, añadir placeholders
    while len(images_data) < 2:
        images_data.append({
            'name': 'No hay imagen disponible',
            'path': None,
            'data': None,
            'modified': 'N/A'
        })
    
    return render_template('index.html', images=images_data)

@app.route('/upload', methods=['POST'])
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
def refresh_images():
    """Endpoint para actualizar las imágenes sin recargar la página completa."""
    latest_images = get_latest_images(app.config['UPLOAD_FOLDER'])
    images_data = [get_image_data(img) for img in latest_images]
    
    while len(images_data) < 2:
        images_data.append({
            'name': 'No hay imagen disponible',
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
def scan_documents():
    """Ejecuta el script de escaneo de prueba."""
    try:
        # Ruta al script de escaneo
        script_path = os.path.join('functions', 'gen_test_input.py')
        
        # Verificar si el script existe
        if not os.path.exists(script_path):
            logger.error(f"Script de escaneo no encontrado: {script_path}")
            return jsonify({'success': False, 'error': 'Script de escaneo no encontrado'}), 404
        
        # Ejecutar el script
        logger.info(f"Ejecutando script de escaneo: {script_path}")
        result = subprocess.run(['python3', script_path], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Escaneo completado con éxito")
            return jsonify({'success': True, 'output': result.stdout}), 200
        else:
            logger.error(f"Error al ejecutar el script de escaneo: {result.stderr}")
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        logger.error(f"Error al escanear documentos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def start_folder_monitor():
    """Inicia el hilo de monitoreo de la carpeta."""
    monitor_thread = threading.Thread(target=check_folder_changes, daemon=True)
    monitor_thread.start()
    return monitor_thread

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
