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


def download_resource(api, resource_id, save_json=False, save_env=False):
    """Descarga un recurso específico"""
    
    # Obtener tipos de recursos para mejor contexto
    resource_types = {}
    try:
        resource_types = api.get_resource_types()
        print(f"✓ Tipos de recursos cargados: {len(resource_types)}")
    except Exception as e:
        print(f"⚠ No se pudieron cargar tipos de recursos: {e}")
    
    resource = api.get_resource(resource_id, include_secret=True, include_permissions=True)
    
    # Obtener información del tipo de recurso
    resource_type_info = None
    resource_type_id = resource.get('resource_type_id')
    if resource_type_id and resource_type_id in resource_types:
        resource_type_info = resource_types[resource_type_id]
        print(f"→ Tipo de recurso: {resource_type_info['name']} ({resource_type_info['slug']})")
    
    # Descifrar metadata si existe (recursos v5)
    decrypted_metadata = None
    if 'metadata' in resource and resource['metadata']:
        print("\n→ Descifrando metadata...")
        try:
            decrypted_metadata_str = api.decrypt_secret(resource['metadata'])
            decrypted_metadata = json.loads(decrypted_metadata_str)
            print(f"✓ Metadata descifrado")
        except Exception as e:
            print(f"✗ Error al descifrar metadata: {e}")
    
    # Mostrar información
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
            # Puede ser un objeto con 'uri' o un string directo
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
    
    # Descifrar secreto si existe
    secret_value = None
    if 'secrets' in resource and resource['secrets']:
        secret_data = resource['secrets'][0].get('data') if isinstance(resource['secrets'], list) else resource['secrets'].get('data')
        
        if secret_data:
            print("\n→ Descifrando secreto...")
            try:
                secret_value_str = api.decrypt_secret(secret_data)
                print(f"✓ Secreto descifrado")
                
                # Intentar parsear como JSON
                try:
                    secret_value = json.loads(secret_value_str)
                    print("\nContenido del secreto (JSON):")
                    print(json.dumps(secret_value, indent=2, ensure_ascii=False))
                except:
                    # Si no es JSON, crear un objeto con el contenido como texto
                    secret_value = {"value": secret_value_str}
                    print(f"\nContenido del secreto (texto plano):")
                    print(f"  {secret_value_str}")
                    
            except Exception as e:
                print(f"✗ Error al descifrar: {e}")
    
    # Crear directorio de salida si no existe
    if save_json or save_env:
        os.makedirs('out', exist_ok=True)
    
    # Procesamiento común para ambos formatos de salida
    # Extraer valores para el archivo .env
    name = ''
    username = ''
    password = ''
    uri = ''
    description = ''
    
    # Obtener datos de metadata descifrado o del recurso
    if decrypted_metadata:
        name = decrypted_metadata.get('name', '')
        username = decrypted_metadata.get('username', '')
        uri_list = decrypted_metadata.get('uris', [])
        if uri_list and len(uri_list) > 0:
            uri = uri_list[0].get('uri', '') if isinstance(uri_list[0], dict) else uri_list[0]
        description = decrypted_metadata.get('description', '')
    else:
        name = resource.get('name', '')
        username = resource.get('username', '')
        uri = resource.get('uri', '')
        description = resource.get('description', '')
    
    # Obtener password y otros campos del secreto descifrado
    if secret_value:
        # Manejar estructura v5-default (password directo)
        if resource_type_info and resource_type_info.get('slug') == 'v5-default':
            password = secret_value.get('password', '')
            # Para v5-default, también extraer otros campos estándar del secreto
            if not username and 'username' in secret_value:
                username = secret_value.get('username', '')
            if not uri and 'uri' in secret_value:
                uri = secret_value.get('uri', '')
            if not description and 'description' in secret_value:
                description = secret_value.get('description', '')
            if not name and 'name' in secret_value:
                name = secret_value.get('name', '')
        else:
            # Estructura con custom_fields
            if isinstance(secret_value, dict):
                password = secret_value.get('password', secret_value.get('value', ''))
            else:
                password = str(secret_value)

    # Guardar como JSON si se solicita
    if save_json:
        output_file = f"out/{resource_id}.json"
        
        # Crear una estructura simple clave-valor
        output_data = {
            "resource_id": resource.get('id'),
            "created": resource.get('created'),
            "modified": resource.get('modified'),
            "resource_type_id": resource.get('resource_type_id'),
            "folder_parent_id": resource.get('folder_parent_id'),
        }
        
        # Agregar información del tipo de recurso si está disponible
        if resource_type_info:
            output_data.update({
                "resource_type_name": resource_type_info.get('name', ''),
                "resource_type_slug": resource_type_info.get('slug', '')
            })
        
        # Agregar información de metadatos procesada
        metadata_status = "decrypted" if decrypted_metadata else "fallback - could not decrypt"
        output_data.update({
            "name": name,
            "username": username,
            "description": description,
            "uri": uri,
            "metadata_status": metadata_status
        })
        
        # Agregar campos del secreto descifrado directamente como clave-valor
        if secret_value:
            # Manejar estructura v5-default (password directo)
            if resource_type_info and resource_type_info.get('slug') == 'v5-default':
                if 'password' in secret_value:
                    output_data['password'] = secret_value.get('password', '')
                if 'description' in secret_value:
                    output_data['secret_description'] = secret_value.get('description', '')
                # Otros campos estándar que puede tener v5-default
                for field in ['username', 'uri', 'totp']:
                    if field in secret_value:
                        output_data[field] = secret_value.get(field, '')
            
            # Manejar estructura con custom_fields
            elif 'custom_fields' in secret_value and secret_value['custom_fields']:
                # Determinar nombres de campos basándose en el tipo de recurso
                field_names = []
                if resource_type_info:
                    slug = resource_type_info.get('slug', '')
                    if 'ssh' in slug.lower():
                        field_names = ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_password']
                    elif 'database' in slug.lower() or 'mysql' in slug.lower() or 'postgres' in slug.lower():
                        field_names = ['db_host', 'db_port', 'db_user', 'db_password']
                    elif 'web' in slug.lower() or 'website' in slug.lower():
                        field_names = ['web_url', 'web_port', 'web_user', 'web_password']
                    elif 'api' in slug.lower():
                        field_names = ['api_endpoint', 'api_port', 'api_key', 'api_secret']
                    else:
                        # Usar nombres genéricos del servidor
                        field_names = ['server_host', 'server_port', 'server_user', 'server_password']
                else:
                    # Fallback a nombres genéricos
                    field_names = ['server_ip', 'server_port', 'server_user', 'server_password']
                
                for i, field in enumerate(secret_value['custom_fields']):
                    field_name = field_names[i] if i < len(field_names) else f"custom_field_{i+1}"
                    output_data[field_name] = field.get('secret_value', '')
                    # También agregar metadatos del campo si es útil
                    output_data[f"{field_name}_type"] = field.get('type', 'text')
                    output_data[f"{field_name}_id"] = field.get('id', '')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Datos JSON guardados en: {output_file}")
        print(f"  - Estructura simplificada clave-valor")
    
    # Guardar como ENV si se solicita
    if save_env:
        output_file = f"out/.env"
        
        # Procesar custom_fields (v5)
        custom_env_vars = {}
        if decrypted_metadata and 'custom_fields' in decrypted_metadata and decrypted_metadata['custom_fields']:
            # Crear mapeo de IDs a metadata_keys
            metadata_fields = {cf['id']: cf.get('metadata_key', '') 
                             for cf in decrypted_metadata['custom_fields']}
            
            # Combinar con valores del secreto
            if secret_value and 'custom_fields' in secret_value and secret_value['custom_fields']:
                for secret_field in secret_value['custom_fields']:
                    field_id = secret_field.get('id')
                    if field_id in metadata_fields and metadata_fields[field_id]:
                        key = metadata_fields[field_id]
                        value = secret_field.get('secret_value', '')
                        custom_env_vars[key] = value
        elif secret_value and 'custom_fields' in secret_value and secret_value['custom_fields']:
            # Si no hay metadatos pero sí hay campos custom en el secreto, usar nombres genéricos basados en tipo de recurso
            print("→ Los metadatos no se pudieron descifrar, usando nombres basados en el tipo de recurso...")
            
            # Determinar nombres de campos basándose en el tipo de recurso
            field_names = []
            if resource_type_info:
                slug = resource_type_info.get('slug', '')
                if 'ssh' in slug.lower():
                    field_names = ['SSH_HOST', 'SSH_PORT', 'SSH_USER', 'SSH_PASSWORD']
                elif 'database' in slug.lower() or 'mysql' in slug.lower() or 'postgres' in slug.lower():
                    field_names = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD']
                elif 'web' in slug.lower() or 'website' in slug.lower():
                    field_names = ['WEB_URL', 'WEB_PORT', 'WEB_USER', 'WEB_PASSWORD']
                elif 'api' in slug.lower():
                    field_names = ['API_ENDPOINT', 'API_PORT', 'API_KEY', 'API_SECRET']
                else:
                    # Usar nombres genéricos del servidor
                    field_names = ['SERVER_HOST', 'SERVER_PORT', 'SERVER_USER', 'SERVER_PASSWORD']
            else:
                # Fallback a nombres genéricos
                field_names = ['SERVER_IP', 'SERVER_PORT', 'SERVER_USER', 'SERVER_PASSWORD']
            
            for i, secret_field in enumerate(secret_value['custom_fields']):
                if i < len(field_names):
                    key = field_names[i]
                else:
                    key = f"CUSTOM_FIELD_{i+1}"
                value = secret_field.get('secret_value', '')
                custom_env_vars[key] = value
        
        # Escribir archivo .env
        with open(output_file, 'w', encoding='utf-8') as f:
            # Escribir comentario con información del recurso y tipo
            if resource_type_info:
                f.write(f"# Resource Type: {resource_type_info['name']} ({resource_type_info['slug']})\n")
            f.write(f"# Resource: {name}\n")
            if description:
                f.write(f"# {description}\n")
            f.write(f"\n")
            f.write(f"RESOURCE_ID={resource_id}\n")
            if name:
                f.write(f"RESOURCE_NAME={name}\n")
            if resource_type_info:
                f.write(f"RESOURCE_TYPE={resource_type_info['slug']}\n")
            if username:
                f.write(f"USERNAME={username}\n")
            if password:
                f.write(f"PASSWORD={password}\n")
            if uri:
                f.write(f"URI={uri}\n")
            
            # Agregar custom fields
            if custom_env_vars:
                f.write(f"\n# Custom Fields\n")
                for key, value in custom_env_vars.items():
                    f.write(f"{key}={value}\n")
        
        print(f"\n✓ Datos ENV guardados en: {output_file}")
    
    return resource, decrypted_metadata, secret_value


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
    parser.add_argument('--download', '-d', nargs='?', const=RESOURCE_ID,
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
        
        if args.download:
            download_resource(api, args.download, save_json=args.json, save_env=args.env)
        
        print("\n" + "=" * 70)
        print("✓ OPERACIÓN COMPLETADA")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
