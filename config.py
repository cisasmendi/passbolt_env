"""
Configuración centralizada para la aplicación Passbolt
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class PassboltConfig:
    """Clase para manejar la configuración de Passbolt"""
    
    def __init__(self):
        self.passbolt_url = os.getenv('PASSBOLT_URL')
        self.resource_id = os.getenv('RESOURCE_ID')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.passphrase = os.getenv('PASSPHRASE')
    
    def validate(self):
        """Valida que todas las configuraciones requeridas estén presentes"""
        missing = []
        
        if not self.passbolt_url:
            missing.append('PASSBOLT_URL')
        if not self.private_key:
            missing.append('PRIVATE_KEY')
        if not self.passphrase:
            missing.append('PASSPHRASE')
            
        if missing:
            raise ValueError(f"Variables de entorno faltantes: {', '.join(missing)}")
        
        return True


# Instancia global de configuración
config = PassboltConfig()