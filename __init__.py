"""
Passbolt CLI - Cliente refactorizado para la API de Passbolt

Módulos:
- config: Configuración centralizada
- exceptions: Excepciones personalizadas  
- passbolt_fetch_resource: Cliente API principal
- services: Servicios de negocio
- formatters: Formateo de datos de salida
"""

__version__ = "2.0.0"
__author__ = "Refactorizado"

# Importaciones principales para facilitar el uso
from .config import config
from .passbolt_fetch_resource import PassboltAPI
from .services import ResourceService
from .formatters import ResourceFormatter
from .exceptions import (
    PassboltError,
    AuthenticationError, 
    DecryptionError,
    ResourceNotFoundError,
    ConfigurationError
)

__all__ = [
    'config',
    'PassboltAPI',
    'ResourceService', 
    'ResourceFormatter',
    'PassboltError',
    'AuthenticationError',
    'DecryptionError', 
    'ResourceNotFoundError',
    'ConfigurationError'
]