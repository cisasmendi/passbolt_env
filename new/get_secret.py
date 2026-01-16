#!/usr/bin/env python3
"""
Script completo para obtener y descifrar recursos de Passbolt
Maneja claves compartidas (shared keys)
"""

import os
import json
from dotenv import load_dotenv
from passbolt_gpgauth import PassboltGPGAuth

load_dotenv()

def main():
    """Obtiene recurso con secreto descifrado"""
    
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
    if not client.login():
        print("❌ Error en la autenticación")
        return
    
    print("\n" + "="*60)
    print("📦 OBTENIENDO RECURSO CON SECRET")
    print("="*60)
    
    # Obtener recurso CON el secret (contain[secret]=1)
    resource = client.get_resource_with_secret(resource_id)
    
    if not resource:
        print("❌ No se pudo obtener el recurso")
        return
    
    body = resource.get('body', {})
    
    print(f"\n📋 Información del Recurso:")
    print(f"   ID: {body.get('id')}")
    print(f"   Creado: {body.get('created')}")
    print(f"   Modificado: {body.get('modified')}")
    
    # Obtener resource type para conocer los nombres de los campos
    resource_type_id = body.get('resource_type_id')
    field_names = {}
    
    if resource_type_id:
        resource_type = client.get_resource_type(resource_type_id)
        if resource_type and 'body' in resource_type:
            rt_body = resource_type['body']
            # La definición puede venir como string JSON o como dict
            definition = rt_body.get('definition')
            if isinstance(definition, str):
                try:
                    definition = json.loads(definition)
                except:
                    pass
            
            if isinstance(definition, dict) and 'resource' in definition:
                # Obtener nombres de custom_fields desde la definición
                if 'custom_fields' in definition['resource']:
                    for field_def in definition['resource']['custom_fields']:
                        field_names[field_def['id']] = field_def.get('label', field_def.get('name', 'Sin nombre'))
    
    # Descifrar metadata si está cifrado
    metadata_decrypted = None
    if 'metadata' in body:
        metadata_raw = body['metadata']
        metadata_key_id = body.get('metadata_key_id')
        metadata_key_type = body.get('metadata_key_type')
        
        if isinstance(metadata_raw, str) and metadata_raw.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                print(f"\n🔓 Descifrando metadata...")
                print(f"   Tipo de clave: {metadata_key_type}")
                print(f"   ID de clave: {metadata_key_id}")
                
                # Si es una shared_key, necesitamos obtenerla primero
                if metadata_key_type == 'shared_key' and metadata_key_id:
                    print(f"   Obteniendo clave compartida...")
                    
                    # Obtener la metadata key
                    metadata_key_info = client.get_metadata_keys(metadata_key_id)
                    
                    if metadata_key_info and 'metadata_private_keys' in metadata_key_info:
                        # Buscar la clave privada cifrada para nuestro usuario
                        for private_key in metadata_key_info['metadata_private_keys']:
                            encrypted_shared_key = private_key.get('data')
                            if encrypted_shared_key:
                                try:
                                    # Descifrar la clave compartida con nuestra clave privada
                                    print(f"   Descifrando clave compartida...")
                                    shared_key = client._decrypt_message(encrypted_shared_key)
                                    print(f"   ✅ Clave compartida descifrada")
                                    
                                    # Importar la clave compartida temporalmente
                                    stdout, stderr, returncode = client._run_gpg_command(
                                        ['--import'],
                                        input_data=shared_key
                                    )
                                    
                                    if returncode == 0:
                                        print(f"   ✅ Clave compartida importada")
                                        
                                        # Ahora intentar descifrar el metadata con la clave compartida
                                        try:
                                            metadata_text = client._decrypt_message(metadata_raw)
                                            metadata_decrypted = json.loads(metadata_text)
                                            print(f"   ✅ Metadata descifrado exitosamente")
                                        except Exception as e_decrypt:
                                            print(f"   ⚠️  Error descifrando metadata con clave compartida: {str(e_decrypt)}")
                                        break
                                    else:
                                        print(f"   ⚠️  Error importando clave compartida: {stderr}")
                                    
                                except Exception as e:
                                    print(f"   ⚠️  Error con esta clave: {str(e)}")
                                    continue
                    else:
                        print(f"   ⚠️  No se encontraron claves privadas para esta metadata key")
                else:
                    # Intentar descifrar directamente
                    metadata_text = client._decrypt_message(metadata_raw)
                    metadata_decrypted = json.loads(metadata_text)
                    print(f"   ✅ Metadata descifrado exitosamente")
                    
            except Exception as e:
                print(f"   ⚠️  Error descifrando metadata: {str(e)}")
        elif isinstance(metadata_raw, dict):
            metadata_decrypted = metadata_raw
    
    # Mostrar metadata descifrado
    if metadata_decrypted:
        print(f"\n📝 Metadata:")
        if 'name' in metadata_decrypted:
            print(f"   🏷️  Nombre: {metadata_decrypted['name']}")
        if 'username' in metadata_decrypted:
            print(f"   👤 Usuario: {metadata_decrypted['username']}")
        if 'uris' in metadata_decrypted and metadata_decrypted['uris']:
            print(f"   🌐 URI: {metadata_decrypted['uris'][0]}")
        if 'description' in metadata_decrypted and metadata_decrypted['description']:
            print(f"   📝 Descripción: {metadata_decrypted['description']}")
    
    # Mostrar secret descifrado
    if 'secrets' in body and body['secrets']:
        secret = body['secrets'][0]
        print(f"\n🔓 Secret descifrado:")
        
        # El secret data puede venir cifrado
        if 'data' in secret:
            try:
                # Intentar descifrar si está cifrado
                secret_data = secret['data']
                
                if secret_data.startswith('-----BEGIN PGP MESSAGE-----'):
                    print("   (Descifrando secret...)")
                    decrypted_secret = client._decrypt_message(secret_data)
                    
                    # Intentar parsear como JSON
                    try:
                        secret_json = json.loads(decrypted_secret)
                        print(json.dumps(secret_json, indent=2, ensure_ascii=False))
                        
                        # Mostrar password si existe
                        if 'password' in secret_json:
                            print(f"\n   🔑 Password: {secret_json['password']}")
                        
                        # Mostrar custom_fields con nombres desde metadata o resource type
                        if 'custom_fields' in secret_json:
                            print(f"\n   📋 Campos personalizados:")
                            
                            # Primero intentar obtener nombres desde metadata descifrado
                            if metadata_decrypted and 'custom_fields' in metadata_decrypted:
                                for field_meta in metadata_decrypted['custom_fields']:
                                    field_names[field_meta['id']] = field_meta.get('label', field_meta.get('name', 'Sin nombre'))
                            
                            # Mostrar cada campo con su nombre
                            for field in secret_json['custom_fields']:
                                field_id = field['id']
                                field_name = field_names.get(field_id, f'Campo {field_id[:8]}')
                                field_value = field.get('secret_value', field.get('value', 'N/A'))
                                print(f"      • {field_name}: {field_value}")
                            
                    except json.JSONDecodeError:
                        print(f"   {decrypted_secret}")
                else:
                    # Ya está descifrado
                    try:
                        secret_json = json.loads(secret_data)
                        print(json.dumps(secret_json, indent=2, ensure_ascii=False))
                        
                        if 'password' in secret_json:
                            print(f"\n   🔑 Password: {secret_json['password']}")
                    except:
                        print(f"   {secret_data}")
                        
            except Exception as e:
                print(f"   ⚠️  Error procesando secret: {str(e)}")
                print(f"   Secret raw: {secret.get('data', 'N/A')[:100]}...")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
