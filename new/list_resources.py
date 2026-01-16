#!/usr/bin/env python3
"""
Script para listar todos los recursos disponibles en Passbolt
"""

import os
import json
from dotenv import load_dotenv
from passbolt_gpgauth import PassboltGPGAuth

load_dotenv()

def list_resources(client, page=1, limit=50):
    """
    Lista recursos disponibles
    
    Args:
        client: Cliente PassboltGPGAuth autenticado
        page: Número de página (default: 1)
        limit: Límite por página (default: 50)
        
    Returns:
        Lista de recursos
    """
    if not client.is_authenticated():
        print("❌ No hay sesión autenticada")
        return None
    
    from urllib.parse import urljoin
    url = urljoin(client.base_url, f'/resources.json?page={page}&limit={limit}')
    response = client.session.get(url)
    
    if response.status_code != 200:
        print(f"❌ Error listando recursos: {response.status_code}")
        return None
    
    return response.json()


def main():
    """Lista todos los recursos disponibles"""
    
    # Configuración
    passbolt_url = os.getenv('PASSBOLT_URL')
    private_key = os.getenv('PRIVATE_KEY')
    passphrase = os.getenv('PASSPHRASE', '')
    
    if not all([passbolt_url, private_key]):
        print("❌ Error: Configura PASSBOLT_URL y PRIVATE_KEY en .env")
        return
    
    # Crear cliente
    client = PassboltGPGAuth(
        base_url=passbolt_url,
        private_key=private_key,
        passphrase=passphrase if passphrase else None
    )
    
    # Autenticar
    if not client.login():
        print("❌ Error en la autenticación")
        return
    
    print("\n" + "="*60)
    print("📋 LISTANDO RECURSOS DISPONIBLES")
    print("="*60)
    
    # Listar recursos
    response = list_resources(client)
    
    if not response:
        print("❌ No se pudieron obtener los recursos")
        return
    
    resources = response.get('body', [])
    header = response.get('header', {})
    
    print(f"\n📊 Total de recursos encontrados: {len(resources)}")
    print(f"   Página: {header.get('pagination', {}).get('page', 1)}")
    print("-" * 60)
    
    # Mostrar cada recurso
    for idx, resource in enumerate(resources, 1):
        print(f"\n{idx}. 📦 Recurso")
        print(f"   ID: {resource.get('id')}")
        print(f"   Nombre: {resource.get('name', 'N/A')}")
        print(f"   Tipo: {resource.get('resource_type_id', 'N/A')}")
        print(f"   Creado: {resource.get('created', 'N/A')}")
        print(f"   Modificado: {resource.get('modified', 'N/A')}")
        
        # Si tiene URI
        if 'uri' in resource and resource['uri']:
            print(f"   🌐 URI: {resource['uri']}")
        
        # Si tiene username
        if 'username' in resource and resource['username']:
            print(f"   👤 Usuario: {resource['username']}")
    
    print("\n" + "="*60)
    print(f"✅ Se listaron {len(resources)} recursos exitosamente")
    print("="*60)
    
    # Opcional: preguntar si quiere ver el detalle de alguno
    print("\n💡 Para ver el secret de un recurso específico:")
    print("   1. Copia su ID")
    print("   2. Agrégalo a .env como RESOURCE_ID=<id>")
    print("   3. Ejecuta: python get_secret.py")


if __name__ == '__main__':
    main()
