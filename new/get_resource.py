#!/usr/bin/env python3
"""
Script para descifrar metadata de recursos de Passbolt
"""

import os
import json
from dotenv import load_dotenv
from passbolt_gpgauth import PassboltGPGAuth

load_dotenv()

def main():
    """Obtiene y descifra un recurso de Passbolt"""
    
    # Configuración
    passbolt_url = os.getenv('PASSBOLT_URL')
    private_key = os.getenv('PRIVATE_KEY')
    passphrase = os.getenv('PASSPHRASE', '')
    resource_id = os.getenv('RESOURCE_ID')
    
    if not all([passbolt_url, private_key, resource_id]):
        print("❌ Error: Configura PASSBOLT_URL, PRIVATE_KEY y RESOURCE_ID en .env")
        return
    
    # Crear cliente
    client = PassboltGPGAuth(
        base_url=passbolt_url,
        private_key=private_key,
        passphrase=passphrase if passphrase else None
    )
    
    # Autenticar
    print("\n" + "="*60)
    if not client.login():
        print("❌ Error en la autenticación")
        return
    
    print("\n" + "="*60)
    print("📦 OBTENIENDO RECURSO")
    print("="*60)
    
    # Obtener recurso
    resource = client.get_resource(resource_id)
    
    if not resource:
        print("❌ No se pudo obtener el recurso")
        return
    
    body = resource.get('body', {})
    
    print(f"\n📋 Información del Recurso:")
    print(f"   ID: {body.get('id')}")
    print(f"   Creado: {body.get('created')}")
    print(f"   Modificado: {body.get('modified')}")
    print(f"   Personal: {body.get('personal')}")
    
    # Obtener metadata cifrado
    encrypted_metadata = body.get('metadata')
    
    if not encrypted_metadata:
        print("\n⚠️  No hay metadata cifrado en este recurso")
        return
    
    print(f"\n🔐 Metadata cifrado encontrado")
    print(f"   Longitud: {len(encrypted_metadata)} caracteres")
    
    # Descifrar metadata
    try:
        print("\n🔓 Descifrando metadata...")
        decrypted_metadata = client._decrypt_message(encrypted_metadata)
        
        # Intentar parsear como JSON
        try:
            metadata_json = json.loads(decrypted_metadata)
            print("\n✅ Metadata descifrado (JSON):")
            print(json.dumps(metadata_json, indent=2, ensure_ascii=False))
            
            # Mostrar campos importantes si existen
            if 'name' in metadata_json:
                print(f"\n🏷️  Nombre: {metadata_json['name']}")
            if 'username' in metadata_json:
                print(f"👤 Usuario: {metadata_json['username']}")
            if 'uri' in metadata_json:
                print(f"🌐 URI: {metadata_json['uri']}")
            if 'description' in metadata_json:
                print(f"📝 Descripción: {metadata_json['description']}")
            
        except json.JSONDecodeError:
            # No es JSON, mostrar como texto plano
            print("\n✅ Metadata descifrado (texto plano):")
            print(decrypted_metadata)
            
    except Exception as e:
        print(f"\n❌ Error al descifrar metadata: {str(e)}")
    
    print("\n" + "="*60)
    
    # Opcional: cerrar sesión
    # client.logout()


if __name__ == '__main__':
    main()
