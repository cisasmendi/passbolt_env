# Passbolt CLI - Código Refactorizado

## Refactorización Realizada

### Mejoras Implementadas

1. **Separación de Responsabilidades**:
   - `config.py`: Manejo centralizado de configuración
   - `exceptions.py`: Excepciones personalizadas
   - `services.py`: Lógica de negocio para recursos
   - `formatters.py`: Formateo de datos de salida
   - `passbolt_fetch_resource.py`: Cliente API principal
   - `passbolt_cli.py`: Interfaz de línea de comandos

2. **Eliminación de Código Duplicado**:
   - Funciones comunes movidas a servicios reutilizables
   - Lógica de descifrado centralizada
   - Formateo de salida unificado

3. **Mejor Manejo de Errores**:
   - Excepciones específicas para diferentes tipos de errores
   - Validación de configuración mejorada
   - Mensajes de error más informativos

4. **Código Más Limpio**:
   - Métodos más pequeños y enfocados
   - Mejor organización de la lógica
   - Documentación mejorada

### Estructura de Archivos

```
├── config.py              # Configuración centralizada
├── exceptions.py          # Excepciones personalizadas
├── services.py            # Servicios de negocio
├── formatters.py          # Formateo de salida
├── passbolt_fetch_resource.py  # Cliente API principal
├── passbolt_cli.py        # CLI refactorizado
├── requirements.txt       # Dependencias
└── README.md             # Documentación
```

### Beneficios de la Refactorización

1. **Mantenibilidad**: Código más fácil de mantener y extender
2. **Testabilidad**: Componentes independientes más fáciles de testear
3. **Reutilización**: Servicios reutilizables en diferentes contextos
4. **Legibilidad**: Código más claro y bien organizado
5. **Escalabilidad**: Estructura preparada para futuras expansiones

### Compatibilidad

El CLI mantiene la misma interfaz de usuario, por lo que todos los comandos existentes funcionan igual:

```bash
# Listar recursos
python passbolt_cli.py --list

# Buscar recursos
python passbolt_cli.py --list --search "database"

# Descargar recurso
python passbolt_cli.py --download RESOURCE_ID --json
```

### Uso de los Nuevos Módulos

```python
from config import config
from passbolt_fetch_resource import PassboltAPI
from services import ResourceService
from formatters import ResourceFormatter

# Crear instancia de API
api = PassboltAPI()

# Usar servicios
resource_service = ResourceService(api)
formatter = ResourceFormatter(resource_service.get_resource_types())
```