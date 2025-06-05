##temporal para gore nuble, obtiene indexacion desde ocr

import os
import csv
import logging
import re
import sys
import json

# Add parent directory to path to import from functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functions.boton_indexacion import extract_project_code_from_ocr

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def auto_indexar():
    """
    Automáticamente indexa todas las carpetas sin indexar.
    
    Busca las carpetas en ocr_generado (columna ocr_generado en carpetas.csv) 
    que no estén en carpeta_indexada, extrae el código del OCR y,
    si coincide con algún código en db_input.csv, indexa la carpeta con ese código.
    
    Returns:
        dict: Resultado de la operación con estadísticas
    """
    try:
        logger.info("Iniciando proceso de auto-indexación")
        
        # Verificar archivos necesarios
        carpetas_path = 'carpetas.csv'
        db_input_path = 'db_input.csv'
        
        if not os.path.exists(carpetas_path):
            return {
                'success': False,
                'error': 'No se encontró el archivo carpetas.csv',
                'processed': 0,
                'indexed': 0,
                'errors': 0
            }
        
        if not os.path.exists(db_input_path):
            return {
                'success': False,
                'error': 'No se encontró el archivo db_input.csv',
                'processed': 0,
                'indexed': 0,
                'errors': 0
            }
        
        # Obtener todas las carpetas a indexar (en ocr_generado pero no en carpeta_indexada)
        carpetas_a_indexar = []
        with open(carpetas_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            header = next(reader)
            
            # Verificar encabezados
            if 'carpeta_indexada' not in header or 'ocr_generado' not in header:
                return {
                    'success': False,
                    'error': 'Estructura de carpetas.csv incorrecta',
                    'processed': 0,
                    'indexed': 0,
                    'errors': 0
                }
            
            indexada_idx = header.index('carpeta_indexada')
            ocr_generado_idx = header.index('ocr_generado')
            
            for row in reader:
                if len(row) > ocr_generado_idx and row[ocr_generado_idx] and (len(row) <= indexada_idx or not row[indexada_idx]):
                    carpetas_a_indexar.append(row[ocr_generado_idx])
        
        logger.info(f"Se encontraron {len(carpetas_a_indexar)} carpetas para indexar automáticamente")
        
        # Obtener todos los códigos ya existentes en db_input.csv
        codigos_existentes = set()
        with open(db_input_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            header = next(reader)
            
            if 'CODIGO' not in header:
                return {
                    'success': False,
                    'error': 'Estructura de db_input.csv incorrecta (falta columna CODIGO)',
                    'processed': 0,
                    'indexed': 0,
                    'errors': 0
                }
            
            codigo_idx = header.index('CODIGO')
            
            for row in reader:
                if len(row) > codigo_idx and row[codigo_idx]:
                    codigos_existentes.add(row[codigo_idx])
        
        logger.info(f"Se encontraron {len(codigos_existentes)} códigos existentes en db_input.csv")
        
        # Procesar cada carpeta
        resultados = {
            'processed': len(carpetas_a_indexar),
            'indexed': 0,
            'errors': 0,
            'details': []
        }
        
        for carpeta in carpetas_a_indexar:
            try:
                # Extraer código de proyecto desde OCR
                logger.info(f"Procesando carpeta: {carpeta}")
                ocr_result = extract_project_code_from_ocr(carpeta)
                
                if not ocr_result['success'] or 'project_code' not in ocr_result:
                    logger.warning(f"No se pudo extraer código de OCR para carpeta {carpeta}: {ocr_result.get('error', 'Error desconocido')}")
                    resultados['errors'] += 1
                    resultados['details'].append({
                        'carpeta': carpeta,
                        'status': 'error',
                        'message': f"No se pudo extraer código: {ocr_result.get('error', 'Error desconocido')}"
                    })
                    continue
                
                project_code = ocr_result['project_code']
                logger.info(f"Código extraído para carpeta {carpeta}: {project_code}")
                
                # Verificar si el código existe en db_input.csv
                if project_code not in codigos_existentes:
                    logger.warning(f"Código {project_code} no encontrado en db_input.csv")
                    resultados['errors'] += 1
                    resultados['details'].append({
                        'carpeta': carpeta,
                        'status': 'error',
                        'message': f"Código {project_code} no encontrado en db_input.csv"
                    })
                    continue
                
                # Indexar la carpeta con el código encontrado
                index_result = indexar_carpeta(carpeta, project_code)
                
                if index_result['success']:
                    logger.info(f"Carpeta {carpeta} indexada correctamente con código {project_code}")
                    resultados['indexed'] += 1
                    resultados['details'].append({
                        'carpeta': carpeta,
                        'status': 'success',
                        'message': f"Indexada con código {project_code}"
                    })
                else:
                    logger.error(f"Error al indexar carpeta {carpeta}: {index_result.get('error', 'Error desconocido')}")
                    resultados['errors'] += 1
                    resultados['details'].append({
                        'carpeta': carpeta,
                        'status': 'error',
                        'message': f"Error al indexar: {index_result.get('error', 'Error desconocido')}"
                    })
            
            except Exception as e:
                logger.error(f"Error al procesar carpeta {carpeta}: {str(e)}")
                resultados['errors'] += 1
                resultados['details'].append({
                    'carpeta': carpeta,
                    'status': 'error',
                    'message': f"Error: {str(e)}"
                })
        
        resultados['success'] = True
        return resultados
    
    except Exception as e:
        logger.error(f"Error en proceso de auto-indexación: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f"Error en proceso de auto-indexación: {str(e)}",
            'processed': 0,
            'indexed': 0,
            'errors': 0
        }

def indexar_carpeta(folder_id, project_code):
    """
    Indexa una carpeta con el código de proyecto especificado.
    
    Args:
        folder_id (str): ID de la carpeta a indexar
        project_code (str): Código de proyecto a usar
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        logger.info(f"Indexando carpeta {folder_id} con código {project_code}")
        
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
        
        # Crear el archivo si no existe (no debería ocurrir aquí)
        if not os.path.exists(db_input_path):
            return {
                'success': False,
                'error': f"No se encontró el archivo {db_input_path}"
            }
        
        # Leer el archivo
        rows = []
        with open(db_input_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
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
                return {
                    'success': False,
                    'error': 'Estructura de archivo db_input.csv incorrecta'
                }
            
            # Leer todas las filas
            for row in reader:
                if len(row) > codigo_idx and row[codigo_idx] == project_code:
                    # Actualizar fila existente
                    row[caja_idx] = ""  # Valor por defecto vacío
                    row[doc_presente_idx] = "SI"  # Valor por defecto SI
                    row[observacion_idx] = ""  # Valor por defecto vacío
                    row[pdf_path_idx] = ocr_pdf_path
                    row[indexado_idx] = 'SI'
                    row[carpeta_idx] = folder_id
                    db_input_updated = True
                rows.append(row)
        
        # Si no se encontró el código, agregar una nueva fila
        if not db_input_updated:
            new_row = [''] * len(header)
            new_row[codigo_idx] = project_code
            new_row[caja_idx] = ""  # Valor por defecto vacío
            new_row[doc_presente_idx] = "SI"  # Valor por defecto SI
            new_row[observacion_idx] = ""  # Valor por defecto vacío
            new_row[pdf_path_idx] = ocr_pdf_path
            new_row[indexado_idx] = 'SI'
            new_row[carpeta_idx] = folder_id
            rows.append(new_row)
        
        # Escribir los cambios
        with open(db_input_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)
        
        # Actualizar carpetas.csv
        carpetas_updated = False
        
        # Crear el archivo si no existe (no debería ocurrir aquí)
        if not os.path.exists(carpetas_path):
            return {
                'success': False,
                'error': f"No se encontró el archivo {carpetas_path}"
            }
        
        # Leer el archivo
        carpetas_rows = []
        folder_in_list = False
        with open(carpetas_path, 'r', newline='', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            carpetas_header = next(reader)  # Guardar el encabezado
            
            # Buscar el índice de las columnas necesarias
            indexada_idx = carpetas_header.index('carpeta_indexada') if 'carpeta_indexada' in carpetas_header else -1
            ocr_generado_idx = carpetas_header.index('ocr_generado') if 'ocr_generado' in carpetas_header else -1
            
            if indexada_idx == -1 or ocr_generado_idx == -1:
                return {
                    'success': False,
                    'error': 'Estructura de archivo carpetas.csv incorrecta'
                }
            
            # Leer todas las filas
            for row in reader:
                if len(row) > ocr_generado_idx and row[ocr_generado_idx] == folder_id:
                    # Actualizar fila existente: poner el ID de carpeta en carpeta_indexada
                    row[indexada_idx] = folder_id
                    folder_in_list = True
                    carpetas_updated = True
                carpetas_rows.append(row)
        
        # Si no se encontró la carpeta, agregar una nueva fila (aunque esto no debería ocurrir)
        if not folder_in_list:
            new_row = [''] * len(carpetas_header)
            new_row[indexada_idx] = folder_id
            new_row[ocr_generado_idx] = folder_id
            carpetas_rows.append(new_row)
            carpetas_updated = True
        
        # Escribir los cambios
        with open(carpetas_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(carpetas_header)
            writer.writerows(carpetas_rows)
        
        # Registrar información
        logger.info(f"Indexación completada para carpeta {folder_id}")
        logger.info(f"Código de Proyecto: {project_code}")
        logger.info(f"Archivo db_input.csv {'actualizado' if db_input_updated else 'con nueva entrada'}")
        logger.info(f"Archivo carpetas.csv actualizado: ID carpeta {folder_id} registrado como indexado")
        
        return {
            'success': True,
            'message': 'Documento indexado correctamente'
        }
    except Exception as e:
        error_msg = f"Error al indexar carpeta {folder_id}: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }

if __name__ == "__main__":
    # Para pruebas desde línea de comandos
    result = auto_indexar()
    print(json.dumps(result, indent=2))

