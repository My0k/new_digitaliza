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
                    return jsonify({'success': True, 'proyecto': row}), 200
        
        # Si llegamos aquí, el código no se encontró
        return jsonify({'success': False, 'error': 'Código no encontrado'}), 404
    
    except Exception as e:
        error_msg = f"Error al buscar código: {str(e)}"
        logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/procesar_documento', methods=['POST'])
@login_required
def procesar_documento():
    """Procesa el documento y actualiza el CSV."""
    try:
        data = request.json
        codigo = data.get('codigo', '')
        nombre_proyecto = data.get('nombreProyecto', '')
        documento_presente = data.get('documentoPresente', 'SI')
        observacion = data.get('observacion', '')
        selected_images = data.get('selectedImages', [])
        
        if not codigo:
            return jsonify({'success': False, 'error': 'Falta el código del proyecto'}), 400
        
        # Crear carpeta para PDFs si no existe
        pdf_folder = 'pdf_procesado'
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Nombre del archivo PDF
        filename = f"{codigo}.pdf"
        pdf_path = os.path.join(pdf_folder, filename)
        
        # Si no se especificaron imágenes, usar todas las disponibles
        if not selected_images:
            image_files = get_latest_images(folder=app.config['UPLOAD_FOLDER'])
        else:
            # Usar las imágenes seleccionadas
            image_files = [os.path.join(app.config['UPLOAD_FOLDER'], img) for img in selected_images]
        
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
        
        # Actualizar el CSV con los nuevos datos
        actualizar_csv_proyecto(codigo, filename, documento_presente, observacion)
        
        # Limpiar la carpeta input
        limpiar_input_folder()
        
        logger.info(f"Documento procesado correctamente: {pdf_path}")
        return jsonify({'success': True, 'filename': filename}), 200
    
    except Exception as e:
        error_msg = f"Error al procesar documento: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

def actualizar_csv_proyecto(codigo, pdf_path, doc_presente='SI', observacion=''):
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
                    codigo_encontrado = True
                rows.append(row)
        
        # Si el código no existe, añadir una nueva fila
        if not codigo_encontrado:
            new_row = {field: '' for field in fieldnames}
            new_row['CODIGO'] = codigo
            new_row['DOC_PRESENTE'] = doc_presente
            new_row['OBSERVACION'] = observacion
            new_row['PDF_PATH'] = pdf_path
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
