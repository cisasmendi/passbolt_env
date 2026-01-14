#!/usr/bin/env python3
"""
Script simplificado para obtener recursos de Passbolt
Incluye opciones para listar y descargar recursos específicos
"""

import os
import json
import argparse
from dotenv import load_dotenv
from passbolt_fetch_resource import PassboltAPI

# Cargar variables de entorno
load_dotenv()

PASSBOLT_URL = os.getenv('PASSBOLT_URL')
RESOURCE_ID = os.getenv('RESOURCE_ID')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')


def list_resources(api, limit=20, search=None):
    """Lista los recursos disponibles"""
    
    url = f"{api.base_url}/resources.json"
    params = []
    
    # Incluir información básica
    params.extend([
        "contain[secret]=0",
        "contain[favorite]=1",
        "contain[permission]=1"
    ])
    
    # Nota: filter[search] no funciona con metadata cifrado en v5
    # Haremos el filtro del lado del cliente después de descifrar
    
    if params:
        url += "?" + "&".join(params)
    
    print(f"\n→ Listando recursos...")
    
    # Usar la sesión con cookie de autenticación
    response = api.session.get(url)
    response.raise_for_status()
    
    data = response.json()
    all_resources = data['body']
    
    print(f"✓ Se obtuvieron {len(all_resources)} recursos del servidor")
    
    # Descifrar y filtrar recursos
    filtered_resources = []
    
    if search:
        print(f"→ Filtrando por: '{search}'...")
        search_lower = search.lower()
    
    for resource in all_resources:
        resource_id = resource.get('id', '')
        
        # Intentar obtener datos de metadata cifrado (v5) o campos directos (v4)
        name = 'Sin nombre'
        username = ''
        uri = ''
        description = ''
        
        # Si tiene metadata cifrado (v5), descifrarlo
        if 'metadata' in resource and resource['metadata']:
            try:
                decrypted_metadata_str = api.decrypt_secret(resource['metadata'])
                decrypted_metadata = json.loads(decrypted_metadata_str)
                name = decrypted_metadata.get('name', 'Sin nombre')
                username = decrypted_metadata.get('username', '')
                description = decrypted_metadata.get('description', '')
                uris = decrypted_metadata.get('uris', [])
                if uris and len(uris) > 0:
                    uri = uris[0].get('uri', '') if isinstance(uris[0], dict) else uris[0]
            except Exception as e:
                # Si falla el descifrado, usar valores por defecto
                name = f"[Error descifrado]"
        else:
            # Fallback a campos directos (v4 o recursos sin metadata)
            name = resource.get('name', 'Sin nombre')
            username = resource.get('username', '')
            uri = resource.get('uri', '')
            description = resource.get('description', '')
        
        # Aplicar filtro de búsqueda (case-insensitive)
        if search:
            search_text = f"{name} {username} {uri} {description}".lower()
            if search_lower not in search_text:
                continue  # Saltar este recurso
        
        # Agregar a la lista filtrada
        filtered_resources.append({
            'id': resource_id,
            'name': name,
            'username': username,
            'uri': uri
        })
    
    # Aplicar límite
    display_resources = filtered_resources[:limit]
    
    print(f"✓ Se encontraron {len(filtered_resources)} recursos que coinciden\n")
    print("=" * 100)
    print(f"{'ID':<38} {'Nombre':<30} {'Username':<20} {'URI':<20}")
    print("=" * 100)
    
    for res in display_resources:
        # Truncar para ajustar a la tabla
        name_display = res['name'][:28]
        username_display = res['username'][:18]
        uri_display = res['uri'][:18]
        
        print(f"{res['id']:<38} {name_display:<30} {username_display:<20} {uri_display:<20}")
    
    if len(filtered_resources) > limit:
        print(f"\n... y {len(filtered_resources) - limit} más")
    
    print("=" * 100)
    
    return filtered_resources

def view_resource(api, resource_id):



def main():
    parser = argparse.ArgumentParser(
        description='Cliente CLI para la API de Passbolt',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Listar todos los recursos
  python passbolt_cli.py --list
  
  # Listar recursos con búsqueda
  python passbolt_cli.py --list --search "password"
  
  # Descargar un recurso específico en formato JSON
  python passbolt_cli.py --download RESOURCE_ID --json
  
  # Descargar el recurso en formato ENV
  python passbolt_cli.py --download RESOURCE_ID --env
  
  # Descargar en ambos formatos
  python passbolt_cli.py --download RESOURCE_ID -j -e
        """
    )
    
    parser.add_argument('--list', '-l', action='store_true',
                        help='Listar todos los recursos disponibles')
    parser.add_argument('--search', '-s', type=str,
                        help='Buscar recursos por nombre/descripción')
    parser.add_argument('--view', '-d', nargs='?', const=RESOURCE_ID,
                        help='Ver un recurso específico (usa RESOURCE_ID del config si no se especifica)')
    parser.add_argument('--limit', type=int, default=50,
                        help='Límite de recursos a mostrar en el listado (default: 50)')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Guardar el recurso en formato JSON en out/')
    parser.add_argument('--env', '-e', action='store_true',
                        help='Guardar el recurso en formato .env en out/')
    
    args = parser.parse_args()
    
    # Validar que se especificó al menos una acción
    if not any([args.list, args.view]):
        parser.print_help()
        return
    
    print("=" * 70)
    print("PASSBOLT API CLIENT")
    print("=" * 70)
    
    try:
        # Inicializar API
        api = PassboltAPI(PASSBOLT_URL, PRIVATE_KEY, PASSPHRASE)
        
        # Login
        print("\n→ Autenticando...")
        api.login()
        print("✓ Autenticación exitosa")
        
        # Ejecutar acción solicitada
        if args.list:
            list_resources(api, limit=args.limit, search=args.search)
        
        if args.view:
            view_resource(api, args.view)
        
        print("\n" + "=" * 70)
        print("✓ OPERACIÓN COMPLETADA")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
