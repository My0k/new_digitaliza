import os
import csv
import logging
import pandas as pd
from datetime import datetime
import glob
from PyPDF2 import PdfReader

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
                'error': 'No hay documentos disponibles para generar cuadratura'
            }
        
        # Crear un DataFrame con los documentos
        df = pd.DataFrame(documentos)
        
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
        
        # Inicializar nuevas columnas
        df_reporte['imagenes_carpeta'] = 0
        df_reporte['paginas_pdf'] = 0
        
        # Procesar cada documento para obtener conteos
        for index, row in df_reporte.iterrows():
            # Contar imágenes en la carpeta
            carpeta_id = row['carpeta']
            if carpeta_id:
                df_reporte.at[index, 'imagenes_carpeta'] = contar_imagenes_en_carpeta(carpeta_id)
            
            # Contar páginas del PDF
            pdf_path = df.at[index, 'pdf_path'] if 'pdf_path' in df.columns else None
            if pdf_path:
                df_reporte.at[index, 'paginas_pdf'] = contar_paginas_pdf(pdf_path)
        
        # Renombrar columnas para el reporte final
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
        writer = pd.ExcelWriter(reporte_path, engine='openpyxl')
        df_reporte.to_excel(writer, index=False, sheet_name='Cuadratura')
        
        # Ajustar anchos de columna
        for column in df_reporte:
            column_width = max(df_reporte[column].astype(str).map(len).max(), len(column))
            col_idx = df_reporte.columns.get_loc(column)
            writer.sheets['Cuadratura'].column_dimensions[chr(65 + col_idx)].width = column_width + 2
        
        writer.close()
        
        logger.info(f"Cuadratura generada: {reporte_path}")
        
        return {
            'success': True,
            'filename': reporte_filename,
            'path': reporte_path,
            'document_count': len(documentos)
        }
    
    except Exception as e:
        logger.error(f"Error al generar cuadratura: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f"Error al generar cuadratura: {str(e)}"
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
