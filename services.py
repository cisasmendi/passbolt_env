"""
Servicios para el manejo de recursos de Passbolt
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from exceptions import DecryptionError, ResourceNotFoundError


class ResourceService:
    """Servicio para operaciones con recursos"""
    
    def __init__(self, api):
        self.api = api
        self._resource_types_cache = None
    
    def get_resource_types(self) -> Dict[str, Dict]:
        """Obtiene y cachea los tipos de recursos"""
        if self._resource_types_cache is None:
            try:
                self._resource_types_cache = self.api.get_resource_types()
            except Exception as e:
                print(f"[WARN] No se pudieron cargar tipos de recursos: {e}")
                self._resource_types_cache = {}
        
        return self._resource_types_cache
    
    def get_resource_with_decrypted_content(self, resource_id: str) -> Tuple[Dict, Optional[Dict], Optional[Dict]]:
        """
        Obtiene un recurso con su contenido descifrado
        
        Returns:
            Tuple[resource, decrypted_metadata, decrypted_secret]
        """
        resource = self.api.get_resource(resource_id, include_secret=True, include_permissions=True)
        
        if not resource:
            raise ResourceNotFoundError(f"Recurso {resource_id} no encontrado")
        
        # Descifrar metadata
        decrypted_metadata = None
        if 'metadata' in resource and resource['metadata']:
            try:
                decrypted_metadata = self.api.decrypt_metadata(resource)
                if decrypted_metadata:
                    print(f"[OK] Metadata descifrado")
                else:
                    print(f"[WARN] No se pudo descifrar metadata")
            except Exception as e:
                print(f"[WARN] No se pudo descifrar metadata: {e}")
                # No lanzar error, continuar con metadata nulo
        
        # Descifrar secreto
        decrypted_secret = None
        field_mapping = {}
        
        if 'secrets' in resource and resource['secrets']:
            secret_data = resource['secrets'][0].get('data') if isinstance(resource['secrets'], list) else resource['secrets'].get('data')
            
            if secret_data:
                try:
                    secret_value_str = self.api.decrypt_secret(secret_data)
                    print(f"[OK] Secreto descifrado")
                    # Intentar parsear como JSON
                    try:
                        decrypted_secret = json.loads(secret_value_str)
                        
                        # Si hay metadata descifrada y custom_fields, mapear nombres
                        if decrypted_metadata and 'custom_fields' in decrypted_secret:
                            field_mapping = self.api.extract_field_names_from_metadata(
                                decrypted_metadata, 
                                decrypted_secret['custom_fields']
                            )
                            
                            # Añadir nombres de campo si están disponibles
                            for field in decrypted_secret['custom_fields']:
                                field_id = field.get('id')
                                if field_id in field_mapping:
                                    field['field_name'] = field_mapping[field_id]
                                    
                    except json.JSONDecodeError:
                        # Si no es JSON válido, guardarlo como texto plano
                        decrypted_secret = {"value": secret_value_str}
                except Exception as e:
                    print(f"[WARN] No se pudo descifrar secreto: {e}")
                    # No lanzar error, continuar con secreto nulo
        
        return resource, decrypted_metadata, decrypted_secret
    
    def list_resources_with_decrypted_info(self, search: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Lista recursos con información descifrada para mostrar"""
        url = f"{self.api.base_url}/resources.json"
        params = [
            "contain[secret]=0",
            "contain[favorite]=1",
            "contain[permission]=1"
        ]
        
        if params:
            url += "?" + "&".join(params)
        
        response = self.api.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        all_resources = data['body']
        
        filtered_resources = []
        
        if search:
            search_lower = search.lower()
        
        for resource in all_resources:
            resource_info = self._extract_resource_display_info(resource)
            
            # Aplicar filtro de búsqueda
            if search:
                search_text = f"{resource_info['name']} {resource_info['username']} {resource_info['uri']} {resource_info.get('description', '')}".lower()
                if search_lower not in search_text:
                    continue
            
            filtered_resources.append(resource_info)
            
            if len(filtered_resources) >= limit:
                break
        
        return filtered_resources
    
    def _extract_resource_display_info(self, resource: Dict) -> Dict:
        """Extrae información para mostrar de un recurso (con metadata descifrado si es posible)"""
        resource_id = resource.get('id', '')
        name = 'Sin nombre'
        username = ''
        uri = ''
        description = ''
        
        # Intentar descifrar metadata si existe (v4/v5)
        if 'metadata' in resource and resource['metadata']:
            try:
                decrypted_metadata = self.api.decrypt_metadata(resource)
                if decrypted_metadata:
                    name = decrypted_metadata.get('name', 'Sin nombre')
                    username = decrypted_metadata.get('username', '')
                    description = decrypted_metadata.get('description', '')
                    uris = decrypted_metadata.get('uris', [])
                    if uris and len(uris) > 0:
                        uri = uris[0].get('uri', '') if isinstance(uris[0], dict) else uris[0]
                else:
                    name = "[Metadata no accesible]"
            except Exception:
                name = "[Error descifrado]"
        else:
            # Usar campos directos (v4)
            name = resource.get('name', 'Sin nombre')
            username = resource.get('username', '')
            uri = resource.get('uri', '')
            description = resource.get('description', '')
        
        return {
            'id': resource_id,
            'name': name,
            'username': username,
            'uri': uri,
            'description': description
        }