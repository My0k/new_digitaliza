import csv
import logging
import os
import json
from functions.procesar_documento import procesar_y_subir_documento

# Configurar logging
logger = logging.getLogger(__name__)

def obtener_documentos_para_exportar():
    """
    Obtiene la lista de documentos que pueden ser exportados a Gesdoc.
    Un documento puede ser exportado si tiene valores en nombre_documento, folio y rut.
    
    Returns:
        list: Lista de diccionarios con la información de los documentos exportables
    """
    try:
        documentos_exportables = []
        
        # Verificar si el archivo CSV existe
        csv_path = 'db_input.csv'
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV no encontrado: {csv_path}")
            return documentos_exportables
        
        # Leer el archivo CSV directamente como texto plano primero
        with open(csv_path, 'r', encoding='utf-8') as file:
            lineas = file.readlines()
            
        if not lineas:
            logger.error("El archivo CSV está vacío")
            return documentos_exportables
        
        # Obtener los encabezados y corregir el BOM si está presente
        headers = lineas[0].strip().split(',')
        
        # Corregir el primer encabezado si tiene el BOM
        if headers and headers[0].startswith('\ufeff'):
            headers[0] = headers[0].replace('\ufeff', '')
            logger.info(f"Se eliminó el BOM del primer encabezado: '{headers[0]}'")
        
        logger.info(f"Encabezados del CSV (después de corrección): {headers}")
        
        # Identificar las posiciones de las columnas clave
        try:
            # Buscar el índice de 'rut' de manera más flexible
            idx_rut = -1
            for i, header in enumerate(headers):
                if header.lower() == 'rut' or header.lower().endswith('rut'):
                    idx_rut = i
                    logger.info(f"Se encontró el encabezado 'rut' en la posición {i}: '{header}'")
                    break
            
            if idx_rut == -1:
                logger.error("No se pudo encontrar la columna 'rut' en los encabezados")
                return documentos_exportables
                
            idx_dig_ver = headers.index('dig_ver') if 'dig_ver' in headers else -1
            idx_folio = headers.index('folio') if 'folio' in headers else -1
            idx_nombre_documento = headers.index('nombre_documento') if 'nombre_documento' in headers else -1
            
            # Columnas adicionales para información complementaria
            idx_nombres = headers.index('nombres_alumno') if 'nombres_alumno' in headers else -1
            idx_apellido_pat = headers.index('apellido_pat_alumno') if 'apellido_pat_alumno' in headers else -1
            idx_apellido_mat = headers.index('apellido_mat_alumno') if 'apellido_mat_alumno' in headers else -1
            
            logger.info(f"Índices de columnas encontrados - rut:{idx_rut}, dig_ver:{idx_dig_ver}, folio:{idx_folio}, nombre_documento:{idx_nombre_documento}")
        except ValueError as e:
            logger.error(f"Error al encontrar columnas necesarias: {e}")
            return documentos_exportables
        
        # Procesar cada línea del CSV (excepto el encabezado)
        for i, linea in enumerate(lineas[1:], 1):
            try:
                if not linea.strip():
                    continue  # Ignorar líneas vacías
                
                # Dividir la línea en campos
                campos = linea.strip().split(',')
                
                # Verificar que la línea tenga suficientes campos
                max_idx = max(idx for idx in [idx_rut, idx_dig_ver, idx_folio, idx_nombre_documento] if idx >= 0)
                if len(campos) <= max_idx:
                    logger.warning(f"Línea {i} no tiene suficientes campos: {linea.strip()}")
                    continue
                
                # Obtener los valores de las columnas clave
                rut = campos[idx_rut].strip() if idx_rut >= 0 else ""
                dig_ver = campos[idx_dig_ver].strip() if idx_dig_ver >= 0 else ""
                folio = campos[idx_folio].strip() if idx_folio >= 0 else ""
                nombre_documento = campos[idx_nombre_documento].strip() if idx_nombre_documento >= 0 else ""
                
                # Información de diagnóstico para líneas con valores relevantes
                if rut or folio or nombre_documento:
                    logger.info(f"Línea {i}: rut='{rut}', dig_ver='{dig_ver}', folio='{folio}', nombre_documento='{nombre_documento}'")
                
                # Verificar si tiene los campos necesarios para ser exportable
                # Cualquier valor no vacío se considera válido (incluyendo "TEST")
                if rut and folio and nombre_documento:
                    # Obtener información adicional para mostrar en la alerta
                    nombres = campos[idx_nombres].strip() if idx_nombres >= 0 and idx_nombres < len(campos) else ""
                    apellido_pat = campos[idx_apellido_pat].strip() if idx_apellido_pat >= 0 and idx_apellido_pat < len(campos) else ""
                    apellido_mat = campos[idx_apellido_mat].strip() if idx_apellido_mat >= 0 and idx_apellido_mat < len(campos) else ""
                    
                    nombre_completo = f"{nombres} {apellido_pat} {apellido_mat}".strip()
                    rut_completo = f"{rut}-{dig_ver}"
                    
                    documento = {
                        'nombre_documento': nombre_documento,
                        'folio': folio,
                        'rut': rut_completo,
                        'nombres': nombre_completo
                    }
                    
                    documentos_exportables.append(documento)
                    logger.info(f"Documento añadido para exportar: {documento}")
            
            except Exception as e:
                logger.error(f"Error al procesar línea {i}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"Total de documentos encontrados para exportar: {len(documentos_exportables)}")
        return documentos_exportables
    
    except Exception as e:
        logger.error(f"Error al obtener documentos para exportar: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def exportar_a_gesdoc(usuario="Sistema"):
    """
    Exporta los documentos elegibles a Gesdoc y devuelve un mensaje para mostrar en la alerta.
    
    Args:
        usuario (str): Nombre del usuario que está realizando la exportación
    
    Returns:
        dict: Resultado de la operación con la siguiente estructura:
            - success (bool): True si la operación fue exitosa, False en caso contrario
            - mensaje (str): Mensaje que se mostrará en la alerta
            - documentos (list): Lista de documentos que se exportaron (o se exportarían)
            - total (int): Total de documentos que se exportaron (o se exportarían)
            - resultados (list): Lista de resultados de las operaciones individuales
    """
    try:
        # Verificar si el archivo CSV existe
        csv_path = 'db_input.csv'
        if not os.path.exists(csv_path):
            error_msg = f"Archivo CSV no encontrado: {csv_path}"
            logger.error(error_msg)
            return {
                'success': False,
                'mensaje': error_msg,
                'documentos': [],
                'total': 0
            }
        
        # Obtener documentos exportables
        documentos = obtener_documentos_para_exportar()
        total_documentos = len(documentos)
        
        if total_documentos == 0:
            # Mostrar mensaje de que no hay documentos para exportar
            debug_msg = "No hay documentos para exportar a Gesdoc."
            logger.info(debug_msg)
            return {
                'success': False,
                'mensaje': debug_msg,
                'documentos': [],
                'total': 0
            }
        
        # Construir mensaje para la alerta
        mensaje = f"Exportar {total_documentos} documentos a Gesdoc"
        
        # Obtener los primeros 5 documentos para mostrar en la alerta
        primeros_5 = documentos[:5]
        
        # Añadir detalle de los primeros 5 documentos al mensaje
        detalles = []
        for doc in primeros_5:
            detalle = f"- {doc['nombre_documento']} (Folio: {doc['folio']}, RUT: {doc['rut']})"
            detalles.append(detalle)
        
        # Si hay más de 5 documentos, indicarlo
        if total_documentos > 5:
            detalles.append(f"- ... y {total_documentos - 5} más")
        
        # Lógica para exportar a Gesdoc
        resultados = []
        documentos_procesados = 0
        documentos_exitosos = 0
        
        for doc in documentos:
            try:
                # Verificar si el PDF ya existe
                pdf_path = os.path.join('pdf_procesado', doc['nombre_documento'])
                
                if os.path.exists(pdf_path):
                    # El PDF ya existe, enviar directamente a Gesdoc
                    logger.info(f"PDF encontrado: {pdf_path}")
                    resultado = procesar_y_subir_documento(doc['rut'], doc['folio'], usuario, None)
                else:
                    # Necesitamos generar el PDF primero
                    logger.info(f"PDF no encontrado: {pdf_path}, generando...")
                    resultado = procesar_y_subir_documento(doc['rut'], doc['folio'], usuario, None)
                
                # Guardar el resultado
                resultado['documento'] = doc['nombre_documento']
                resultado['folio'] = doc['folio']
                resultado['rut'] = doc['rut']
                resultados.append(resultado)
                
                # Contar documentos procesados exitosamente
                documentos_procesados += 1
                if resultado.get('status') == 'success':
                    documentos_exitosos += 1
            
            except Exception as e:
                error_msg = f"Error al procesar documento {doc['nombre_documento']}: {str(e)}"
                logger.error(error_msg)
                resultados.append({
                    'status': 'error',
                    'message': error_msg,
                    'documento': doc['nombre_documento'],
                    'folio': doc['folio'],
                    'rut': doc['rut']
                })
        
        # Determinar si la exportación fue exitosa en general
        success = documentos_exitosos > 0
        
        # Actualizar el mensaje con el resultado
        mensaje_resultado = f"Se exportaron {documentos_exitosos} de {total_documentos} documentos a Gesdoc."
        
        return {
            'success': success,
            'mensaje': mensaje_resultado,
            'detalles': detalles,
            'documentos': documentos,
            'total': total_documentos,
            'resultados': resultados,
            'procesados': documentos_procesados,
            'exitosos': documentos_exitosos
        }
    
    except Exception as e:
        error_msg = f"Error al exportar a Gesdoc: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'mensaje': error_msg,
            'documentos': [],
            'total': 0
        }

if __name__ == "__main__":
    # Código para pruebas
    import json
    
    # Configurar logging para pruebas
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Obtener documentos para exportar
    docs = obtener_documentos_para_exportar()
    print(f"Total de documentos para exportar: {len(docs)}")
    
    # Mostrar los primeros 3 documentos
    for i, doc in enumerate(docs[:3]):
        print(f"Documento {i+1}: {json.dumps(doc, indent=2)}")
    
    # Ejecutar exportación
    resultado = exportar_a_gesdoc("test_user")
    print("\nResultado de exportación:")
    print(json.dumps(resultado, indent=2))
