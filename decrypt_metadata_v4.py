#!/usr/bin/env python3
"""
Script simplificado para intentar descifrar metadata directamente (método v4)
"""

import os
import json
import gnupg
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')


def decrypt_metadata_direct(file_path, output_file=None):
    """
    Intentar descifrar metadata directamente usando descifrado PGP tradicional
    
    Args:
        file_path (str): Ruta al archivo JSON con el recurso
        output_file (str): Ruta del archivo de salida (opcional)
    """
    
    if not all([PRIVATE_KEY, PASSPHRASE]):
        raise Exception("Variables de entorno requeridas no configuradas: PRIVATE_KEY, PASSPHRASE")
    
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
    
    # Configurar GPG
    gpg = gnupg.GPG()
    
    # Importar la clave privada
    import_result = gpg.import_keys(PRIVATE_KEY)
    if import_result.count == 0:
        raise Exception("No se pudo importar la clave privada PGP")
    
    print(f"[OK] Clave PGP importada: {import_result.fingerprints[0]}")
    
    # Intentar descifrar metadata directamente
    print("\\n> Intentando descifrado directo del metadata...")
    
    metadata_blob = resource['metadata']
    
    try:
        # Intentar descifrado directo
        decrypted = gpg.decrypt(metadata_blob, passphrase=PASSPHRASE)
        
        if decrypted.ok:
            print("[OK] Metadata descifrado exitosamente (método v4)")
            
            # Parsear como JSON
            try:
                decrypted_metadata = json.loads(str(decrypted))
                
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
                print("\\n=== METADATA DESENCRIPTADO ===")
                print(json.dumps(decrypted_metadata, indent=2, ensure_ascii=False))
                
                return decrypted_metadata
                
            except json.JSONDecodeError as e:
                print(f"[WARN] El contenido descifrado no es JSON válido: {e}")
                print(f"Contenido raw: {str(decrypted)[:200]}...")
                return None
                
        else:
            print(f"[WARN] Error en descifrado: {decrypted.status}")
            print(f"Stderr: {decrypted.stderr}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Excepción durante descifrado: {e}")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Descifrar metadata directamente (método v4)")
    parser.add_argument('file', help="Archivo JSON con el recurso de Passbolt")
    parser.add_argument('-o', '--output', help="Archivo de salida (opcional)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[ERROR] Archivo no encontrado: {args.file}")
        return 1
    
    try:
        result = decrypt_metadata_direct(args.file, args.output)
        return 0 if result else 1
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    exit(main())