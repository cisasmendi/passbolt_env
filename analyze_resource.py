#!/usr/bin/env python3
"""
Script para analizar y mostrar la información disponible del recurso Passbolt
"""

import os
import json
import argparse
from datetime import datetime

def analyze_resource(file_path):
    """
    Analizar el archivo de recurso y mostrar toda la información disponible
    
    Args:
        file_path (str): Ruta al archivo JSON con el recurso
    """
    
    # Leer el archivo JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verificar que es un archivo de recurso válido
    if 'resource' not in data:
        raise Exception("El archivo no contiene un recurso válido")
    
    resource = data['resource']
    
    print("=" * 60)
    print("ANÁLISIS DEL RECURSO PASSBOLT")
    print("=" * 60)
    
    # Información básica
    print("\\n📋 INFORMACIÓN BÁSICA:")
    print(f"  ID: {resource.get('id', 'N/A')}")
    print(f"  Tipo de recurso: {resource.get('resource_type_id', 'N/A')}")
    print(f"  Personal: {'Sí' if resource.get('personal', False) else 'No'}")
    print(f"  Eliminado: {'Sí' if resource.get('deleted', False) else 'No'}")
    print(f"  Expirado: {resource.get('expired', 'No')}")
    
    # Fechas
    print("\\n📅 FECHAS:")
    created = resource.get('created')
    modified = resource.get('modified')
    if created:
        print(f"  Creado: {created}")
    if modified:
        print(f"  Modificado: {modified}")
    
    # Metadata
    print("\\n🔒 METADATA:")
    print(f"  Key Type: {resource.get('metadata_key_type', 'N/A')}")
    print(f"  Key ID: {resource.get('metadata_key_id', 'N/A')}")
    print(f"  Metadata encriptado: {'Sí' if resource.get('metadata') else 'No'}")
    print(f"  Metadata descifrado: {'Sí' if data.get('decrypted_metadata') else 'No'}")
    
    if data.get('decrypted_metadata'):
        metadata = data['decrypted_metadata']
        print(f"    - Nombre: {metadata.get('name', 'N/A')}")
        print(f"    - Username: {metadata.get('username', 'N/A')}")
        print(f"    - Descripción: {metadata.get('description', 'N/A')}")
        if 'uris' in metadata:
            print(f"    - URIs: {', '.join(metadata['uris']) if metadata['uris'] else 'Ninguna'}")
    
    # Secret descifrado (información del servidor SSH)
    print("\\n🔑 DATOS DESCIFRADOS (SSH SERVER):")
    decrypted_secret = data.get('decrypted_secret')
    if decrypted_secret and 'custom_fields' in decrypted_secret:
        custom_fields = decrypted_secret['custom_fields']
        
        # Mapear los campos comunes de SSH
        field_mapping = {
            0: "🖥️  IP/Host",
            1: "🔌 Puerto",
            2: "👤 Usuario",
            3: "🔑 Contraseña"
        }
        
        for i, field in enumerate(custom_fields):
            field_name = field_mapping.get(i, f"Campo {i+1}")
            field_value = field.get('secret_value', 'N/A')
            field_type = field.get('type', 'N/A')
            print(f"  {field_name}: {field_value} ({field_type})")
        
        # Información de conexión SSH completa
        if len(custom_fields) >= 4:
            host = custom_fields[0].get('secret_value', '')
            port = custom_fields[1].get('secret_value', '')
            user = custom_fields[2].get('secret_value', '')
            password = custom_fields[3].get('secret_value', '')
            
            print(f"\\n🚀 COMANDO SSH:")
            print(f"  ssh {user}@{host} -p {port}")
            print(f"  Password: {password}")
    else:
        print("  ❌ No hay datos descifrados disponibles")
    
    # Permisos
    print("\\n👥 PERMISOS:")
    permissions = resource.get('permissions', [])
    for i, perm in enumerate(permissions):
        perm_type = perm.get('type', 'N/A')
        aro_key = perm.get('aro_foreign_key', 'N/A')
        print(f"  {i+1}. Usuario {aro_key}: Tipo {perm_type}")
    
    # Folder parent
    folder_parent = resource.get('folder_parent_id')
    if folder_parent:
        print(f"\\n📁 CARPETA PADRE: {folder_parent}")
    
    print("\\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Analizar archivo de recurso de Passbolt")
    parser.add_argument('file', help="Archivo JSON con el recurso de Passbolt")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[ERROR] Archivo no encontrado: {args.file}")
        return 1
    
    try:
        analyze_resource(args.file)
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())