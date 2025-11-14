// Dashboard de Calefacción - JavaScript
// Declarar variable global
let dashboard;

class HeatingDashboard {
    constructor() {
        this.apiBase = '/heating/api/';
        this.statusInterval = null;
        this.currentScheduleId = null;
        this.currentSettingsId = null;
        this.selectedSettingsId = null;
        this.csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        this.init();
    }
    
    init() {
        this.loadStatus();
        this.loadAllSettings();
        this.loadSchedules();
        this.loadLogs();
        this.setupWeekdaySelector();
        
        // Actualizar estado cada 30 segundos
        this.statusInterval = setInterval(() => {
            this.loadStatus();
            this.loadLogs();
        }, 30000);
    }
    
    // === API HELPERS ===
    async apiCall(endpoint, options = {}) {
        try {
            // Preparar headers con CSRF token
            const headers = {
                'Content-Type': 'application/json',
                ...options.headers
            };
            
            // Agregar CSRF token para métodos que modifican datos
            if (options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase())) {
                headers['X-CSRFToken'] = this.csrfToken;
            }
            
            const response = await fetch(this.apiBase + endpoint, {
                headers: headers,
                credentials: 'same-origin', // Incluir cookies de sesión
                ...options
            });
            
            // Verificar si es una redirección HTML (login page)
            const contentType = response.headers.get('content-type');
            if (!response.ok || (contentType && contentType.includes('text/html'))) {
                if (response.status === 403 || response.status === 401 || contentType?.includes('text/html')) {
                    // Redirigir al login si no está autenticado o si recibimos HTML en lugar de JSON
                    this.showAlert('Sesión expirada. Redirigiendo al login...', 'error');
                    setTimeout(() => {
                        window.location.href = '/admin/login/?next=/heating/dashboard/';
                    }, 2000);
                    return null;
                }
                
                // Para errores HTTP 400 (Bad Request), intentar obtener el mensaje del servidor
                if (response.status === 400 && contentType?.includes('application/json')) {
                    try {
                        const errorData = await response.json();
                        const errorMessage = errorData.error || errorData.message || response.statusText;
                        throw new Error(errorMessage);
                    } catch (parseError) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                }
                
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Si llegamos aquí, la response es válida
            // Para DELETE requests, verificar si hay contenido antes de parsear JSON
            if (response.status === 204 || options.method === 'DELETE') {
                return true; // Éxito sin contenido
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            if (error.name !== 'TypeError') { // No mostrar errores de red si ya se maneja la redirección
                this.showAlert(`Error: ${error.message}`, 'error');
            }
            throw error;
        }
    }
    
    // === STATUS ===
    async loadStatus() {
        try {
            const response = await fetch('/heating/api/status/', {
                credentials: 'same-origin'
            });
            if (!response.ok) return; // Si hay error, salir silenciosamente
            
            const data = await response.json();
            if (!data) return; // Si no hay datos, salir
            
            // Actualizar temperatura actual
            const currentTemp = data.current_temperature;
            document.getElementById('current-temp').textContent = 
                currentTemp ? `${currentTemp}°C` : '--°C';
            
            // Actualizar estado de calefacción
            const isHeating = data.is_heating;
            const statusEl = document.getElementById('heating-status');
            statusEl.textContent = isHeating ? '🔥 Calefacción ENCENDIDA' : '❄️ Calefacción APAGADA';
            statusEl.className = isHeating ? 'heating-on' : 'heating-off';
            
            // Actualizar temperatura objetivo
            document.getElementById('target-temp').textContent = `${data.target_temperature}°C`;
            
            // Actualizar horario activo
            const scheduleEl = document.getElementById('current-schedule');
            if (data.active_schedule) {
                scheduleEl.textContent = data.active_schedule.name;
            } else {
                scheduleEl.textContent = 'Sin horario activo';
            }
            
        } catch (error) {
            console.error('Error loading status:', error);
        }
    }
    
    // === SETTINGS ===
    async loadAllSettings() {
        try {
            console.log('🔄 Cargando configuraciones...'); 
            const data = await this.apiCall('settings/');
            console.log('✅ Settings loaded:', data); // Debug
            const settingsList = document.getElementById('settings-list');
            
            // Las APIs devuelven arrays directos, no objetos con results
            if (!data || !Array.isArray(data) || data.length === 0) {
                console.log('No hay configuraciones o data inválida'); // Debug
                settingsList.innerHTML = '<p>No hay configuraciones. <button class="btn btn-success" onclick="dashboard.createNewSettings()">Crear primera configuración</button></p>';
                return;
            }
            
            console.log('Renderizando', data.length, 'configuraciones'); // Debug
            settingsList.innerHTML = data.map(settings => `
                <div class="schedule-item ${settings.is_active ? 'schedule-active' : ''}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${settings.name}</strong><br>
                            <small>Temperatura por defecto: ${settings.default_temperature}°C • Histéresis: ${settings.hysteresis}°C</small>
                            ${settings.is_active ? '<br><small style="color: #27ae60;">✅ CONFIGURACIÓN ACTIVA</small>' : ''}
                        </div>
                        <div>
                                                        <button class="btn btn-success" onclick="dashboard.editSettings(${settings.id})">✏️</button>
                            <button class="btn btn-success" 
                                    onclick="dashboard.toggleSettings(${settings.id}, ${!settings.is_active})">
                                ${settings.is_active ? '⏸️' : '▶️'}
                            </button>
                            <button class="btn btn-success" onclick="dashboard.deleteSettings(${settings.id})">🗑️</button>
                        </div>
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    async saveSettings() {
        try {
            const name = document.getElementById('settings-name').value;
            const defaultTemp = parseFloat(document.getElementById('settings-default-temp').value);
            const hysteresis = parseFloat(document.getElementById('settings-hysteresis').value);
            
            console.log('Saving settings - currentSettingsId:', this.currentSettingsId);
            
            if (this.currentSettingsId) {
                // Actualizar configuración existente - obtener estado actual primero
                const currentSettings = await this.apiCall(`settings/${this.currentSettingsId}/`);
                if (!currentSettings) return;
                
                const payload = {
                    name: name,
                    default_temperature: defaultTemp,
                    hysteresis: hysteresis,
                    is_active: currentSettings.is_active  // Conservar estado actual
                };
                
                console.log('Updating existing settings:', payload);
                const result = await this.apiCall(`settings/${this.currentSettingsId}/`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                if (!result) return;
                this.showAlert('Configuración actualizada correctamente', 'success');
            } else {
                // Crear nueva configuración (inactiva por defecto)
                const payload = {
                    name: name,
                    default_temperature: defaultTemp,
                    hysteresis: hysteresis,
                    is_active: false
                };
                
                console.log('Creating new settings:', payload);
                const result = await this.apiCall('settings/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                if (!result) return;
                this.showAlert('Configuración creada correctamente', 'success');
            }
            
            this.closeSettingsModal();
            this.loadAllSettings();
            this.loadStatus();
            
        } catch (error) {
            console.error('Error saving settings:', error);
            
            // Mostrar error en la modal en lugar de alert
            const errorArea = document.getElementById('settings-error-area');
            const errorMessage = document.getElementById('settings-error-message');
            
            if (errorArea && errorMessage) {
                errorMessage.textContent = error.message;
                errorArea.style.display = 'block';
                
                // Scroll hacia arriba para que se vea el error
                const modal = document.getElementById('settings-modal');
                if (modal) modal.scrollTop = 0;
            } else {
                // Fallback al alert si no está disponible el área de error
                this.showAlert('Error guardando configuración: ' + error.message, 'error');
            }
        }
    }
    
    async deleteSettings(id) {
        if (!confirm('¿Estás seguro de que quieres eliminar esta configuración?')) return;
        
        try {
            const result = await this.apiCall(`settings/${id}/`, {
                method: 'DELETE'
            });
            
            if (result) {
                this.showAlert('Configuración eliminada correctamente', 'success');
                // Forzar recarga completa
                await this.loadAllSettings();
                await this.loadStatus();
                console.log('Configuración eliminada y datos recargados');
            }
            
        } catch (error) {
            console.error('Error deleting settings:', error);
            this.showAlert('Error eliminando configuración: ' + error.message, 'error');
        }
    }
    
    async toggleSettings(id) {
        try {
            // Obtener configuración actual
            const settings = await this.apiCall(`settings/${id}/`);
            
            if (!settings.is_active) {
                // Si no está activa, activarla (esto desactivará automáticamente las otras)
                await this.apiCall(`settings/${id}/`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        ...settings,
                        is_active: true
                    })
                });
                this.showAlert(`Configuración "${settings.name}" establecida como activa`, 'success');
            } else {
                // No permitir desactivar la configuración activa sin activar otra
                this.showAlert('No puedes desactivar la configuración activa. Activa otra configuración primero.', 'error');
                return;
            }
            
            this.loadAllSettings();
            this.loadStatus();
            
        } catch (error) {
            console.error('Error toggling settings:', error);
        }
    }
    
    editSettings(id) {
        this.apiCall(`settings/${id}/`).then(settings => {
            this.currentSettingsId = id;
            
            // Limpiar área de errores
            const errorArea = document.getElementById('settings-error-area');
            if (errorArea) errorArea.style.display = 'none';
            
            // Llenar formulario
            document.getElementById('settings-modal-title').textContent = 'Editar Configuración';
            document.getElementById('settings-name').value = settings.name;
            document.getElementById('settings-default-temp').value = settings.default_temperature;
            document.getElementById('settings-hysteresis').value = settings.hysteresis;
            
            this.showSettingsModal();
        });
    }
    

    
    // === SCHEDULES ===
    async loadSchedules() {
        try {
            console.log('🔄 Cargando horarios...'); 
            const data = await this.apiCall('schedules/');
            console.log('✅ Schedules loaded:', data); // Debug
            const schedulesList = document.getElementById('schedules-list');
            
            if (!data || !Array.isArray(data) || data.length === 0) {
                schedulesList.innerHTML = '<p>No hay horarios programados. <button class="btn btn-success" onclick="dashboard.createNewSchedule()">Crear primer horario</button></p>';
                return;
            }
            
            schedulesList.innerHTML = data.map(schedule => `
                <div class="schedule-item ${schedule.is_active ? 'schedule-active' : ''} ${schedule.is_active_now ? 'schedule-current' : ''}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${schedule.name}</strong><br>
                            <small>${schedule.weekdays_display} • ${schedule.start_time} - ${schedule.end_time} • ${schedule.target_temperature}°C</small>
                            ${schedule.is_active_now ? '<br><small style="color: #e74c3c;">🔥 ACTIVO AHORA</small>' : ''}
                        </div>
                        <div>
                            <button class="btn btn-success" onclick="dashboard.editSchedule(${schedule.id})">✏️</button>
                            <button class="btn btn-success" 
                                    onclick="dashboard.toggleSchedule(${schedule.id}, ${!schedule.is_active})">
                                ${schedule.is_active ? '⏸️' : '▶️'}
                            </button>
                            <button class="btn btn-success" onclick="dashboard.deleteSchedule(${schedule.id})">🗑️</button>
                        </div>
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error loading schedules:', error);
        }
    }
    
    async saveSchedule() {
        try {
            const name = document.getElementById('schedule-name').value;
            const startTime = document.getElementById('start-time').value;
            const endTime = document.getElementById('end-time').value;
            const targetTemp = parseFloat(document.getElementById('target-temperature').value);
            
            // Obtener días seleccionados
            const selectedDays = Array.from(document.querySelectorAll('.weekday-btn.selected'))
                .map(btn => parseInt(btn.dataset.day));
            
            // Obtener estado de activación
            const isActive = document.getElementById('schedule-is-active').checked;
            
            const payload = {
                name: name,
                start_time: startTime,
                end_time: endTime,
                target_temperature: targetTemp,
                weekdays_list: selectedDays,
                is_active: isActive
            };
            
            console.log('Saving schedule:', payload);
            console.log('CSRF Token:', this.csrfToken);
            
            if (this.currentScheduleId) {
                // Actualizar horario existente
                const result = await this.apiCall(`schedules/${this.currentScheduleId}/`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                if (!result) return; // Si hay redirección, salir
                this.showAlert('Horario actualizado correctamente', 'success');
            } else {
                // Crear nuevo horario
                console.log('Creating new schedule...');
                const result = await this.apiCall('schedules/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                if (!result) return; // Si hay redirección, salir
                console.log('Schedule created:', result);
                this.showAlert('Horario creado correctamente', 'success');
            }
            
            this.closeScheduleModal();
            this.loadSchedules();
            this.loadStatus(); // Recargar estado del sistema
            
        } catch (error) {
            console.error('Error saving schedule:', error);
            
            // Mostrar error en la modal en lugar de alert
            const errorArea = document.getElementById('schedule-error-area');
            const errorMessage = document.getElementById('schedule-error-message');
            
            if (errorArea && errorMessage) {
                errorMessage.textContent = error.message;
                errorArea.style.display = 'block';
                
                // Scroll hacia arriba para que se vea el error
                const modal = document.getElementById('schedule-modal');
                if (modal) modal.scrollTop = 0;
            } else {
                // Fallback al alert si no está disponible el área de error
                this.showAlert('Error guardando horario: ' + error.message, 'error');
            }
        }
    }
    
    async deleteSchedule(id) {
        if (!confirm('¿Estás seguro de que quieres eliminar este horario?')) return;
        
        try {
            const result = await this.apiCall(`schedules/${id}/`, {
                method: 'DELETE'
            });
            
            if (result) {
                this.showAlert('Horario eliminado correctamente', 'success');
                // Forzar recarga completa
                await this.loadSchedules();
                await this.loadStatus();
                console.log('Horario eliminado y datos recargados');
            }
            
        } catch (error) {
            console.error('Error deleting schedule:', error);
            this.showAlert('Error eliminando horario: ' + error.message, 'error');
        }
    }
    
    async toggleSchedule(id) {
        try {
            // Obtener horario actual
            const schedule = await this.apiCall(`schedules/${id}/`);
            
            // Cambiar estado
            await this.apiCall(`schedules/${id}/`, {
                method: 'PUT',
                body: JSON.stringify({
                    ...schedule,
                    is_active: !schedule.is_active
                })
            });
            
            const status = schedule.is_active ? 'desactivado' : 'activado';
            this.showAlert(`Horario ${status} correctamente`, 'success');
            this.loadSchedules();
            this.loadStatus(); // Recargar estado porque cambió un horario
            
        } catch (error) {
            console.error('Error toggling schedule:', error);
        }
    }
    
    editSchedule(id) {
        this.apiCall(`schedules/${id}/`).then(schedule => {
            this.currentScheduleId = id;
            
            console.log('Editando horario:', schedule); // Debug
            
            // Llenar formulario
            document.getElementById('schedule-modal-title').textContent = 'Editar Horario';
            document.getElementById('schedule-name').value = schedule.name;
            document.getElementById('start-time').value = schedule.start_time;
            document.getElementById('end-time').value = schedule.end_time;
            document.getElementById('target-temperature').value = schedule.target_temperature;
            
            // Limpiar selección de días
            document.querySelectorAll('.weekday-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Seleccionar días del horario
            if (schedule.weekdays_list && Array.isArray(schedule.weekdays_list)) {
                console.log('Días a seleccionar:', schedule.weekdays_list); // Debug
                schedule.weekdays_list.forEach(day => {
                    const btn = document.querySelector(`.weekday-btn[data-day="${day}"]`);
                    if (btn) {
                        btn.classList.add('selected');
                        console.log(`Día ${day} seleccionado`); // Debug
                    } else {
                        console.log(`Botón para día ${day} no encontrado`); // Debug
                    }
                });
            } else {
                console.log('No hay días configurados o formato incorrecto:', schedule.weekdays_list); // Debug
            }
            
            // Configurar el checkbox de activación
            document.getElementById('schedule-is-active').checked = schedule.is_active;
            
            this.showScheduleModal();
        }).catch(error => {
            console.error('Error cargando horario para editar:', error);
            this.showAlert('Error cargando horario: ' + error.message, 'error');
        });
    }
    
    // === LOGS ===
    async loadLogs() {
        try {
            console.log('Cargando logs...'); // Debug
            const data = await this.apiCall('logs/?ordering=-timestamp');
            console.log('Logs response:', data); // Debug
            const logsList = document.getElementById('recent-logs');
            
            // Los logs también devuelven array directo, no formato paginado
            if (!data || !Array.isArray(data) || data.length === 0) {
                console.log('No hay logs o data inválida'); // Debug
                logsList.innerHTML = '<p>No hay actividad reciente</p>';
                return;
            }
            
            console.log('Renderizando', data.length, 'logs'); // Debug
            logsList.innerHTML = data.slice(0, 10).map(log => {
                const date = new Date(log.timestamp).toLocaleString('es-ES');
                const status = log.is_heating ? '🔥 ON' : '❄️ OFF';
                const temp = log.current_temperature ? `${log.current_temperature}°C` : '--';
                const target = log.target_temperature ? `→ ${log.target_temperature}°C` : '';
                
                return `
                    <div class="log-item">
                        <div>${date}</div>
                        <div>${status} ${temp} ${target}</div>
                        <div><small>${log.action_reason}</small></div>
                    </div>
                `;
            }).join('');
            
        } catch (error) {
            console.error('Error loading logs:', error);
        }
    }
    
    // === UI HELPERS ===
    
    // === HORARIOS RÁPIDOS ===

    
    // === UI HELPERS ===
    showScheduleModal() {
        // Limpiar área de errores
        const errorArea = document.getElementById('schedule-error-area');
        if (errorArea) errorArea.style.display = 'none';
        
        // Solo resetear ID si no estamos editando
        if (!this.currentScheduleId) {
            document.getElementById('schedule-modal-title').textContent = 'Nuevo Horario';
            document.getElementById('schedule-form').reset();
            document.querySelectorAll('.weekday-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
        }
        document.getElementById('schedule-modal').style.display = 'block';
    }
    
    createNewSchedule() {
        this.currentScheduleId = null;
        document.getElementById('schedule-modal-title').textContent = 'Nuevo Horario';
        document.getElementById('schedule-form').reset();
        document.querySelectorAll('.weekday-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        // Configurar checkbox de activación por defecto
        document.getElementById('schedule-is-active').checked = true;
        document.getElementById('schedule-modal').style.display = 'block';
    }
    
    closeScheduleModal() {
        document.getElementById('schedule-modal').style.display = 'none';
        document.getElementById('schedule-form').reset();
        document.querySelectorAll('.weekday-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        // Limpiar también el área de errores
        const errorArea = document.getElementById('schedule-error-area');
        if (errorArea) {
            errorArea.style.display = 'none';
        }
        this.currentScheduleId = null;
    }
    
    showSettingsModal() {
        // Solo resetear ID si no estamos editando
        if (!this.currentSettingsId) {
            document.getElementById('settings-modal-title').textContent = 'Nueva Configuración';
            document.getElementById('settings-form').reset();
        }
        document.getElementById('settings-modal').style.display = 'block';
    }
    
    createNewSettings() {
        this.currentSettingsId = null;
        
        // Limpiar área de errores
        const errorArea = document.getElementById('settings-error-area');
        if (errorArea) errorArea.style.display = 'none';
        
        document.getElementById('settings-modal-title').textContent = 'Nueva Configuración';
        document.getElementById('settings-form').reset();
        document.getElementById('settings-modal').style.display = 'block';
    }
    
    closeSettingsModal() {
        document.getElementById('settings-modal').style.display = 'none';
        document.getElementById('settings-form').reset();
        this.currentSettingsId = null;
    }
    
    hideSettingsModal() {
        this.closeSettingsModal();
    }
    
    setupWeekdaySelector() {
        document.querySelectorAll('.weekday-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('selected');
            });
        });
    }
    
    showAlert(message, type = 'success') {
        const alertsContainer = document.getElementById('alerts');
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        
        alertsContainer.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }
}

// Global functions for onclick handlers
function showScheduleModal() {
    dashboard.showScheduleModal();
}

function saveSchedule() {
    dashboard.saveSchedule();
}

function closeScheduleModal() {
    dashboard.closeScheduleModal();
}

function showSettingsModal() {
    dashboard.showSettingsModal();
}

function saveSettings() {
    dashboard.saveSettings();
}

function closeSettingsModal() {
    dashboard.closeSettingsModal();
}



function createNewSettings() {
    dashboard.createNewSettings();
}

function createNewSchedule() {
    dashboard.createNewSchedule();
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new HeatingDashboard();
});

// Close modals when clicking outside
window.onclick = function(event) {
    const scheduleModal = document.getElementById('schedule-modal');
    const settingsModal = document.getElementById('settings-modal');
    if (event.target === scheduleModal) {
        closeScheduleModal();
    }
    if (event.target === settingsModal) {
        closeSettingsModal();
    }
}