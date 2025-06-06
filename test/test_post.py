#!/usr/bin/env python3
import requests
import configparser
import sys
import os
import json
import base64
import unittest
from pathlib import Path
import urllib3
import re

# Suppress only the single InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def encode_file_to_base64(file_path):
    """Encode a file to base64 string"""
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
            return base64.b64encode(file_content).decode('utf-8')
    except Exception as e:
        print(f"Error encoding file to base64: {e}")
        return None

def sanitize_rut(rut):
    """Sanitize RUT format for API use"""
    # Remove any spaces or dots
    clean_rut = re.sub(r'[.\s]', '', rut)
    # Ensure it has the dash format if not present
    if '-' not in clean_rut and len(clean_rut) > 1:
        # Insert dash before the last character (verification digit)
        clean_rut = f"{clean_rut[:-1]}-{clean_rut[-1]}"
    return clean_rut

def upload_document_to_gesdoc(rut, folio, base64_file, usuario="Sistema", verify_ssl=False):
    """Upload a document to Gesdoc API using RUT, folio and base64 encoded file"""
    config = load_config()
    
    # Sanitize RUT format
    rut = sanitize_rut(rut)
    
    # Build the URL from the config
    base_url = config.get('endpoint', config.get('gesdoc_api'))
    
    # Always use HTTPS since the server is redirecting to it anyway
    if base_url.startswith('http://'):
        base_url = 'https://' + base_url[7:]
    elif not base_url.startswith('https://'):
        base_url = 'https://' + base_url
    
    print(f"Using URL: {base_url}")
    
    # Use the correct endpoint from Postman collection
    api_path = "/api/v1/upload_document"  # This is the endpoint used in the Postman collection
    api_key = config.get('apikey')
    auth_token = config.get('auth_token')
    
    # Build the URL with query parameters (like in the Postman collection)
    url = f"{base_url}{api_path}?rut={rut}&folio={folio}"
    
    # Set up headers
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Create payload exactly as in the Postman collection
    payload = {
        "usuario": usuario,
        "file": base64_file
    }
    
    try:
        print(f"Making POST request to: {url}")
        print(f"Parameters: rut={rut}, folio={folio}")
        print(f"SSL Verification: {verify_ssl}")
        print(f"Payload format: {list(payload.keys())}")
        print(f"Payload contains file of length: {len(base64_file)} characters")
        
        # Allow redirects this time, but use a direct HTTPS URL
        response = requests.post(
            url, 
            headers=headers, 
            json=payload, 
            verify=verify_ssl,
            allow_redirects=True
        )
        
        print(f"Response status code: {response.status_code}")
        
        # Try to parse response as JSON if possible
        try:
            result = response.json()
            print(f"Success! Parsed JSON response.")
            return result
        except ValueError:
            # Not JSON, check if it's a successful status code
            if response.status_code >= 200 and response.status_code < 300:
                print(f"Success with status code {response.status_code}, but response is not JSON.")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return {"status": "success", "message": f"Status code {response.status_code}"}
            else:
                print(f"Error response (not JSON): {response.text[:200]}...")
                response.raise_for_status()  # Raise exception for non-2xx
                
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Status code: {e.response.status_code}")
            print(f"Response text: {e.response.text[:200]}...")  # Print first 200 chars
        
        # Try with direct file upload (not base64)
        try:
            print("\nTrying direct file upload approach...")
            
            # Create a temporary file from the base64 data
            temp_file_path = "temp_file.pdf"
            with open(temp_file_path, "wb") as f:
                f.write(base64.b64decode(base64_file))
            
            # Create multipart form data
            files = {
                'document': ('document.pdf', open(temp_file_path, 'rb'), 'application/pdf')
            }
            
            form_data = {
                'rut': rut,
                'folio': folio,
                'usuario': usuario
            }
            
            # Set up headers without Content-Type (will be set automatically)
            upload_headers = {
                "apikey": api_key,
                "Authorization": f"Bearer {auth_token}"
            }
            
            url_without_params = f"{base_url}{api_path}"
            print(f"Making direct file upload request to: {url_without_params}")
            
            response = requests.post(
                url_without_params, 
                headers=upload_headers,
                files=files,
                data=form_data,
                verify=verify_ssl,
                allow_redirects=True
            )
            
            print(f"Response status code: {response.status_code}")
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # Try to parse response
            try:
                result = response.json()
                print(f"Direct upload succeeded with JSON response!")
                return result
            except ValueError:
                if response.status_code >= 200 and response.status_code < 300:
                    print(f"Direct upload succeeded with status code {response.status_code}, but response is not JSON.")
                    print(f"Response text: {response.text[:200]}...")
                    return {"status": "success", "message": f"Status code {response.status_code}"}
                else:
                    print(f"Direct upload failed: {response.status_code} - {response.text[:200]}...")
            
        except Exception as e:
            print(f"Direct upload approach failed: {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        # Try one more approach: URL-encoded form data
        try:
            print("\nTrying URL-encoded form data approach...")
            
            form_headers = {
                "apikey": api_key,
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Create form data with base64 file
            form_data = {
                'rut': rut,
                'folio': folio,
                'usuario': usuario,
                'file': base64_file
            }
            
            response = requests.post(
                url_without_params,
                headers=form_headers,
                data=form_data,
                verify=verify_ssl,
                allow_redirects=True
            )
            
            print(f"Response status code: {response.status_code}")
            
            # Try to parse response
            try:
                result = response.json()
                print(f"URL-encoded approach succeeded with JSON response!")
                return result
            except ValueError:
                if response.status_code >= 200 and response.status_code < 300:
                    print(f"URL-encoded approach succeeded with status code {response.status_code}, but response is not JSON.")
                    print(f"Response text: {response.text[:200]}...")
                    return {"status": "success", "message": f"Status code {response.status_code}"}
                else:
                    print(f"URL-encoded approach failed: {response.status_code} - {response.text[:200]}...")
            
        except Exception as e:
            print(f"URL-encoded approach failed: {e}")
        
        print("\nAll attempts failed. Unable to upload document.")
        return None

class TestGesdocAPI(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        # Example test data
        self.test_rut = "9849007-8"
        self.test_folio = "2020200172"
        # Path to test image file - always use input.pdf
        self.test_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'input.pdf')
    
    def test_upload_document(self):
        """Test uploading a document to Gesdoc API"""
        # Encode file to base64
        base64_file = encode_file_to_base64(self.test_file_path)
        self.assertIsNotNone(base64_file, "Failed to encode file to base64")
        
        # Upload document with SSL verification disabled
        response = upload_document_to_gesdoc(
            self.test_rut, 
            self.test_folio, 
            base64_file, 
            usuario="Test User",
            verify_ssl=False
        )
        
        # Assert response
        self.assertIsNotNone(response, "No response received from API")
        
        # Check if response contains expected fields
        # Note: Adjust these assertions based on the actual API response structure
        if response:
            if isinstance(response, dict) and "status" in response:
                self.assertEqual(response.get("status"), "success", f"API call failed: {response}")
            else:
                self.fail(f"Unexpected response format: {response}")

def main():
    """Main function to run the script interactively"""
    print("=== Gesdoc Document Upload Tool ===")
    
    # Get RUT with guion
    while True:
        rut = input("Enter RUT with guion (e.g., 12345678-9): ").strip()
        if rut and '-' in rut:
            break
        print("RUT with guion is required. Please include the dash (-). Example: 12345678-9")
    
    # Get folio
    while True:
        folio = input("Enter Folio: ").strip()
        if folio:
            break
        print("Folio is required. Please try again.")
    
    # Get usuario (required)
    while True:
        usuario = input("Enter username: ").strip()
        if usuario:
            break
        print("Username is required. Please try again.")
    
    # Get PDF path
    while True:
        pdf_path = input("Enter PDF file path: ").strip()
        if os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
            break
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
        elif not pdf_path.lower().endswith('.pdf'):
            print(f"File must be a PDF: {pdf_path}")
        print("Please enter a valid path to a PDF file.")
    
    # Encode file to base64
    base64_file = encode_file_to_base64(pdf_path)
    if not base64_file:
        print("Failed to encode file to base64. Exiting.")
        return
    
    # SSL verification is disabled by default for better compatibility
    verify_ssl = False
    
    print(f"\nUploading document for RUT: {rut}, Folio: {folio}, User: {usuario}...")
    result = upload_document_to_gesdoc(rut, folio, base64_file, usuario=usuario, verify_ssl=verify_ssl)
    
    if result:
        print("\nResponse from API:")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)
        
        # Check for success
        if isinstance(result, dict) and result.get("status") == "success":
            print("\nDocument uploaded successfully!")
        else:
            print("\nDocument may have been uploaded, but response format is unexpected.")
    else:
        print("\nNo response received or an error occurred.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=['first-arg-is-ignored'])
    else:
        main()
