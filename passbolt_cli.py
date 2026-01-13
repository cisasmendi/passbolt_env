#!/usr/bin/env python3
"""
Cliente CLI refactorizado para la API de Passbolt
Incluye opciones para listar y descargar recursos específicos
"""

import argparse
import json

from config import config
from passbolt_fetch_resource import PassboltAPI
from services import ResourceService
from formatters import ResourceFormatter
from exceptions import PassboltError, ConfigurationError


def list_resources(api, limit=20, search=None):
    """Lista los recursos disponibles usando el servicio refactorizado"""
    
    print(f"\n→ Listando recursos...")
    
    resource_service = ResourceService(api)
    filtered_resources = resource_service.list_resources_with_decrypted_info(search=search, limit=limit)
    
    print(f"✓ Se encontraron {len(filtered_resources)} recursos que coinciden\n")
    print("=" * 100)
    print(f"{'ID':<38} {'Nombre':<30} {'Username':<20} {'URI':<20}")
    print("=" * 100)
    
    for res in filtered_resources:
        # Truncar para ajustar a la tabla
        name_display = res['name'][:28]
        username_display = res['username'][:18]
        uri_display = res['uri'][:18]
        
        print(f"{res['id']:<38} {name_display:<30} {username_display:<20} {uri_display:<20}")
    
    print("=" * 100)
    
    return filtered_resources


def download_resource(api, resource_id, save_json=False, save_env=False):
    """Descarga un recurso específico usando los servicios refactorizados"""
    
    # Crear servicios
    resource_service = ResourceService(api)
    resource_types = resource_service.get_resource_types()
    formatter = ResourceFormatter(resource_types)
    
    # Obtener recurso con datos descifrados
    try:
        resource, decrypted_metadata, decrypted_secret = resource_service.get_resource_with_decrypted_content(resource_id)
    except Exception as e:
        print(f"✗ Error al obtener recurso: {e}")
        return None, None, None
    
    # Obtener información del tipo de recurso
    resource_type_info = None
    resource_type_id = resource.get('resource_type_id')
    if resource_type_id and resource_type_id in resource_types:
        resource_type_info = resource_types[resource_type_id]
        print(f"→ Tipo de recurso: {resource_type_info['name']} ({resource_type_info['slug']})")
    
    # Mostrar información del recurso
    _display_resource_info(resource, decrypted_metadata, decrypted_secret)
    
    # Extraer datos estructurados
    resource_data = formatter.extract_resource_data(resource, decrypted_metadata, decrypted_secret)
    
    # Guardar en formatos solicitados
    if save_json:
        json_file = formatter.format_as_json(resource_data)
        print(f"\n✓ Datos JSON guardados en: {json_file}")
        print(f"  - Estructura simplificada clave-valor")
    
    if save_env:
        env_file = formatter.format_as_env(resource_data)
        print(f"\n✓ Datos ENV guardados en: {env_file}")
    
    return resource, decrypted_metadata, decrypted_secret


def _display_resource_info(resource, decrypted_metadata, decrypted_secret):
    """Muestra la información del recurso en consola"""
    print("\n" + "=" * 70)
    print("INFORMACIÓN DEL RECURSO")
    print("=" * 70)
    print(f"ID:          {resource.get('id')}")
    
    # Usar metadata descifrado si está disponible
    if decrypted_metadata:
        print(f"Nombre:      {decrypted_metadata.get('name', 'N/A')}")
        print(f"Username:    {decrypted_metadata.get('username', 'N/A')}")
        uri_list = decrypted_metadata.get('uris', [])
        if uri_list and len(uri_list) > 0:
            uri = uri_list[0].get('uri', 'N/A') if isinstance(uri_list[0], dict) else uri_list[0]
        else:
            uri = 'N/A'
        print(f"URI:         {uri}")
        print(f"Descripción: {decrypted_metadata.get('description', 'N/A')}")
    else:
        print(f"Nombre:      {resource.get('name', 'N/A')}")
        print(f"Username:    {resource.get('username', 'N/A')}")
        print(f"URI:         {resource.get('uri', 'N/A')}")
        print(f"Descripción: {resource.get('description', 'N/A')}")
    
    print(f"Creado:      {resource.get('created')}")
    print(f"Modificado:  {resource.get('modified')}")
    
    # Mostrar contenido del secreto si existe
    if decrypted_secret:
        print("\nContenido del secreto:")
        if isinstance(decrypted_secret, dict):
            print(json.dumps(decrypted_secret, indent=2, ensure_ascii=False))
        else:
            print(f"  {decrypted_secret}")


def main():
    """Función principal del CLI"""
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
    parser.add_argument('--download', '-d', nargs='?', const=config.resource_id,
                        help='Descargar un recurso específico (usa RESOURCE_ID del config si no se especifica)')
    parser.add_argument('--limit', type=int, default=50,
                        help='Límite de recursos a mostrar en el listado (default: 50)')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Guardar el recurso en formato JSON en out/')
    parser.add_argument('--env', '-e', action='store_true',
                        help='Guardar el recurso en formato .env en out/')
    
    args = parser.parse_args()
    
    # Validar que se especificó al menos una acción
    if not any([args.list, args.download]):
        parser.print_help()
        return
    
    try:
        # Validar configuración
        config.validate()
        
        print("=" * 70)
        print("PASSBOLT API CLIENT (REFACTORIZADO)")
        print("=" * 70)
        
        # Inicializar API
        api = PassboltAPI()
        
        # Login
        print("\n→ Autenticando...")
        api.login()
        print("✓ Autenticación exitosa")
        
        # Ejecutar acción solicitada
        if args.list:
            list_resources(api, limit=args.limit, search=args.search)
        
        if args.download:
            download_resource(api, args.download, save_json=args.json, save_env=args.env)
        
        print("\n" + "=" * 70)
        print("✓ OPERACIÓN COMPLETADA")
        print("=" * 70)
        
    except ConfigurationError as e:
        print(f"\n✗ Error de configuración: {e}")
        print("Verifica tu archivo .env")
    except PassboltError as e:
        print(f"\n✗ Error de Passbolt: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()