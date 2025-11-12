# 🏠 Sistema de Calefacción Inteligente

## 📋 Descripción General

Este sistema permite configurar:

1. **Temperatura por defecto** - Temperatura mínima cuando no hay horarios activos
2. **Horarios programados** - Temperaturas específicas por días de la semana y horas
3. **Control automático** - El sistema decide automáticamente la temperatura objetivo

## 🔧 Modelos del Sistema

### HeatingSettings (Configuración)
- `default_temperature`: Temperatura por defecto (°C)
- `hysteresis`: Tolerancia para evitar ciclos on/off
- `is_active`: Si el sistema está activo

### HeatingSchedule (Horarios)
- `day_of_week`: Día de la semana (0=Lunes, 6=Domingo)  
- `start_time` / `end_time`: Horario de inicio y fin
- `target_temperature`: Temperatura objetivo durante ese horario
- `is_active`: Si el horario está activo

### HeatingLog (Historial)
- Registro automático de todos los cambios del sistema
- Incluye datos del actuador (WiFi, memoria, etc.)

## 🌐 Endpoints de la API

### Configuración
```bash
# Obtener configuración actual
GET /heating/api/settings/current/

# Listar todas las configuraciones  
GET /heating/api/settings/

# Crear nueva configuración
POST /heating/api/settings/
{
    "name": "Casa Invierno",
    "default_temperature": 19.0,
    "hysteresis": 0.5
}

# Activar configuración específica
POST /heating/api/settings/{id}/activate/
```

### Horarios
```bash
# Obtener horario activo actual
GET /heating/api/schedules/current_active/

# Horarios agrupados por día
GET /heating/api/schedules/by_day/

# Crear nuevo horario
POST /heating/api/schedules/
{
    "name": "Lunes Mañana",
    "day_of_week": 0,
    "start_time": "07:00",
    "end_time": "09:00", 
    "target_temperature": 21.0,
    "settings": 1
}
```

### Control del Sistema
```bash
# Estado actual completo
GET /heating/api/control/status/

# Temperatura objetivo actual
GET /heating/api/control/target_temperature/

# Control manual temporal
POST /heating/api/control/manual_override/
{
    "temperature": 25.0,
    "duration_minutes": 30
}
```

### Logs y Estadísticas
```bash
# Último log
GET /heating/api/logs/latest/

# Estadísticas del día
GET /heating/api/logs/stats/

# Logs por rango de fechas
GET /heating/api/logs/?date_from=2025-11-01&date_to=2025-11-12
```

## 📊 Ejemplo de Uso

### 1. Configurar Sistema
```python
# Crear configuración básica
settings = {
    "name": "Configuración Casa",
    "default_temperature": 18.0,  # Mínimo 18°C siempre
    "hysteresis": 0.5,
    "is_active": True
}

# POST /heating/api/settings/
```

### 2. Crear Horarios
```python
# Horario matutino lunes-viernes
morning_schedule = {
    "name": "Mañanas Laborables", 
    "day_of_week": 0,  # Lunes
    "start_time": "07:00",
    "end_time": "09:00",
    "target_temperature": 21.0
}

# Repetir para martes (1), miércoles (2), jueves (3), viernes (4)
```

### 3. Verificar Estado
```python
# El sistema automáticamente:
# - A las 07:00-09:00 (L-V): 21°C
# - A las 18:00-22:00 (L-V): 22°C  
# - Sábado-Domingo 09:00-23:00: 20°C
# - Resto del tiempo: 18°C (default_temperature)
```

## 🔄 Lógica del Sistema

### Prioridad de Temperaturas
1. **Horario activo** - Si hay un horario programado activo
2. **Temperatura por defecto** - Si no hay horarios activos
3. **Control manual** - Sobrescribe temporalmente

### Integración con mqtt_bridge
- Los actuadores envían su estado a `/actuator/api/status/`
- Automáticamente se crean logs en `HeatingLog`
- El sistema puede consultar `target_temperature` para decidir encender/apagar

### Ejemplo de Flujo Completo
```
1. ESP Sensor mide 17.5°C
2. Sistema consulta temperatura objetivo: 21.0°C (horario activo)
3. Temperatura actual < objetivo → Enviar comando encender
4. ESP Actuator recibe comando y enciende calefacción
5. ESP Actuator confirma estado → Se crea log automáticamente
6. Proceso se repite hasta alcanzar temperatura objetivo
```

## 🎛️ Panel de Administración

Accede a `/admin/` para configurar:
- ✅ Configuraciones de calefacción
- ✅ Horarios por días de la semana  
- ✅ Ver logs de actividad
- ✅ Estadísticas del sistema

## 🧪 Datos de Prueba

El sistema viene con horarios preconfigurados:
- **L-V 07:00-09:00**: 21°C (mañanas)
- **L-V 18:00-22:00**: 22°C (tardes) 
- **S-D 09:00-23:00**: 20°C (fin de semana)
- **Resto del tiempo**: 18°C (por defecto)

¡El sistema está listo para usar! 🎉