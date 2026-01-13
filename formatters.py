"""
Utilidades para formateo de datos de recursos
"""

import json
import os
from typing import Dict, Optional, Tuple


class ResourceFormatter:
    """Formateador para diferentes tipos de salida de recursos"""
    
    def __init__(self, resource_types: Dict):
        self.resource_types = resource_types
    
    def extract_resource_data(self, resource: Dict, decrypted_metadata: Optional[Dict], 
                            decrypted_secret: Optional[Dict]) -> Dict[str, str]:
        """Extrae datos del recurso en un formato consistente"""
        
        # Obtener información del tipo de recurso
        resource_type_info = None
        resource_type_id = resource.get('resource_type_id')
        if resource_type_id and resource_type_id in self.resource_types:
            resource_type_info = self.resource_types[resource_type_id]
        
        # Extraer campos básicos
        name = ''
        username = ''
        password = ''
        uri = ''
        description = ''
        
        # Usar metadata descifrado si está disponible
        if decrypted_metadata:
            name = decrypted_metadata.get('name', '')
            username = decrypted_metadata.get('username', '')
            description = decrypted_metadata.get('description', '')
            uri_list = decrypted_metadata.get('uris', [])
            if uri_list and len(uri_list) > 0:
                uri = uri_list[0].get('uri', '') if isinstance(uri_list[0], dict) else uri_list[0]
        else:
            # Usar campos directos del recurso
            name = resource.get('name', '')
            username = resource.get('username', '')
            uri = resource.get('uri', '')
            description = resource.get('description', '')
        
        # Extraer password y otros campos del secreto
        custom_fields = {}
        
        if decrypted_secret:
            # Manejar estructura v5-default
            if resource_type_info and resource_type_info.get('slug') == 'v5-default':
                password = decrypted_secret.get('password', '')
                # Sobrescribir campos si están en el secreto
                if not username and 'username' in decrypted_secret:
                    username = decrypted_secret.get('username', '')
                if not uri and 'uri' in decrypted_secret:
                    uri = decrypted_secret.get('uri', '')
            else:
                # Estructura con custom_fields o password directo
                if isinstance(decrypted_secret, dict):
                    password = decrypted_secret.get('password', decrypted_secret.get('value', ''))
                    
                    # Procesar custom_fields si existen
                    if 'custom_fields' in decrypted_secret:
                        custom_fields = self._extract_custom_fields(
                            decrypted_secret['custom_fields'], 
                            resource_type_info
                        )
                else:
                    password = str(decrypted_secret)
        
        # Crear diccionario base con solo los campos necesarios
        base_data = {
            'resource_id': resource.get('id', ''),
            'resource_type_slug': resource_type_info.get('slug', '') if resource_type_info else ''
        }
        
        # Agregar campos solo si tienen contenido
        if name:
            base_data['name'] = name
        if username:
            base_data['username'] = username
        if password:
            base_data['password'] = password
        if uri:
            base_data['uri'] = uri
        if description:
            base_data['description'] = description
        
        # Combinar con custom_fields
        return {**base_data, **custom_fields}
    
    def _extract_custom_fields(self, custom_fields_data: list, resource_type_info: Optional[Dict]) -> Dict[str, str]:
        """Extrae custom fields con nombres apropiados según el tipo de recurso"""
        custom_fields = {}
        
        # Determinar nombres de campos basándose en el tipo de recurso
        field_names = self._get_field_names_for_resource_type(resource_type_info)
        
        for i, field in enumerate(custom_fields_data):
            field_name = field_names[i] if i < len(field_names) else f"custom_field_{i+1}"
            custom_fields[field_name] = field.get('secret_value', '')
        
        return custom_fields
    
    def _get_field_names_for_resource_type(self, resource_type_info: Optional[Dict]) -> list:
        """Obtiene nombres de campos apropiados según el tipo de recurso"""
        if not resource_type_info:
            return ['server_ip', 'server_port', 'server_user', 'server_password']
        
        slug = resource_type_info.get('slug', '').lower()
        
        if 'ssh' in slug:
            return ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_password']
        elif 'database' in slug or 'mysql' in slug or 'postgres' in slug:
            return ['db_host', 'db_port', 'db_user', 'db_password']
        elif 'web' in slug or 'website' in slug:
            return ['web_url', 'web_port', 'web_user', 'web_password']
        elif 'api' in slug:
            return ['api_endpoint', 'api_port', 'api_key', 'api_secret']
        else:
            return ['server_host', 'server_port', 'server_user', 'server_password']
    
    def format_as_json(self, resource_data: Dict, output_dir: str = 'out') -> str:
        """Formatea los datos del recurso como JSON"""
        os.makedirs(output_dir, exist_ok=True)
        
        resource_id = resource_data['resource_id']
        output_file = os.path.join(output_dir, f"{resource_id}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resource_data, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def format_as_env(self, resource_data: Dict, output_dir: str = 'out') -> str:
        """Formatea los datos del recurso como archivo .env"""
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, '.env')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Escribir comentarios con información del recurso
            if resource_data.get('resource_type_name'):
                f.write(f"# Resource Type: {resource_data['resource_type_name']} ({resource_data['resource_type_slug']})\n")
            f.write(f"# Resource: {resource_data.get('name', 'N/A')}\n")
            if resource_data.get('description'):
                f.write(f"# {resource_data['description']}\n")
            f.write("\n")
            
            # Variables básicas
            f.write(f"RESOURCE_ID={resource_data['resource_id']}\n")
            if resource_data.get('name'):
                f.write(f"RESOURCE_NAME={resource_data['name']}\n")
            if resource_data.get('resource_type_slug'):
                f.write(f"RESOURCE_TYPE={resource_data['resource_type_slug']}\n")
            if resource_data.get('username'):
                f.write(f"USERNAME={resource_data['username']}\n")
            if resource_data.get('password'):
                f.write(f"PASSWORD={resource_data['password']}\n")
            if resource_data.get('uri'):
                f.write(f"URI={resource_data['uri']}\n")
            
            # Custom fields
            custom_fields = {k: v for k, v in resource_data.items() 
                           if k not in ['resource_id', 'name', 'username', 'password', 'uri', 'description',
                                      'created', 'modified', 'resource_type_id', 'resource_type_name', 'resource_type_slug']}
            
            if custom_fields:
                f.write("\n# Custom Fields\n")
                for key, value in custom_fields.items():
                    env_key = key.upper()
                    f.write(f"{env_key}={value}\n")
        
        return output_file