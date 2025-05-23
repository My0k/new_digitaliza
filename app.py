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

@app.route('/ocr')
def run_ocr():
    """Ejecuta el script de OCR."""
    try:
        # Ruta al script de OCR
        script_path = os.path.join('functions', 'test_ocr.py')
        
        # Verificar si el script existe
        if not os.path.exists(script_path):
            logger.error(f"Script de OCR no encontrado: {script_path}")
            return jsonify({'success': False, 'error': 'Script de OCR no encontrado'}), 404
        
        # Ejecutar el script
        logger.info(f"Ejecutando script de OCR: {script_path}")
        result = subprocess.run(['python3', script_path], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("OCR completado con éxito")
            
            # Verificar si se generó el archivo de salida
            output_file = 'output.txt'
            student_data_file = 'student_data.json'
            
            ocr_text = 'No se generó el archivo de salida'
            student_data = {}
            
            if os.path.exists(output_file):
                # Leer el contenido del archivo
                with open(output_file, 'r', encoding='utf-8') as f:
                    ocr_text = f.read()
            
            if os.path.exists(student_data_file):
                # Leer los datos del estudiante
                with open(student_data_file, 'r', encoding='utf-8') as f:
                    student_data = json.load(f)
            
            return jsonify({
                'success': True, 
                'output': result.stdout,
                'ocr_text': ocr_text,
                'student_data': student_data
            }), 200
        else:
            logger.error(f"Error al ejecutar el script de OCR: {result.stderr}")
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        logger.error(f"Error al ejecutar OCR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        if not rut_number or not rut_dv or not folio:
            return jsonify({'success': False, 'error': 'Faltan datos necesarios'}), 400
        
        # Crear carpeta para PDFs si no existe
        pdf_folder = 'pdf_procesado'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Nombre del archivo PDF
        filename = f"{rut_number}{rut_dv}_{folio}.pdf"
        pdf_path = os.path.join(pdf_folder, filename)
        
        # Obtener las imágenes más recientes
        image_files = get_latest_images(folder=app.config['UPLOAD_FOLDER'], count=2)
        
        if len(image_files) < 2:
            return jsonify({'success': False, 'error': 'No hay suficientes imágenes para generar el PDF'}), 400
        
        # Crear el PDF con las imágenes
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        
        # Crear un PDF con las imágenes
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # IMPORTANTE: Invertir el orden de las imágenes para que el pagaré sea primero
        # La imagen más reciente (index 0) es la firma, la segunda más reciente (index 1) es el pagaré
        
        # Añadir la primera imagen (Pagaré - que está en la posición 1)
        img1 = Image.open(image_files[1])  # Cambiado de 0 a 1
        img_width, img_height = img1.size
        
        # Ajustar tamaño para que quepa en la página
        page_width, page_height = letter
        ratio = min(page_width / img_width, page_height / img_height) * 0.9
        new_width = img_width * ratio
        new_height = img_height * ratio
        
        # Posicionar en el centro de la página
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        
        c.drawImage(ImageReader(img1), x, y, width=new_width, height=new_height)
        c.showPage()
        
        # Añadir la segunda imagen (Firma - que está en la posición 0)
        img2 = Image.open(image_files[0])  # Cambiado de 1 a 0
        img_width, img_height = img2.size
        
        # Ajustar tamaño para que quepa en la página
        ratio = min(page_width / img_width, page_height / img_height) * 0.9
        new_width = img_width * ratio
        new_height = img_height * ratio
        
        # Posicionar en el centro de la página
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        
        c.drawImage(ImageReader(img2), x, y, width=new_width, height=new_height)
        c.showPage()
        
        # Guardar el PDF
        c.save()
        
        # Actualizar el CSV con el nombre del documento
        actualizar_csv(folio, filename)
        
        logger.info(f"PDF generado correctamente: {pdf_path}")
        return jsonify({'success': True, 'filename': filename}), 200
    
    except Exception as e:
        error_msg = f"Error al generar PDF: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

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
