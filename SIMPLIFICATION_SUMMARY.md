# Simplificación del Sistema de Calefacción

## Resumen de Cambios

Se ha simplificado el sistema de calefacción eliminando los perfiles complejos de temperatura y manteniendo únicamente:

### 1. Horarios de Calefacción (`HeatingSchedule`)
- Configuración de horarios específicos con temperaturas objetivo
- Soporte para múltiples días de la semana
- Validación de conflictos entre horarios

### 2. Configuración Simple (`HeatingSettings`)
- **Temperatura mínima**: Temperatura que se mantiene cuando NO hay horarios activos
- **Histéresis**: Para evitar encendido/apagado frecuente
- Configuración única y centralizada

### 3. Lógica Simplificada
El sistema ahora funciona de manera muy simple:

1. **Si hay un horario activo**: Usa la temperatura del horario
2. **Si NO hay horarios activos**: Usa la temperatura mínima configurada
3. **Protección**: Siempre respeta la temperatura mínima como límite inferior

## Archivos Modificados

### Modelos
- `heating/models.py`: Eliminados `TemperatureProfile` y `TemperatureThreshold`
- `heating/models.py`: Añadido `HeatingSettings` con temperatura mínima e histéresis

### Vistas y APIs
- `heating/views.py`: Eliminadas vistas de perfiles, añadida `HeatingSettingsViewSet`
- `heating/serializers.py`: Eliminados serializers obsoletos, añadido `HeatingSettingsSerializer`
- `heating/urls.py`: Actualizadas rutas, eliminadas URLs de perfiles
- `heating/admin.py`: Actualizado admin para nuevos modelos

### Templates
- `dashboard/templates/dashboard/settings.html`: Nueva página de configuración
- `dashboard/templates/dashboard/base.html`: Actualizada navegación
- Eliminado: `dashboard/templates/dashboard/profiles.html`

### Lógica de Control
- `heating/heating_logic.py`: Simplificada para usar configuración mínima

## Funcionalidad Actual

### API Endpoints Disponibles
```
/heating/api/schedules/          # Gestión de horarios
/heating/api/control/            # Control de calefacción
/heating/api/logs/               # Logs del sistema
/heating/api/settings/           # Nueva configuración
```

### Endpoints Específicos de Configuración
```
GET  /heating/api/settings/current/                    # Obtener configuración actual
POST /heating/api/settings/update_minimum_temperature/ # Actualizar temp. mínima
```

### Páginas Web
```
/dashboard/              # Dashboard principal
/dashboard/schedules/    # Gestión de horarios
/dashboard/control/      # Control manual
/dashboard/settings/     # Nueva página de configuración
/dashboard/history/      # Histórico de datos
```

## Migración de Datos

Se aplicó la migración `0005_heatingsettings_delete_temperatureprofile_and_more.py` que:
- ✅ Creó el modelo `HeatingSettings`
- ✅ Eliminó `TemperatureProfile`
- ✅ Eliminó `TemperatureThreshold`
- ✅ Mantuvo todos los datos de `HeatingSchedule`

## Configuración por Defecto

El sistema crea automáticamente una configuración por defecto:
- **Temperatura mínima**: 16.0°C
- **Histéresis**: 0.5°C

Esta configuración se puede modificar desde:
1. La nueva página web `/dashboard/settings/`
2. El panel de administración de Django
3. La API REST

## Ventajas de la Simplificación

1. **Más fácil de entender**: Solo horarios + temperatura mínima
2. **Menos complejidad**: Eliminadas múltiples configuraciones de perfiles
3. **Más eficiente**: Menos consultas a base de datos
4. **Mantenimiento**: Código más limpio y fácil de mantener
5. **Funcionalidad**: Mantiene toda la funcionalidad esencial

## Prueba del Sistema

Para verificar que todo funciona:

```bash
cd backend
python manage.py check
python manage.py runserver
```

Luego visitar:
- http://localhost:8000/dashboard/settings/ - Nueva configuración
- http://localhost:8000/admin/ - Panel de administración
- http://localhost:8000/heating/api/settings/current/ - API de configuración