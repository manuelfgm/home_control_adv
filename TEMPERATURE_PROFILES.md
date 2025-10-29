# Sistema de Perfiles de Temperatura

## ✨ **Nueva Funcionalidad Implementada**

### **Características Principales**

#### 🌡️ **Perfiles de Temperatura Configurables**
- **Temperatura Mínima**: Protección contra frío extremo (nunca baja de este valor)
- **Temperatura de Confort**: Temperatura objetivo durante el día
- **Temperatura Nocturna**: Temperatura reducida durante la noche
- **Horarios Nocturnos**: Configurables (inicio y fin del modo nocturno)

#### 🏠 **Tipos de Perfiles Predefinidos**
1. **Normal**: Uso diario estándar (16°C min, 20°C confort, 17°C noche)
2. **Vacaciones**: Modo ahorro (12°C min, 15°C confort, 12°C noche)
3. **Económico**: Balance entre confort y ahorro (15°C min, 18°C confort, 16°C noche)
4. **Nocturno**: Solo calefacción nocturna (14°C min, 16°C día, 18°C noche)
5. **Personalizado**: Configuración libre

#### ⚙️ **Lógica de Funcionamiento**

```
Prioridad de Temperaturas:
1. Temperatura Mínima (SIEMPRE respetada)
2. Horario Programado (si existe)
3. Perfil Activo (día/noche según horario)
4. Protección por defecto
```

#### 🔧 **Integración con Sistema Existente**
- **Compatible** con horarios programados existentes
- **Respeta** temperatura mínima incluso con horarios activos
- **Automático** cambio día/noche según perfil
- **Vacaciones** modo rápido con un clic

### **Nuevos Endpoints API**

```bash
# Gestión de Perfiles
GET    /heating/api/profiles/                 # Listar perfiles
POST   /heating/api/profiles/                 # Crear perfil
PUT    /heating/api/profiles/{id}/            # Actualizar perfil
DELETE /heating/api/profiles/{id}/            # Eliminar perfil

# Estado y Control
GET    /heating/api/profiles/active_profile/  # Perfil activo
GET    /heating/api/profiles/current_status/  # Estado actual
POST   /heating/api/profiles/activate_profile/ # Activar perfil
GET    /heating/api/profiles/vacation_mode/   # Modo vacaciones
```

### **Nueva Interfaz Web**

#### 📱 **Dashboard de Perfiles** (`/dashboard/profiles/`)
- **Estado Actual**: Perfil activo, temperatura objetivo, modo día/noche
- **Acciones Rápidas**: Modo vacaciones, modo normal
- **Gestión de Perfiles**: Crear, editar, activar, eliminar
- **Vista en Tiempo Real**: Actualización automática cada 30 segundos

#### 🎨 **Características de la UI**
- **Tarjetas Visuales**: Estado claro de cada perfil
- **Colores Diferenciados**: Activo (verde), Vacaciones (amarillo)
- **Badges de Estado**: Activo, Inactivo, Por Defecto
- **Formulario Modal**: Configuración completa de perfiles
- **Validación Frontend**: Temperaturas coherentes

### **Casos de Uso**

#### 🏡 **Uso Diario Normal**
```
- Perfil "Normal" activo por defecto
- Día: 20°C objetivo
- Noche (23:00-06:00): 17°C objetivo
- Mínimo SIEMPRE: 16°C
```

#### ✈️ **Modo Vacaciones**
```
- Un clic para activar "Vacaciones"
- Temperaturas reducidas para ahorro
- Protección mínima: 12°C
- Fácil regreso al modo normal
```

#### 💰 **Modo Económico**
```
- Balance entre confort y ahorro
- Temperaturas ligeramente reducidas
- Activación automática configurable
```

#### 🛡️ **Protección Anti-Congelación**
```
- Temperatura mínima SIEMPRE respetada
- Independiente de horarios programados
- Protección automática de tuberías
```

### **Integración con Horarios**

#### 🔄 **Compatibilidad Total**
- Los **horarios programados** siguen funcionando igual
- La **temperatura mínima** del perfil actúa como límite inferior
- **Ejemplo**: 
  - Horario programado: 22°C
  - Perfil mínimo: 16°C
  - Resultado: 22°C (horario respetado)
  
  - Horario programado: 14°C  
  - Perfil mínimo: 16°C
  - Resultado: 16°C (mínimo protegido)

#### 🌙 **Sin Horarios Activos**
- Usa temperaturas del **perfil activo**
- Cambia automáticamente **día/noche**
- Respeta **temperatura mínima** siempre

### **Configuración Recomendada**

#### 🏠 **Casa Habitada** (Perfil Normal)
```
Mínima: 16°C     # Protección tuberías
Confort: 20°C    # Temperatura diurna cómoda  
Nocturna: 17°C   # Ahorro nocturno moderado
Horario: 23:00-06:00  # Periodo nocturno
```

#### ✈️ **Casa Vacía** (Perfil Vacaciones)
```
Mínima: 12°C     # Protección básica
Confort: 15°C    # Ahorro máximo
Nocturna: 12°C   # Sin diferencia día/noche
Horario: 22:00-08:00  # Periodo más largo
```

#### 💰 **Ahorro Energético** (Perfil Económico)
```
Mínima: 15°C     # Protección tuberías
Confort: 18°C    # Confort reducido
Nocturna: 16°C   # Ahorro nocturno
Horario: 23:30-06:30  # Optimizado
```

### **Ventajas del Sistema**

✅ **Seguridad**: Protección automática contra frío extremo  
✅ **Flexibilidad**: Múltiples perfiles para diferentes situaciones  
✅ **Compatibilidad**: Funciona con horarios existentes  
✅ **Eficiencia**: Optimización automática día/noche  
✅ **Simplicidad**: Activación con un clic (vacaciones)  
✅ **Personalización**: Perfiles completamente configurables  

### **Archivos Modificados**

```
backend/heating/
├── models.py              # + TemperatureProfile model
├── serializers.py         # + Profile serializers  
├── views.py              # + Profile ViewSet
├── urls.py               # + Profile endpoints
├── admin.py              # + Profile admin
├── heating_logic.py      # ↻ Updated logic
└── migrations/           # + New migrations

backend/dashboard/
├── templates/dashboard/
│   ├── base.html         # ↻ Updated navigation
│   └── profiles.html     # + New profiles page
├── urls.py               # + Profiles URL
└── views.py              # + ProfilesView
```