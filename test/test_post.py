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

def upload_document_to_gesdoc(rut, folio, base64_file, verify_ssl=False):
    """Upload a document to Gesdoc API using RUT, folio and base64 encoded file"""
    config = load_config()
    
    # Build the URL from the config
    base_url = config.get('endpoint', config.get('gesdoc_api'))
    
    # Remove https:// and replace with http:// if SSL verification is disabled
    if not verify_ssl and base_url.startswith('https://'):
        print("Using HTTP instead of HTTPS due to SSL verification being disabled")
        base_url = 'http://' + base_url[8:]
    
    api_path = "/api/v1/upload_document"  # Endpoint for document upload
    api_key = config.get('apikey')
    auth_token = config.get('auth_token')
    
    url = f"{base_url}{api_path}"
    
    # Set up headers
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Prepare the payload
    payload = {
        "file": base64_file,
        "rut": rut,
        "folio": folio
    }
    
    try:
        print(f"Making POST request to: {url}")
        print(f"Parameters: rut={rut}, folio={folio}")
        print(f"SSL Verification: {verify_ssl}")
        
        # Disable SSL verification if needed
        response = requests.post(url, headers=headers, json=payload, verify=verify_ssl)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        print(f"Status code: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making the request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        
        # Try alternative methods if there's an SSL error
        if isinstance(e, requests.exceptions.SSLError) and verify_ssl:
            print("\nRetrying with SSL verification disabled...")
            # Try again with SSL verification disabled
            try:
                alt_url = url
                if alt_url.startswith('https://'):
                    alt_url = 'http://' + alt_url[8:]
                print(f"Trying alternative URL: {alt_url}")
                response = requests.post(alt_url, headers=headers, json=payload, verify=False)
                response.raise_for_status()
                print(f"Alternative request succeeded! Status code: {response.status_code}")
                return response.json()
            except requests.exceptions.RequestException as alt_e:
                print(f"Alternative request also failed: {alt_e}")
        
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
        response = upload_document_to_gesdoc(self.test_rut, self.test_folio, base64_file, verify_ssl=False)
        
        # Assert response
        self.assertIsNotNone(response, "No response received from API")
        
        # Check if response contains expected fields
        # Note: Adjust these assertions based on the actual API response structure
        if response:
            self.assertIn("status", response, "Response does not contain status field")
            self.assertEqual(response.get("status"), "success", f"API call failed: {response}")

def main():
    """Main function to run the script interactively"""
    print("=== Gesdoc Document Upload Tool ===")
    
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
    
    # Always use input.pdf as the default file
    default_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'input.pdf')
    
    if os.path.exists(default_file_path):
        file_path = default_file_path
        print(f"Using default file: {file_path}")
    else:
        print("Default file 'input.pdf' not found.")
        while True:
            file_path = input("Enter path to file: ").strip()
            if os.path.exists(file_path):
                break
            print("File not found. Please try again.")
    
    # Encode file to base64
    base64_file = encode_file_to_base64(file_path)
    if not base64_file:
        print("Failed to encode file to base64. Exiting.")
        return
    
    # Ask about SSL verification
    verify_ssl = False  # Default to disabled for better compatibility
    
    print(f"\nUploading document for RUT: {rut}, Folio: {folio}...")
    result = upload_document_to_gesdoc(rut, folio, base64_file, verify_ssl=verify_ssl)
    
    if result:
        print("\nResponse from API:")
        print(json.dumps(result, indent=2))
        if result.get("status") == "success":
            print("\nDocument uploaded successfully!")
        else:
            print(f"\nUpload failed: {result.get('message', 'Unknown error')}")
    else:
        print("\nNo response received or an error occurred.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=['first-arg-is-ignored'])
    else:
        main()
