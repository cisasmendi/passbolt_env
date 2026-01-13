"""
Excepciones personalizadas para la aplicación Passbolt
"""


class PassboltError(Exception):
    """Excepción base para errores de Passbolt"""
    pass


class AuthenticationError(PassboltError):
    """Error de autenticación"""
    pass


class DecryptionError(PassboltError):
    """Error de descifrado"""
    pass


class ResourceNotFoundError(PassboltError):
    """Recurso no encontrado"""
    pass


class ConfigurationError(PassboltError):
    """Error de configuración"""
    pass