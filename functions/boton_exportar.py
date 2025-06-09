import os
import csv
import logging
import pandas as pd
from datetime import datetime
import glob
from PyPDF2 import PdfReader
from PIL import Image

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_exportable_documents():
    """
    Obtiene la lista de documentos disponibles para exportar según estos criterios:
    1) Carpetas que están en ambas columnas en carpetas.csv (ocr_generado y carpeta_indexada)
    2) Tienen un valor en CODIGO en db_input.csv
    
    Returns:
        dict: Resultado de la operación con la lista de documentos exportables
    """
    try:
        logger.info("Obteniendo documentos para exportar")
        
        # Verificar archivos necesarios
        carpetas_path = 'carpetas.csv'
        db_input_path = 'db_input.csv'
        
        if not os.path.exists(carpetas_path):
            return {
                'success': False,
                'error': 'No se encontró el archivo carpetas.csv',
                'documents': []
            }
        
        if not os.path.exists(db_input_path):
            return {
                'success': False,
                'error': 'No se encontró el archivo db_input.csv',
                'documents': []
            }
        
        # Paso 1: Obtener carpetas que están tanto en ocr_generado como en carpeta_indexada
        carpetas_indexadas = []
        with open(carpetas_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            header = next(reader)
            
            # Verificar encabezados
            if 'carpeta_indexada' not in header or 'ocr_generado' not in header:
                return {
                    'success': False,
                    'error': 'Estructura de carpetas.csv incorrecta',
                    'documents': []
                }
            
            indexada_idx = header.index('carpeta_indexada')
            ocr_generado_idx = header.index('ocr_generado')
            
            for row in reader:
                if len(row) > ocr_generado_idx and row[ocr_generado_idx] and len(row) > indexada_idx and row[indexada_idx]:
                    # Ambas columnas tienen valor para esta fila
                    if row[ocr_generado_idx] == row[indexada_idx]:
                        carpetas_indexadas.append(row[indexada_idx])
        
        logger.info(f"Se encontraron {len(carpetas_indexadas)} carpetas indexadas con OCR generado")
        
        # Paso 2: Verificar cuáles de estas carpetas tienen CODIGO en db_input.csv
        documentos_exportables = []
        with open(db_input_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            header = next(reader)
            
            # Verificar encabezados
            if 'CARPETA' not in header or 'CODIGO' not in header:
                return {
                    'success': False,
                    'error': 'Estructura de db_input.csv incorrecta (faltan columnas CARPETA o CODIGO)',
                    'documents': []
                }
            
            carpeta_idx = header.index('CARPETA')
            codigo_idx = header.index('CODIGO')
            pdf_path_idx = header.index('PDF_PATH') if 'PDF_PATH' in header else -1
            
            # Buscar otras columnas que puedan ser útiles
            columnas_adicionales = ['NOMBRE_INICIATIVA', 'CAJA', 'DOC_PRESENTE', 'OBSERVACION']
            indices_adicionales = {}
            for col in columnas_adicionales:
                if col in header:
                    indices_adicionales[col] = header.index(col)
            
            for row in reader:
                if len(row) > carpeta_idx and row[carpeta_idx] in carpetas_indexadas:
                    if len(row) > codigo_idx and row[codigo_idx]:
                        # Crear diccionario con la información del documento
                        documento = {
                            'carpeta': row[carpeta_idx],
                            'codigo': row[codigo_idx],
                            'pdf_path': row[pdf_path_idx] if pdf_path_idx >= 0 and len(row) > pdf_path_idx else None
                        }
                        
                        # Añadir columnas adicionales si existen
                        for col, idx in indices_adicionales.items():
                            if len(row) > idx:
                                documento[col.lower()] = row[idx]
                        
                        documentos_exportables.append(documento)
        
        logger.info(f"Se encontraron {len(documentos_exportables)} documentos exportables")
        
        return {
            'success': True,
            'documents': documentos_exportables,
            'total': len(documentos_exportables)
        }
    
    except Exception as e:
        logger.error(f"Error al obtener documentos exportables: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f"Error al obtener documentos exportables: {str(e)}",
            'documents': []
        }

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
            
            return is_white
            
    except Exception as e:
        logger.error(f"Error al analizar si la imagen {image_path} es blanca: {str(e)}")
        # En caso de error, asumimos que no es blanca para procesarla
        return False

def contar_imagenes_blancas_en_carpeta(carpeta_id):
    """
    Cuenta cuántas imágenes blancas hay en una carpeta específica
    
    Args:
        carpeta_id: Identificador de la carpeta
        
    Returns:
        tuple: (Número de imágenes blancas, Número de imágenes sin las blancas)
    """
    try:
        # Ruta a la carpeta
        carpeta_path = os.path.join('proceso', 'carpetas', carpeta_id)
        
        # Si la carpeta no existe, devolver (0, 0)
        if not os.path.exists(carpeta_path):
            print(f"   Carpeta {carpeta_id} no encontrada en el sistema de archivos")
            return (0, 0)
        
        # Obtener archivos de imagen
        imagenes = glob.glob(os.path.join(carpeta_path, '*.jpg')) + \
                  glob.glob(os.path.join(carpeta_path, '*.jpeg'))
        
        total_imagenes = len(imagenes)
        
        # Si no hay imágenes, reportar y retornar rápido
        if total_imagenes == 0:
            print(f"   Carpeta {carpeta_id}: No contiene imágenes")
            return (0, 0)
            
        print(f"   Analizando {total_imagenes} imágenes en carpeta {carpeta_id}...")
        
        # Contar imágenes blancas
        imagenes_blancas = 0
        for i, img_path in enumerate(imagenes):
            # Mostrar progreso cada 5 imágenes o en la última
            if i % 5 == 0 or i == total_imagenes - 1:
                print(f"      Progreso: {i+1}/{total_imagenes} imágenes ({((i+1)/total_imagenes)*100:.1f}%)")
                
            if is_mostly_white(img_path):
                imagenes_blancas += 1
        
        # Calcular imágenes sin las blancas
        imagenes_sin_blancas = total_imagenes - imagenes_blancas
        
        print(f"   Resultado carpeta {carpeta_id}: {total_imagenes} imágenes totales, {imagenes_blancas} blancas, {imagenes_sin_blancas} útiles")
        return (imagenes_blancas, imagenes_sin_blancas)
    except Exception as e:
        logger.error(f"Error al contar imágenes blancas en carpeta {carpeta_id}: {str(e)}")
        print(f"   ERROR al procesar carpeta {carpeta_id}: {str(e)}")
        return (0, 0)

def contar_imagenes_en_carpeta(carpeta_id):
    """
    Cuenta cuántas imágenes hay en una carpeta específica
    
    Args:
        carpeta_id: Identificador de la carpeta
        
    Returns:
        int: Número de imágenes encontradas
    """
    try:
        # Ruta a la carpeta
        carpeta_path = os.path.join('proceso', 'carpetas', carpeta_id)
        
        # Si la carpeta no existe, devolver 0
        if not os.path.exists(carpeta_path):
            return 0
        
        # Contar archivos de imagen
        imagenes = glob.glob(os.path.join(carpeta_path, '*.jpg')) + \
                  glob.glob(os.path.join(carpeta_path, '*.jpeg'))
        
        return len(imagenes)
    except Exception as e:
        logger.error(f"Error al contar imágenes en carpeta {carpeta_id}: {str(e)}")
        return 0

def contar_paginas_pdf(pdf_path):
    """
    Cuenta el número de páginas en un archivo PDF
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        int: Número de páginas del PDF
    """
    try:
        # Si el archivo no existe, devolver 0
        if not os.path.exists(pdf_path):
            return 0
        
        # Abrir el PDF y contar páginas
        with open(pdf_path, 'rb') as file:
            pdf = PdfReader(file)
            return len(pdf.pages)
    except Exception as e:
        logger.error(f"Error al contar páginas del PDF {pdf_path}: {str(e)}")
        return 0

def generar_cuadratura():
    """
    Genera un archivo Excel con la cuadratura de documentos exportables.
    
    Returns:
        dict: Resultado de la operación con la ruta al archivo generado
    """
    try:
        print("=== INICIANDO GENERACIÓN DE CUADRATURA ===")
        print("Fase 1/4: Obteniendo documentos exportables...")
        # Obtener documentos exportables
        result = get_exportable_documents()
        
        if not result['success']:
            print(f"Error: {result['error']}")
            return {
                'success': False,
                'error': result['error']
            }
        
        documentos = result['documents']
        
        if not documentos:
            print("Error: No hay documentos disponibles para generar cuadratura")
            return {
                'success': False,
                'error': 'No hay documentos disponibles para generar cuadratura'
            }
        
        print(f"Se encontraron {len(documentos)} documentos para incluir en la cuadratura")
        
        # Crear un DataFrame con los documentos
        df = pd.DataFrame(documentos)
        
        print("Fase 2/4: Preparando estructura del reporte...")
        # Determinar columnas disponibles (pueden variar según el CSV)
        columnas = ['codigo', 'carpeta']
        columnas_adicionales = ['nombre_iniciativa', 'caja', 'doc_presente', 'observacion']
        
        for col in columnas_adicionales:
            if col in df.columns:
                columnas.append(col)
        
        # Reordenar y renombrar columnas para el reporte
        df_reporte = df[columnas].copy()
        
        # Agregar columnas de conteo de imágenes y páginas PDF
        logger.info("Agregando conteo de imágenes y páginas PDF a la cuadratura...")
        print(f"Fase 3/4: Procesando {len(df_reporte)} carpetas para análisis detallado...")
        
        # Inicializar nuevas columnas
        df_reporte['imagenes_carpeta'] = 0
        df_reporte['paginas_pdf'] = 0
        df_reporte['imagenes_blancas'] = 0
        df_reporte['imagenes_carpeta_sin_blancas'] = 0
        
        # Procesar cada documento para obtener conteos
        for index, row in df_reporte.iterrows():
            # Mostrar progreso cada 5 carpetas procesadas
            if index % 5 == 0:
                print(f"\nCarpeta {index+1}/{len(df_reporte)} - Progreso: {((index+1)/len(df_reporte))*100:.1f}%")
            
            # Contar imágenes en la carpeta
            carpeta_id = row['carpeta']
            if carpeta_id:
                print(f"Procesando carpeta: {carpeta_id} (Documento: {row['codigo']})")
                total_imagenes = contar_imagenes_en_carpeta(carpeta_id)
                df_reporte.at[index, 'imagenes_carpeta'] = total_imagenes
                
                # Contar imágenes blancas y no blancas
                print(f"Analizando imágenes blancas en carpeta {carpeta_id}...")
                imagenes_blancas, imagenes_sin_blancas = contar_imagenes_blancas_en_carpeta(carpeta_id)
                df_reporte.at[index, 'imagenes_blancas'] = imagenes_blancas
                df_reporte.at[index, 'imagenes_carpeta_sin_blancas'] = imagenes_sin_blancas
                
                # Mostrar resumen para esta carpeta
                print(f"Resumen carpeta {carpeta_id}: {total_imagenes} imágenes totales, {imagenes_blancas} blancas, {imagenes_sin_blancas} útiles")
            else:
                print(f"Carpeta no especificada para documento {row['codigo']}")
            
            # Contar páginas del PDF
            pdf_path = df.at[index, 'pdf_path'] if 'pdf_path' in df.columns else None
            if pdf_path:
                print(f"Contando páginas del PDF: {os.path.basename(pdf_path)}")
                paginas = contar_paginas_pdf(pdf_path)
                df_reporte.at[index, 'paginas_pdf'] = paginas
                print(f"PDF tiene {paginas} páginas")
            else:
                print("No hay PDF asociado a este documento")
        
        print(f"\nProcesamiento de carpetas completado. Total: {len(df_reporte)} carpetas analizadas.")
        
        # Renombrar columnas para el reporte final
        print("Preparando formato final del reporte...")
        df_reporte.columns = [col.upper().replace('_', ' ') for col in df_reporte.columns]
        
        # Agregar columna de fecha de exportación
        df_reporte['FECHA EXPORTACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Crear directorio para reportes si no existe
        reportes_dir = 'reportes'
        os.makedirs(reportes_dir, exist_ok=True)
        
        # Nombre del archivo de cuadratura
        reporte_filename = f"cuadratura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        reporte_path = os.path.join(reportes_dir, reporte_filename)
        
        # Guardar DataFrame en Excel
        print(f"Fase 4/4: Generando archivo Excel de cuadratura: {reporte_filename}")
        writer = pd.ExcelWriter(reporte_path, engine='openpyxl')
        df_reporte.to_excel(writer, index=False, sheet_name='Cuadratura')
        
        # Ajustar anchos de columna
        for column in df_reporte:
            column_width = max(df_reporte[column].astype(str).map(len).max(), len(column))
            col_idx = df_reporte.columns.get_loc(column)
            writer.sheets['Cuadratura'].column_dimensions[chr(65 + col_idx)].width = column_width + 2
        
        writer.close()
        
        logger.info(f"Cuadratura generada: {reporte_path}")
        print(f"\n=== CUADRATURA COMPLETADA EXITOSAMENTE ===")
        print(f"Archivo generado: {reporte_path}")
        print(f"Documentos incluidos: {len(documentos)}")
        print(f"Tamaño del archivo: {os.path.getsize(reporte_path)/1024:.1f} KB")
        
        return {
            'success': True,
            'filename': reporte_filename,
            'path': reporte_path,
            'document_count': len(documentos)
        }
    
    except Exception as e:
        error_msg = f"Error al generar cuadratura: {str(e)}"
        logger.error(error_msg)
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        print(f"\n=== ERROR EN GENERACIÓN DE CUADRATURA ===")
        print(error_msg)
        print(error_trace)
        return {
            'success': False,
            'error': error_msg
        }

def exportar_documentos():
    """
    Prepara un archivo ZIP con todos los PDFs de los documentos exportables.
    
    Returns:
        dict: Resultado de la operación con la ruta al archivo ZIP generado
    """
    try:
        import zipfile
        import shutil
        
        # Obtener documentos exportables
        result = get_exportable_documents()
        
        if not result['success']:
            return {
                'success': False,
                'error': result['error']
            }
        
        documentos = result['documents']
        
        if not documentos:
            return {
                'success': False,
                'error': 'No hay documentos disponibles para exportar'
            }
        
        # Crear directorio temporal para la exportación
        export_temp_dir = 'export_temp'
        os.makedirs(export_temp_dir, exist_ok=True)
        
        # Crear directorio para exportaciones si no existe
        exports_dir = 'exports'
        os.makedirs(exports_dir, exist_ok=True)
        
        # Nombre del archivo ZIP
        zip_filename = f"documentos_exportados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(exports_dir, zip_filename)
        
        # Contador de documentos copiados
        copied_count = 0
        error_count = 0
        
        # Crear archivo ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for doc in documentos:
                pdf_path = doc.get('pdf_path')
                
                if not pdf_path or not os.path.exists(pdf_path):
                    error_count += 1
                    logger.warning(f"PDF no encontrado para documento {doc.get('codigo')}: {pdf_path}")
                    continue
                
                # Usar el código como nombre del archivo en el ZIP
                codigo = doc.get('codigo', 'desconocido')
                archivo_destino = f"{codigo}.pdf"
                
                # Añadir archivo al ZIP
                zipf.write(pdf_path, archivo_destino)
                copied_count += 1
                logger.info(f"Documento agregado al ZIP: {archivo_destino}")
        
        # Limpiar directorio temporal
        shutil.rmtree(export_temp_dir, ignore_errors=True)
        
        logger.info(f"Exportación completada: {zip_path} ({copied_count} documentos)")
        
        return {
            'success': True,
            'filename': zip_filename,
            'path': zip_path,
            'document_count': copied_count,
            'error_count': error_count
        }
    
    except Exception as e:
        logger.error(f"Error al exportar documentos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f"Error al exportar documentos: {str(e)}"
        }
