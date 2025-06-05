import logging
import requests
import configparser
import os
import csv
import datetime
import tempfile
import shutil
import json
from pathlib import Path

# Configurar logging
logger = logging.getLogger(__name__)

def load_config():
    """
    Carga la configuración desde el archivo config.conf
    
    Returns:
        dict: Configuración cargada del archivo
    """
    config = configparser.ConfigParser(interpolation=None)
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.conf')
    
    try:
        with open(config_path, 'r') as f:
            # Add a default section since configparser requires sections
            file_content = '[DEFAULT]\n' + f.read()
        config.read_string(file_content)
        return config['DEFAULT']
    except Exception as e:
        logger.error(f"Error cargando config.conf: {e}")
        raise Exception(f"Error al cargar archivo de configuración: {e}")

def clean_header_name(header):
    """
    Limpia el nombre de la columna eliminando caracteres BOM y normalizándolo
    
    Args:
        header (str): Nombre de la columna a limpiar
    
    Returns:
        str: Nombre de columna limpio
    """
    # Remove BOM and other special characters
    cleaned = header.replace('\ufeff', '').strip()
    return cleaned

def find_record_in_csv(rut, folio, csv_file):
    """
    Busca un registro en el archivo CSV basado en el RUT y folio
    
    Args:
        rut (str): RUT a buscar
        folio (str): Folio a buscar
        csv_file (str): Ruta al archivo CSV
    
    Returns:
        tuple: (número de fila, registro) si se encuentra, (None, None) en caso contrario
    """
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Read the header row
            
            # Clean headers
            headers = [clean_header_name(h) for h in headers]
            
            # Find the indices of the rut and folio columns
            rut_col = -1
            folio_col = -1
            for i, header in enumerate(headers):
                if header.lower() == 'rut':
                    rut_col = i
                elif header.lower() == 'folio':
                    folio_col = i
            
            if rut_col == -1 or folio_col == -1:
                logger.warning(f"No se encontraron columnas 'rut' o 'folio' en CSV. Headers: {headers}")
                return None, None
            
            # Search for the record
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                if len(row) > max(rut_col, folio_col):
                    # Si sólo se proporciona el folio, buscar solo por folio
                    if not rut and row[folio_col] == folio:
                        # Convert row to dict using header names
                        row_dict = {headers[i]: value for i, value in enumerate(row) if i < len(headers)}
                        return row_num, row_dict
                    # Si se proporcionan ambos, buscar por rut y folio
                    elif rut and folio and row[rut_col] == rut and row[folio_col] == folio:
                        # Convert row to dict using header names
                        row_dict = {headers[i]: value for i, value in enumerate(row) if i < len(headers)}
                        return row_num, row_dict
    except Exception as e:
        logger.error(f"Error leyendo archivo CSV: {e}")
        raise
    
    return None, None

def update_csv_record(rut, folio, api_data, csv_file):
    """
    Actualiza o añade un registro en el archivo CSV basado en datos de la API
    
    Args:
        rut (str): RUT a buscar/actualizar
        folio (str): Folio a buscar/actualizar
        api_data (dict): Datos de la API a guardar en el CSV
        csv_file (str): Ruta al archivo CSV
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        # First, read the CSV to get the actual headers
        with open(csv_file, 'r', newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            headers = next(reader)
            
            # Clean headers
            headers = [clean_header_name(h) for h in headers]
            
            logger.debug(f"CSV headers: {headers}")
            
            # Create mapping from API fields to CSV headers
            field_mapping = {
                "RUT": "rut",
                "DIG_VERIF": "dig_ver",
                "NOMBRES": "nombres_alumno",
                "APELLIDO_PATERNO": "apellido_pat_alumno",
                "APELLIDO_MATERNO": "apellido_mat_alumno",
                "SEXO": "sexo",
                "ESTADO_CIVIL": "estado_civil",
                "FECHA_NACIMIENTO": "fecha_nac",
                "DIRECCION_PADRES": "direccion_padres",
                "TIPO_DEUDA": "tipo_deuda",
                "CORREO_INSTITUCIONAL": "correo_institucional",
                "CORREO_PERSONAL": "correo_alumno",
                "TELEFONO": "tel_1",
                "TELEFONO_ALTERNATIVO": "tel_2",
                "FOLIO_PAGARE": "folio",
                "FECHA_PAGARE": "fecha",
                "MONTO_PESOS": "monto",
                "RUT_AVAL": "rut_aval",
                "NOMBRES_AVAL": "nombres_aval",
                "APELLIDO_PAT_AVAL": "ape_pat_aval",
                "APELLIDO_MAT_AVAL": "ap_mat_aval",
                "DIRECCION_AVAL": "dir_aval",
                "CIUDAD_AVAL": "ciudad_aval",
                "TELEFONO_AVAL": "tel_aval",
                "CORREO_ELECTRONICO_AVAL": "mail_aval"
            }
            
            # Verify all keys in field_mapping exist in headers
            for api_field, csv_field in field_mapping.items():
                if csv_field not in headers:
                    logger.warning(f"Advertencia: Campo CSV '{csv_field}' no encontrado en encabezados")
            
            # Process date format for fecha_nac and fecha
            fecha_nac = api_data.get("FECHA_NACIMIENTO", "")
            if fecha_nac:
                try:
                    # Convert from "2006-09-28 00:00:00.000" to "28/09/2006"
                    fecha_nac_dt = datetime.datetime.strptime(fecha_nac, "%Y-%m-%d %H:%M:%S.%f")
                    fecha_nac = fecha_nac_dt.strftime("%d/%m/%Y")
                except Exception as e:
                    logger.warning(f"Error convirtiendo fecha_nac: {e}")
            
            fecha_pagare = api_data.get("FECHA_PAGARE", "")
            if fecha_pagare:
                try:
                    # Convert from "2025-04-07 10:33:42.777" to "07/04/2025"
                    fecha_pagare_dt = datetime.datetime.strptime(fecha_pagare, "%Y-%m-%d %H:%M:%S.%f")
                    fecha_pagare = fecha_pagare_dt.strftime("%d/%m/%Y")
                except Exception as e:
                    logger.warning(f"Error convirtiendo fecha_pagare: {e}")
            
            # Process monto
            monto = api_data.get("MONTO_PESOS", "")
            if monto:
                try:
                    # Convert from "1516323.0000" to "1516323"
                    monto = str(int(float(monto)))
                except Exception as e:
                    logger.warning(f"Error convirtiendo monto: {e}")
            
            # Create a new record with empty values for all columns
            new_record = {header: "" for header in headers}
            
            # Map API data to CSV fields
            for api_field, csv_field in field_mapping.items():
                if api_field in api_data and csv_field in headers:
                    if api_field == "FECHA_NACIMIENTO":
                        new_record[csv_field] = fecha_nac
                    elif api_field == "FECHA_PAGARE":
                        new_record[csv_field] = fecha_pagare
                    elif api_field == "MONTO_PESOS":
                        new_record[csv_field] = monto
                    else:
                        new_record[csv_field] = api_data.get(api_field, "")
        
        # Find the rut and folio fields in the header
        rut_field = None
        folio_field = None
        for header in headers:
            if header.lower() == 'rut':
                rut_field = header
            elif header.lower() == 'folio':
                folio_field = header
        
        if not rut_field or not folio_field:
            logger.error("Error: No se encontraron columnas 'rut' o 'folio' en CSV")
            return False
        
        # Set the RUT and folio values from API or input parameters
        if api_data.get("RUT"):
            new_record[rut_field] = api_data.get("RUT")
        elif rut:
            new_record[rut_field] = rut
            
        if api_data.get("FOLIO_PAGARE"):
            new_record[folio_field] = api_data.get("FOLIO_PAGARE")
        elif folio:
            new_record[folio_field] = folio
        
        # Find if record exists
        row_num, existing_record = find_record_in_csv(rut, folio, csv_file)
        
        if existing_record:
            logger.info(f"Registro encontrado en la fila {row_num}. Eliminando y añadiendo registro actualizado...")
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile('w', newline='', encoding='utf-8', delete=False) as temp_file:
                writer = csv.DictWriter(temp_file, fieldnames=headers)
                writer.writeheader()
                
                # Copy all rows except the one to be deleted
                with open(csv_file, 'r', newline='', encoding='utf-8-sig') as original_file:
                    reader = csv.reader(original_file)
                    next(reader)  # Skip header
                    
                    for row_idx, row in enumerate(reader, start=2):
                        if row_idx != row_num:
                            row_dict = {headers[i]: value for i, value in enumerate(row) if i < len(headers)}
                            writer.writerow(row_dict)
                
                # Add the new record
                writer.writerow(new_record)
                
                temp_filename = temp_file.name
            
            # Replace the original file with the new one
            shutil.move(temp_filename, csv_file)
            
            logger.info("¡Registro actualizado exitosamente!")
        else:
            logger.info("Registro no encontrado. Añadiendo nuevo registro...")
            
            # Append new record
            with open(csv_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writerow(new_record)
            
            logger.info("¡Nuevo registro añadido exitosamente!")
        
        return True
    except Exception as e:
        logger.error(f"Error actualizando archivo CSV: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def buscar_actualizar_folio(rut, folio):
    """
    Busca un registro en la API según el RUT y folio, y actualiza el archivo CSV.
    
    Args:
        rut (str): El número de RUT para el cual se está buscando el folio
        folio (str): El número de folio que se está buscando
    
    Returns:
        dict: Resultado de la operación
    """
    try:
        # Verificar que al menos uno de los parámetros tiene valor
        if not rut and not folio:
            return {
                "success": False,
                "message": "Debe proporcionar al menos un RUT o un número de folio",
                "error": "MISSING_PARAMETERS"
            }
            
        # Asegurar que rut no sea None
        rut = rut or ""
        folio = folio or ""
        
        # Cargar configuración
        config = load_config()
        
        # Obtener el path al archivo CSV
        proyecto_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_file = os.path.join(proyecto_dir, "db_input.csv")
        
        if not os.path.exists(csv_file):
            return {
                "success": False,
                "message": f"Error: Archivo CSV no encontrado en {csv_file}",
                "error": "FILE_NOT_FOUND"
            }
        
        # Registrar la acción en el log
        logger.info(f"Buscando y actualizando folio para rut: {rut} folio: {folio}")
        
        # Si no se proporciona RUT, intentar buscar el RUT en el CSV usando el folio
        if not rut and folio:
            row_num, record = find_record_in_csv("", folio, csv_file)
            if record and "rut" in record:
                rut = record["rut"]
                logger.info(f"RUT encontrado en CSV para folio {folio}: {rut}")
        
        # Construir la URL desde la configuración
        base_url = config.get('endpoint')
        api_path = config.get('api_path')
        api_key = config.get('apikey')
        auth_token = config.get('auth_token')
        
        url = f"{base_url}{api_path}"
        
        # Configurar headers y parámetros
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {auth_token}"
        }
        
        params = {
            "rut": rut,
            "folio": folio
        }
        
        # Realizar la petición a la API
        logger.info(f"Realizando petición a: {url}")
        logger.info(f"Parámetros: {params}")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Lanzar excepción para errores HTTP
        
        logger.info(f"Código de estado: {response.status_code}")
        result = response.json()
        
        # Verificar si la respuesta fue exitosa
        if result and result.get("status") == "success" and result.get("data"):
            # Actualizar o añadir registro al CSV
            api_data = result.get("data", {})
            success = update_csv_record(rut, folio, api_data, csv_file)
            
            if success:
                return {
                    "success": True,
                    "message": f"Registro actualizado exitosamente para RUT: {rut}, Folio: {folio}",
                    "data": {
                        "rut": rut,
                        "folio": folio,
                        "estado": "completado",
                        "api_response": result
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Error al actualizar el archivo CSV para RUT: {rut}, Folio: {folio}",
                    "error": "CSV_UPDATE_ERROR",
                    "api_response": result
                }
        else:
            return {
                "success": False,
                "message": f"No se encontraron resultados en la API para RUT: {rut}, Folio: {folio}",
                "error": "API_NO_DATA",
                "api_response": result
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición HTTP: {e}")
        error_message = str(e)
        if hasattr(e, 'response') and e.response:
            error_message += f" - Status: {e.response.status_code}, Response: {e.response.text}"
        
        return {
            "success": False,
            "message": f"Error al realizar la petición a la API: {error_message}",
            "error": "API_REQUEST_ERROR"
        }
    except Exception as e:
        logger.error(f"Error al buscar/actualizar folio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Error al procesar la solicitud: {str(e)}",
            "error": "GENERAL_ERROR"
        }

def verificar_folio_existe(folio):
    """
    Verifica si un folio existe en el sistema.
    
    Args:
        folio (str): El número de folio a verificar
    
    Returns:
        bool: True si el folio existe, False en caso contrario
    """
    try:
        # Cargar configuración
        config = load_config()
        
        # Obtener el path al archivo CSV
        proyecto_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_file = os.path.join(proyecto_dir, "db_input.csv")
        
        if not os.path.exists(csv_file):
            logger.error(f"Archivo CSV no encontrado en {csv_file}")
            return False
        
        # Buscar el folio en el CSV
        with open(csv_file, 'r', newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Read the header row
            
            # Clean headers
            headers = [clean_header_name(h) for h in headers]
            
            # Find the index of the folio column
            folio_col = -1
            for i, header in enumerate(headers):
                if header.lower() == 'folio':
                    folio_col = i
                    break
            
            if folio_col == -1:
                logger.warning(f"No se encontró la columna 'folio' en CSV. Headers: {headers}")
                return False
            
            # Search for the folio
            for row in reader:
                if len(row) > folio_col and row[folio_col] == folio:
                    return True
        
        return False
    except Exception as e:
        logger.error(f"Error al verificar si el folio existe: {str(e)}")
        return False
