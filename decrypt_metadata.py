#!/usr/bin/env python3
"""
Script para desencriptar metadata de un archivo JSON de recurso de Passbolt
Utiliza la funcionalidad existente para desencriptar metadata v4 y v5
"""

import os
import json
import argparse
from dotenv import load_dotenv
from passbolt_fetch_resource import PassboltAPI

# Cargar variables de entorno
load_dotenv()

PASSBOLT_URL = os.getenv('PASSBOLT_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')


def decrypt_metadata_from_file(file_path, output_file=None):
    """
    Desencriptar metadata de un archivo JSON de recurso de Passbolt
    
    Args:
        file_path (str): Ruta al archivo JSON con el recurso
        output_file (str): Ruta del archivo de salida (opcional)
    """
    
    if not all([PASSBOLT_URL, PRIVATE_KEY, PASSPHRASE]):
        raise Exception("Variables de entorno requeridas no configuradas: PASSBOLT_URL, PRIVATE_KEY, PASSPHRASE")
    
    # Crear instancia de la API (solo para usar métodos de descifrado)
    print(f"[INFO] URL: {PASSBOLT_URL}")
    print(f"[INFO] Tiene clave privada: {'Sí' if PRIVATE_KEY else 'No'}")
    print(f"[INFO] Tiene passphrase: {'Sí' if PASSPHRASE else 'No'}")
    
    api = PassboltAPI(PASSBOLT_URL, PRIVATE_KEY, PASSPHRASE)
    
    # Leer el archivo JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verificar que es un archivo de recurso válido
    if 'resource' not in data:
        raise Exception("El archivo no contiene un recurso válido")
    
    resource = data['resource']
    
    # Verificar si ya tiene metadata desencriptado
    if data.get('decrypted_metadata') is not None:
        print("[INFO] El archivo ya tiene metadata desencriptado")
        print(json.dumps(data['decrypted_metadata'], indent=2))
        return data['decrypted_metadata']
    
    # Verificar si hay metadata para desencriptar
    if not resource.get('metadata'):
        print("[WARN] El recurso no tiene metadata para desencriptar")
        return None
    
    print(f"[INFO] Recurso ID: {resource.get('id')}")
    print(f"[INFO] Metadata key type: {resource.get('metadata_key_type', 'N/A')}")
    print(f"[INFO] Metadata key ID: {resource.get('metadata_key_id', 'N/A')}")
    
    # Desencriptar metadata
    print("\n> Descifrando metadata...")
    try:
        decrypted_metadata = api.decrypt_metadata(resource)
        
        if decrypted_metadata:
            print("[OK] Metadata desencriptado exitosamente")
            
            # Actualizar el objeto data con el metadata desencriptado
            data['decrypted_metadata'] = decrypted_metadata
            
            # Guardar archivo actualizado
            if output_file:
                output_path = output_file
            else:
                # Crear archivo con sufijo _decrypted
                base_name = os.path.splitext(file_path)[0]
                output_path = f"{base_name}_decrypted.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Archivo actualizado guardado en: {output_path}")
            
            # Mostrar metadata desencriptado
            print("\n=== METADATA DESENCRIPTADO ===")
            print(json.dumps(decrypted_metadata, indent=2, ensure_ascii=False))
            
            return decrypted_metadata
        else:
            print("[ERROR] No se pudo desencriptar el metadata")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error al desencriptar metadata: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Desencriptar metadata de un archivo de recurso de Passbolt")
    parser.add_argument('file', help="Archivo JSON con el recurso de Passbolt")
    parser.add_argument('-o', '--output', help="Archivo de salida (opcional)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[ERROR] Archivo no encontrado: {args.file}")
        return 1
    
    try:
        result = decrypt_metadata_from_file(args.file, args.output)
        return 0 if result else 1
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    exit(main())