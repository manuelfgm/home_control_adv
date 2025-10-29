# Documentación de URLs del Sistema de Control de Calefacción

## Estructura de URLs

### 📍 **URLs Principales del Proyecto**
```
/admin/                 → Panel de administración Django
/logout/               → Cerrar sesión
/sensors/              → Aplicación de sensores
/heating/              → Aplicación de calefacción  
/dashboard/            → Dashboard web (SPA)
/                      → Redirige al dashboard
```

### 🌡️ **APIs de Sensores (`/sensors/api/`)**
```
GET    /sensors/api/readings/           → Lista de lecturas
POST   /sensors/api/readings/           → Crear lectura
GET    /sensors/api/readings/{id}/      → Lectura específica
PUT    /sensors/api/readings/{id}/      → Actualizar lectura
DELETE /sensors/api/readings/{id}/      → Eliminar lectura

GET    /sensors/api/status/             → Lista de estados de sensores
POST   /sensors/api/status/             → Crear estado
GET    /sensors/api/status/{id}/        → Estado específico
PUT    /sensors/api/status/{id}/        → Actualizar estado
DELETE /sensors/api/status/{id}/        → Eliminar estado
```

### 🔥 **APIs de Calefacción (`/heating/api/`)**
```
GET    /heating/api/schedules/          → Lista de horarios
POST   /heating/api/schedules/          → Crear horario
GET    /heating/api/schedules/{id}/     → Horario específico
PUT    /heating/api/schedules/{id}/     → Actualizar horario
PATCH  /heating/api/schedules/{id}/     → Actualizar parcialmente
DELETE /heating/api/schedules/{id}/     → Eliminar horario

GET    /heating/api/control/            → Lista de controles
POST   /heating/api/control/            → Crear control
GET    /heating/api/control/{id}/       → Control específico
PUT    /heating/api/control/{id}/       → Actualizar control

GET    /heating/api/logs/               → Lista de logs
GET    /heating/api/logs/{id}/          → Log específico

GET    /heating/api/thresholds/         → Lista de umbrales
POST   /heating/api/thresholds/         → Crear umbral
```

### 📊 **APIs del Dashboard (`/dashboard/api/`)**
```
GET    /dashboard/api/status/           → Estado general del sistema
GET    /dashboard/api/history-stats/    → Estadísticas históricas
GET    /dashboard/api/temperature-chart/ → Datos para gráficos
GET    /dashboard/api/schedules/        → Horarios (solo lectura)
POST   /dashboard/api/manual-control/   → Control manual
```

### 🖥️ **Vistas Web del Dashboard (`/dashboard/`)**
```
GET    /dashboard/                      → Dashboard principal
GET    /dashboard/schedules/            → Página de horarios
GET    /dashboard/history/              → Página de histórico
GET    /dashboard/control/              → Página de control manual
```

## ✅ **URLs Corregidas**

### ❌ **Antes (Incorrectas)**:
```javascript
fetch('/heating/schedules/')           // ❌ No existe
fetch('/heating/schedules/1/')         // ❌ No existe
```

### ✅ **Después (Correctas)**:
```javascript
fetch('/heating/api/schedules/')       // ✅ CRUD completo
fetch('/heating/api/schedules/1/')     // ✅ CRUD completo
fetch('/dashboard/api/schedules/')     // ✅ Solo lectura optimizada
```

## 🎯 **Uso Recomendado**

### **Para Operaciones CRUD (Crear, Leer, Actualizar, Eliminar)**:
- Usar `/heating/api/schedules/` para gestión completa de horarios
- Usar `/sensors/api/readings/` para gestión de lecturas

### **Para Dashboards y Visualización**:
- Usar `/dashboard/api/status/` para estado general
- Usar `/dashboard/api/schedules/` para mostrar horarios (optimizado)
- Usar `/dashboard/api/temperature-chart/` para gráficos

### **Para Control Manual**:
- Usar `/dashboard/api/manual-control/` para controles rápidos
- Usar `/heating/api/control/` para gestión avanzada

## 🔧 **Parámetros Comunes**

### **Filtros de Tiempo**:
```
?hours=24                    → Últimas 24 horas
?days=7                      → Últimos 7 días
?start_date=2025-01-01       → Desde fecha
?end_date=2025-01-31         → Hasta fecha
```

### **Filtros de Sensores**:
```
?sensor_id=room_sensor       → Sensor específico
?sensor_type=temperature     → Tipo de sensor
```

### **Paginación**:
```
?page=2                      → Página específica
?page_size=50                → Elementos por página
?limit=10                    → Límite de resultados
```