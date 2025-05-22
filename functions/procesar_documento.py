import csv
import json
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def buscar_por_folio(folio):
    """
    Busca un registro en el CSV por número de folio.
    
    Args:
        folio (str): Número de folio a buscar
        
    Returns:
        dict: Datos del registro encontrado o None si no se encuentra
    """
    try:
        # Ruta al archivo CSV
        csv_path = 'db_input.csv'
        
        # Verificar si el archivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV no encontrado: {csv_path}")
            return None
        
        # Imprimir información de depuración
        logger.info(f"Buscando folio: {folio}")
        logger.info(f"Ruta del CSV: {os.path.abspath(csv_path)}")
        
        # Contar registros en el CSV para verificar que se está leyendo correctamente
        total_registros = 0
        folios_disponibles = []
        
        # Buscar el folio en el CSV
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                total_registros += 1
                current_folio = row.get('folio', '')
                folios_disponibles.append(current_folio)
                
                if current_folio == folio:
                    # Construir los datos formateados
                    nombre_estudiante = f"{row.get('nombres_alumno', '')} {row.get('apellido_pat_alumno', '')} {row.get('apellido_mat_alumno', '')}"
                    nombre_aval = f"{row.get('nombres_aval', '')} {row.get('ape_pat_aval', '')} {row.get('ap_mat_aval', '')}"
                    
                    # Crear diccionario con los datos requeridos
                    datos = {
                        'nombre_estudiante': nombre_estudiante.strip(),
                        'nombre_aval': nombre_aval.strip(),
                        'rut_aval': row.get('rut_aval', ''),
                        'monto': row.get('monto', ''),
                        'email_aval': row.get('mail_aval', '')
                    }
                    
                    logger.info(f"Registro encontrado para folio {folio}: {datos}")
                    return datos
        
        # Si llegamos aquí, no se encontró el folio
        logger.warning(f"No se encontró registro para el folio {folio}")
        logger.info(f"Total de registros en el CSV: {total_registros}")
        logger.info(f"Primeros 5 folios disponibles: {folios_disponibles[:5]}")
        return None
    
    except Exception as e:
        logger.error(f"Error al buscar folio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Código para pruebas
    folio_test = "2025010058"  # Usar un folio que sabemos que existe en el CSV
    resultado = buscar_por_folio(folio_test)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    # Listar todos los folios disponibles
    csv_path = 'db_input.csv'
    if os.path.exists(csv_path):
        print("\nFolios disponibles:")
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            folios = [row.get('folio', '') for row in csv_reader]
            print(f"Total de folios: {len(folios)}")
            print(f"Primeros 10 folios: {folios[:10]}")
