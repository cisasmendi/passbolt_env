#!/usr/bin/env python3
"""
Script de prueba para verificar la importación de la clave privada PGP
"""

import os
import gnupg
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')

def test_pgp_key():
    """Probar la importación de la clave PGP"""
    
    print("=== Prueba de importación de clave PGP ===")
    print(f"Tiene clave privada: {'Sí' if PRIVATE_KEY else 'No'}")
    print(f"Tiene passphrase: {'Sí' if PASSPHRASE else 'No'}")
    
    if not PRIVATE_KEY:
        print("[ERROR] No hay clave privada configurada")
        return False
    
    print(f"Longitud de clave: {len(PRIVATE_KEY)} caracteres")
    print(f"Primeros 50 caracteres: {PRIVATE_KEY[:50]}")
    print(f"Últimos 50 caracteres: {PRIVATE_KEY[-50:]}")
    
    try:
        # Crear instancia GPG
        gpg = gnupg.GPG()
        
        # Intentar importar la clave
        print("\n> Intentando importar clave...")
        import_result = gpg.import_keys(PRIVATE_KEY)
        
        print(f"Resultado de importación:")
        print(f"  - Count: {import_result.count}")
        print(f"  - Imported: {import_result.imported}")
        print(f"  - Fingerprints: {import_result.fingerprints}")
        print(f"  - Results: {import_result.results}")
        
        if import_result.count > 0:
            print("[OK] Clave importada exitosamente")
            fingerprint = import_result.fingerprints[0]
            print(f"Fingerprint: {fingerprint}")
            
            # Listar claves disponibles
            keys = gpg.list_keys(True)  # True para claves privadas
            print(f"\nClaves privadas disponibles: {len(keys)}")
            for i, key in enumerate(keys):
                print(f"  {i+1}. {key.get('fingerprint', 'N/A')} - {key.get('uids', ['N/A'])[0]}")
            
            return True
        else:
            print("[ERROR] No se pudo importar la clave")
            return False
            
    except Exception as e:
        print(f"[ERROR] Excepción durante importación: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pgp_key()