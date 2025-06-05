#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para convertir un archivo PDF a PDF con OCR.
Utiliza ocrmypdf para procesar el archivo y alinear el texto OCR con las letras originales.
Compatible con Linux y Windows.
"""

import os
import sys
import argparse
import subprocess
import platform
from pathlib import Path

def check_ocrmypdf_installed():
    """Verifica si ocrmypdf está instalado en el sistema."""
    print("Verificando si ocrmypdf está instalado...")
    try:
        subprocess.run(["ocrmypdf", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      check=True)
        print("✓ ocrmypdf está instalado correctamente.")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("✗ ocrmypdf no está instalado.")
        return False

def install_ocrmypdf():
    """Intenta instalar ocrmypdf si no está disponible."""
    system = platform.system()
    print("ocrmypdf no está instalado. Intentando instalar...")
    
    try:
        if system == "Windows":
            print("Instalando ocrmypdf en Windows mediante pip...")
            subprocess.run(["pip", "install", "ocrmypdf"], check=True)
            print("✓ Se ha instalado ocrmypdf correctamente.")
        elif system == "Linux":
            print("En Linux, es recomendable instalar ocrmypdf mediante el gestor de paquetes.")
            print("Por ejemplo, en Ubuntu/Debian: sudo apt-get install ocrmypdf")
            print("O con pip: pip install ocrmypdf")
            sys.exit(1)
        else:
            print(f"Sistema operativo {system} no soportado directamente.")
            print("Intente instalar ocrmypdf manualmente según la documentación oficial.")
            sys.exit(1)
    except subprocess.SubprocessError:
        print("Error al instalar ocrmypdf. Intente instalarlo manualmente.")
        print("Visite: https://ocrmypdf.readthedocs.io/en/latest/installation.html")
        sys.exit(1)

def process_pdf(input_file, output_file, language="spa", deskew=True, clean=True, optimize=True):
    """
    Procesa un archivo PDF y genera una versión con OCR.
    
    Args:
        input_file: Ruta del archivo PDF de entrada
        output_file: Ruta donde se guardará el PDF con OCR
        language: Idioma para el OCR (por defecto español)
        deskew: Si se debe enderezar el texto inclinado
        clean: Si se debe limpiar la imagen antes del OCR
        optimize: Si se debe optimizar el PDF resultante
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    print(f"Verificando archivo de entrada: {input_file}")
    if not input_path.exists():
        print(f"Error: El archivo {input_file} no existe.")
        sys.exit(1)
    
    if not input_path.is_file() or input_path.suffix.lower() != '.pdf':
        print(f"Error: {input_file} no es un archivo PDF válido.")
        sys.exit(1)
    
    print(f"✓ Archivo de entrada verificado: {input_file} ({input_path.stat().st_size} bytes)")
    
    # Preparar comando con opciones
    cmd = ["ocrmypdf"]
    
    if deskew:
        cmd.append("--deskew")
        print("- Habilitada la corrección de inclinación")
    
    if clean:
        cmd.append("--clean")
        print("- Habilitada la limpieza de imágenes")
    
    if optimize:
        cmd.append("--optimize")
        cmd.append("3")
        print("- Habilitada la optimización nivel 3")
    
    # Forzar OCR aunque el PDF ya tenga texto
    cmd.append("--force-ocr")
    print("- Forzando OCR incluso si ya tiene texto")
    
    # Especificar idioma
    cmd.extend(["-l", language])
    print(f"- Idioma seleccionado: {language}")
    
    # Agregar archivos de entrada y salida
    cmd.extend([str(input_path), str(output_path)])
    
    print("\nComando completo:")
    print(" ".join(cmd))
    
    print("\nIniciando proceso OCR...")
    try:
        print(f"Procesando {input_file}...")
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        print("\n--- Salida del proceso ---")
        print(process.stdout)
        
        if output_path.exists():
            print(f"✓ Archivo procesado exitosamente.")
            print(f"✓ Guardado en: {output_file} ({output_path.stat().st_size} bytes)")
            return True
        else:
            print(f"✗ Error: El archivo de salida no se generó correctamente.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Error al procesar el archivo: {e}")
        print(f"Detalles del error:")
        print(e.stderr)
        return False

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Convierte un PDF a PDF con OCR.")
    parser.add_argument("input", nargs='?', default="input.pdf", 
                       help="Archivo PDF de entrada (default: input.pdf)")
    parser.add_argument("-o", "--output", help="Archivo PDF de salida")
    parser.add_argument("-l", "--language", default="spa", 
                        help="Idioma para OCR (default: spa - español)")
    parser.add_argument("--no-deskew", action="store_false", dest="deskew",
                        help="No enderezar páginas inclinadas")
    parser.add_argument("--no-clean", action="store_false", dest="clean",
                        help="No limpiar la imagen antes del OCR")
    parser.add_argument("--no-optimize", action="store_false", dest="optimize",
                        help="No optimizar el PDF resultante")
    
    args = parser.parse_args()
    
    print("=== OCR PDF Processor ===")
    
    # Verificar si ocrmypdf está instalado
    if not check_ocrmypdf_installed():
        install_ocrmypdf()
        # Verificar nuevamente
        if not check_ocrmypdf_installed():
            print("No se pudo instalar ocrmypdf. Por favor, instálelo manualmente.")
            sys.exit(1)
    
    # Configurar archivo de salida si no se especificó
    input_file = args.input
    if args.output:
        output_file = args.output
    else:
        input_path = Path(input_file)
        output_file = str(input_path.with_name(f"{input_path.stem}_ocr{input_path.suffix}"))
    
    print(f"\nConfiguración:")
    print(f"- Archivo de entrada: {input_file}")
    print(f"- Archivo de salida: {output_file}")
    print(f"- Idioma: {args.language}")
    print(f"- Corrección de inclinación: {'Sí' if args.deskew else 'No'}")
    print(f"- Limpieza de imagen: {'Sí' if args.clean else 'No'}")
    print(f"- Optimización: {'Sí' if args.optimize else 'No'}")
    
    # Procesar el PDF
    success = process_pdf(
        input_file=input_file,
        output_file=output_file,
        language=args.language,
        deskew=args.deskew,
        clean=args.clean,
        optimize=args.optimize
    )
    
    if success:
        print("\n✓ Proceso completado con éxito.")
    else:
        print("\n✗ El proceso falló.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(1)
