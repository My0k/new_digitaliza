#!/usr/bin/env python3
import requests
import configparser
import sys
import os
import json
import csv
import datetime
import tempfile
import shutil
from pathlib import Path

def load_config():
    """Load configuration from config file"""
    config = configparser.ConfigParser(interpolation=None)
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.conf')
    
    try:
        with open(config_path, 'r') as f:
            # Add a default section since configparser requires sections
            file_content = '[DEFAULT]\n' + f.read()
        config.read_string(file_content)
        return config['DEFAULT']
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def search_by_rut_folio(rut, folio):
    """Search in API using RUT and folio"""
    config = load_config()
    
    # Build the URL from the config
    base_url = config.get('endpoint')
    api_path = config.get('api_path')
    api_key = config.get('apikey')
    auth_token = config.get('auth_token')
    
    url = f"{base_url}{api_path}"
    
    # Set up headers and parameters
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {auth_token}"
    }
    
    params = {
        "rut": rut,
        "folio": folio
    }
    
    try:
        print(f"Making request to: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        print(f"Status code: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None

def clean_header_name(header):
    """Clean header name by removing BOM characters and normalizing it"""
    # Remove BOM and other special characters
    cleaned = header.replace('\ufeff', '').strip()
    return cleaned

def find_record_in_csv(rut, folio, csv_file):
    """Find a record in the CSV file based on RUT and folio"""
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
                print(f"Could not find 'rut' or 'folio' columns in CSV. Headers: {headers}")
                return None, None
            
            # Search for the record
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                if len(row) > max(rut_col, folio_col) and row[rut_col] == rut and row[folio_col] == folio:
                    # Convert row to dict using header names
                    row_dict = {headers[i]: value for i, value in enumerate(row) if i < len(headers)}
                    return row_num, row_dict
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        import traceback
        traceback.print_exc()
    
    return None, None

def update_csv_record(rut, folio, api_data, csv_file):
    """Update or add a record in the CSV file based on API data"""
    try:
        # First, read the CSV to get the actual headers
        with open(csv_file, 'r', newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            headers = next(reader)
            
            # Clean headers
            headers = [clean_header_name(h) for h in headers]
            
            print(f"CSV headers: {headers}")
            
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
                    print(f"Warning: CSV field '{csv_field}' not found in headers")
            
            # Process date format for fecha_nac and fecha
            fecha_nac = api_data.get("FECHA_NACIMIENTO", "")
            if fecha_nac:
                try:
                    # Convert from "2006-09-28 00:00:00.000" to "28/09/2006"
                    fecha_nac_dt = datetime.datetime.strptime(fecha_nac, "%Y-%m-%d %H:%M:%S.%f")
                    fecha_nac = fecha_nac_dt.strftime("%d/%m/%Y")
                except Exception as e:
                    print(f"Error converting fecha_nac: {e}")
            
            fecha_pagare = api_data.get("FECHA_PAGARE", "")
            if fecha_pagare:
                try:
                    # Convert from "2025-04-07 10:33:42.777" to "07/04/2025"
                    fecha_pagare_dt = datetime.datetime.strptime(fecha_pagare, "%Y-%m-%d %H:%M:%S.%f")
                    fecha_pagare = fecha_pagare_dt.strftime("%d/%m/%Y")
                except Exception as e:
                    print(f"Error converting fecha_pagare: {e}")
            
            # Process monto
            monto = api_data.get("MONTO_PESOS", "")
            if monto:
                try:
                    # Convert from "1516323.0000" to "1516323"
                    monto = str(int(float(monto)))
                except Exception as e:
                    print(f"Error converting monto: {e}")
            
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
            print("Error: Could not find 'rut' or 'folio' columns in CSV")
            return False
        
        # Set the RUT and folio values
        new_record[rut_field] = rut
        new_record[folio_field] = folio
        
        # Find if record exists
        row_num, existing_record = find_record_in_csv(rut, folio, csv_file)
        
        if existing_record:
            print(f"Record found at row {row_num}. Deleting and adding updated record...")
            
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
            
            print("Record updated successfully!")
        else:
            print("Record not found. Adding new record...")
            
            # Append new record
            with open(csv_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writerow(new_record)
            
            print("New record added successfully!")
        
        return True
    except Exception as e:
        print(f"Error updating CSV file: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the script"""
    print("=== Document Search and Update Tool ===")
    
    # Get input from user
    while True:
        rut = input("Enter RUT: ").strip()
        if rut:
            break
        print("RUT is required. Please try again.")
    
    while True:
        folio = input("Enter Folio: ").strip()
        if folio:
            break
        print("Folio is required. Please try again.")
    
    print(f"\nSearching for RUT: {rut}, Folio: {folio}...")
    result = search_by_rut_folio(rut, folio)
    
    if result and result.get("status") == "success" and result.get("data"):
        print("\nResponse from API:")
        print(json.dumps(result, indent=2))
        
        # Get the path to db_input.csv
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        csv_file = os.path.join(project_dir, "db_input.csv")
        
        if not os.path.exists(csv_file):
            print(f"Error: CSV file not found at {csv_file}")
            return
        
        # Update or add record to CSV
        api_data = result.get("data", {})
        success = update_csv_record(rut, folio, api_data, csv_file)
        
        if success:
            print(f"CSV file updated at: {csv_file}")
    else:
        print("\nNo results found or an error occurred.")

if __name__ == "__main__":
    main()

