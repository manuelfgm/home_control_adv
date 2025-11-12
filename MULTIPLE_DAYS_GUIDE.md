# 🗓️ Sistema de Horarios con Múltiples Días

## 🎯 Nueva Funcionalidad Implementada

Ahora los horarios pueden configurarse para **múltiples días de la semana** en un solo horario, permitiendo configuraciones más eficientes como:

- **Laborables** (Lunes-Viernes)
- **Fines de semana** (Sábado-Domingo) 
- **Días específicos** (ej: Martes, Jueves)
- **Todos los días**

## 📊 Comparación: Antes vs Después

### ❌ Antes (días individuales)
```
- Lunes Mañana: L 07:00-09:00 → 21°C
- Martes Mañana: M 07:00-09:00 → 21°C  
- Miércoles Mañana: X 07:00-09:00 → 21°C
- Jueves Mañana: J 07:00-09:00 → 21°C
- Viernes Mañana: V 07:00-09:00 → 21°C
(5 horarios para el mismo período)
```

### ✅ Ahora (múltiples días)
```
- Mañanas Laborables: L-V 07:00-09:00 → 21°C
(1 horario para todo el período)
```

## 🛠️ Uso del Nuevo Sistema

### Crear Horarios con la API

```bash
# Horario para días laborables
POST /heating/api/schedules/
{
    "name": "Mañanas Laborables",
    "weekdays_list": [0, 1, 2, 3, 4],  # L-V
    "start_time": "07:00",
    "end_time": "09:00",
    "target_temperature": 21.0
}

# Horario para fines de semana
POST /heating/api/schedules/
{
    "name": "Fines de Semana", 
    "weekdays_list": [5, 6],  # S-D
    "start_time": "09:00",
    "end_time": "23:00",
    "target_temperature": 20.0
}

# Días específicos (ej: martes y jueves)
POST /heating/api/schedules/
{
    "name": "Martes y Jueves",
    "weekdays_list": [1, 3],
    "start_time": "15:00", 
    "end_time": "17:00",
    "target_temperature": 19.0
}
```

### Crear Horarios Programáticamente

```python
from heating.models import HeatingSchedule
import datetime

# Método 1: Usar métodos helper
laborables = HeatingSchedule.create_workdays_schedule(
    name="Mañanas de Trabajo",
    start_time=datetime.time(7, 0),
    end_time=datetime.time(9, 0), 
    temperature=21.0
)

fin_semana = HeatingSchedule.create_weekend_schedule(
    name="Fin de Semana Relajado",
    start_time=datetime.time(10, 0),
    end_time=datetime.time(22, 0),
    temperature=20.0
)

# Método 2: Crear manualmente
custom_schedule = HeatingSchedule.objects.create(
    name="Días Específicos",
    weekdays="1,3,5",  # Martes, Jueves, Sábado
    start_time=datetime.time(14, 0),
    end_time=datetime.time(16, 0),
    target_temperature=19.5
)

# Método 3: Usando lista de días
schedule = HeatingSchedule()
schedule.name = "Horario Personalizado"
schedule.set_weekdays_from_list([0, 2, 4, 6])  # L, X, V, D
schedule.start_time = datetime.time(20, 0)
schedule.end_time = datetime.time(22, 0)
schedule.target_temperature = 23.0
schedule.save()
```

## 📅 Formato de Días

### Números de Días de la Semana
```
0 = Lunes
1 = Martes  
2 = Miércoles
3 = Jueves
4 = Viernes
5 = Sábado
6 = Domingo
```

### Formatos Soportados

```python
# En base de datos (campo weekdays)
"0,1,2,3,4"     # Laborables
"5,6"           # Fines de semana  
"0,2,4"         # Lunes, miércoles, viernes
"0,1,2,3,4,5,6" # Todos los días

# En API (weekdays_list)
[0, 1, 2, 3, 4]  # Laborables
[5, 6]           # Fines de semana
[1, 3, 5]        # Martes, jueves, sábado
```

### Visualización Inteligente

El sistema muestra automáticamente nombres amigables:

```python
[0, 1, 2, 3, 4] → "Laborables"
[5, 6]          → "Fines de semana" 
[0, 1, 2, 3, 4, 5, 6] → "Todos los días"
[1]             → "Martes"
[1, 3, 5]       → "Martes, Jueves, Sábado"
```

## 🌐 Endpoints de la API

### Consultar Horarios por Día
```bash
GET /heating/api/schedules/by_day/

# Response
{
    "Lunes": [
        {"name": "Mañanas Laborables", "start_time": "07:00", ...},
        {"name": "Tardes Laborables", "start_time": "18:00", ...}
    ],
    "Martes": [
        {"name": "Mañanas Laborables", "start_time": "07:00", ...},
        {"name": "Tardes Laborables", "start_time": "18:00", ...}
    ],
    ...
    "Sábado": [
        {"name": "Fines de Semana", "start_time": "09:00", ...}
    ],
    ...
}
```

### Estado Actual
```bash
GET /heating/api/control/status/

# Response incluye horario activo con días múltiples
{
    "target_temperature": 21.0,
    "active_schedule": {
        "name": "Mañanas Laborables",
        "weekdays_display": "Laborables", 
        "weekdays": "0,1,2,3,4",
        "start_time": "07:00",
        "end_time": "09:00"
    }
}
```

## 🎯 Ventajas del Nuevo Sistema

✅ **Menos configuración**: 3 horarios vs 12 individuales  
✅ **Mayor flexibilidad**: Días específicos, combinaciones personalizadas  
✅ **Más legible**: "Laborables" vs "Lunes, Martes, Miércoles..."  
✅ **Más eficiente**: Menos registros en base de datos  
✅ **Fácil mantenimiento**: Cambiar un horario afecta todos los días  

## 🔄 Migración Automática

Al actualizar desde el sistema anterior:
- ✅ Los datos existentes se conservan
- ✅ Se convierten automáticamente al nuevo formato
- ✅ No se pierde información
- ✅ Compatible con la API anterior

¡El sistema ahora es mucho más potente y fácil de usar! 🚀