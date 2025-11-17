from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
import json
import calendar

from sensors.models import SensorReading
from .models import HeatingLog


@login_required
def charts_dashboard_view(request):
    """Vista del dashboard de gráficas"""
    html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="CSRF_TOKEN_PLACEHOLDER">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico">
    <title>📈 Dashboard de Gráficas - Calefacción</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
            color: #333;
        }

        .header {
            background: #6c757d;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }

        .nav-links {
            display: flex;
            gap: 1rem;
        }

        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            background: rgba(255,255,255,0.1);
            transition: background 0.2s;
        }

        .nav-links a:hover {
            background: rgba(255,255,255,0.2);
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .status-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            text-align: center;
        }

        .status-card h3 {
            margin-top: 0;
            color: #6c757d;
            font-size: 1.2rem;
        }

        .temperature {
            font-size: 2em;
            margin: 10px 0;
            font-weight: bold;
        }

        .heating-on {
            color: #e74c3c;
        }

        .heating-off {
            color: #95a5a6;
        }

        .status-info {
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
            text-align: center;
        }

        .status-info > div {
            flex: 1;
        }

        .controls {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            align-items: center;
        }

        .time-selector {
            display: flex;
            gap: 0.5rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #495057;
            color: white;
        }

        .btn-primary:hover {
            background: #343a40;
        }

        .btn-active {
            background: #495057 !important;
            color: white !important;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }

        @media (min-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr 1fr;
            }
        }

        .chart-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .chart-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #495057;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: #6c757d;
        }

        .refresh-btn {
            background: #495057;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }

        .refresh-btn:hover {
            background: #343a40;
        }

        @media (max-width: 768px) {
            .header {
                padding: 1rem;
                flex-direction: column;
                gap: 1rem;
            }

            .controls {
                justify-content: center;
            }

            .container {
                padding: 0 0.5rem;
            }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>
</head>
<body>
    <header class="header">
        <div>
            <h1>📊 Dashboard de Gráficas</h1>
        </div>
        <nav class="nav-links">
            <a href="/heating/dashboard/">🏠 Panel Principal</a>
            <a href="/admin/logout/" onclick="event.preventDefault(); document.getElementById('logout-form').submit();">🔚 Salir</a>
        </nav>
    </header>

    <form id="logout-form" method="post" action="/admin/logout/" style="display: none;">
        <input type="hidden" name="csrfmiddlewaretoken" value="CSRF_TOKEN_PLACEHOLDER">
    </form>

    <div class="container">
        <!-- Estado Actual -->
        <div class="status-card">
            <h3>Estado Actual</h3>
            <div class="temperature" id="current-temp-main">--°C</div>
            <div id="heating-status-main">Sistema apagado</div>
            <div class="status-info">
                <div>Objetivo: <span id="target-temp-main">--°C</span></div>
                <div>Humedad: <span id="current-humidity-main">--%</span></div>
            </div>
        </div>

        <div class="controls">
            <div class="time-selector">
                <button class="btn btn-primary btn-active" data-period="24h">Últimas 24h</button>
                <button class="btn btn-primary" data-period="7d">Última semana</button>
                <button class="btn btn-primary" data-period="30d">Último mes</button>
            </div>
            <button class="refresh-btn" onclick="charts.refreshData()">🔄 Actualizar</button>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Temperatura y Humedad</div>
                <div class="chart-container">
                    <canvas id="tempHumidityChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <div class="chart-title">Uso Mensual de Calefacción</div>
                <div class="chart-container">
                    <canvas id="monthlyUsageChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        class ChartsManager {
            constructor() {
                this.currentPeriod = '24h';
                this.tempHumidityChart = null;
                this.monthlyUsageChart = null;
                this.csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
                
                this.init();
            }

            init() {
                this.setupEventListeners();
                this.initCharts();
                this.loadData();
                
                // Actualizar cada 30 segundos
                setInterval(() => this.loadData(), 30000);
            }

            setupEventListeners() {
                document.querySelectorAll('[data-period]').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        // Actualizar botones activos
                        document.querySelectorAll('[data-period]').forEach(b => b.classList.remove('btn-active'));
                        e.target.classList.add('btn-active');
                        
                        this.currentPeriod = e.target.dataset.period;
                        this.loadData();
                    });
                });
            }

            initCharts() {
                // Gráfico combinado de temperatura, humedad y calefacción
                const tempCtx = document.getElementById('tempHumidityChart').getContext('2d');
                this.tempHumidityChart = new Chart(tempCtx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [
                            {
                                label: 'Temperatura (°C)',
                                data: [],
                                borderColor: '#e74c3c',
                                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                tension: 0.4,
                                yAxisID: 'y',
                                order: 1,
                                pointRadius: 0,
                                pointHoverRadius: 4
                            },
                            {
                                label: 'Humedad (%)',
                                data: [],
                                borderColor: '#3498db',
                                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                tension: 0.4,
                                yAxisID: 'y1',
                                order: 1,
                                pointRadius: 0,
                                pointHoverRadius: 4
                            },
                            {
                                label: 'Calefacción Activa',
                                data: [],
                                type: 'bar',
                                backgroundColor: 'rgba(231, 76, 60, 0.15)',
                                borderColor: 'rgba(231, 76, 60, 0.3)',
                                borderWidth: 0,
                                yAxisID: 'y2',
                                order: 0,
                                barPercentage: 1.0,
                                categoryPercentage: 1.0
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'Temperatura (°C)'
                                },
                                // Rango inicial 17-22°C (ventana de 5°C)
                                min: 17,
                                max: 22
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'Humedad (%)'
                                },
                                // Rango inicial 40-60% (ventana de 10%)
                                min: 50,
                                max: 60,
                                grid: {
                                    drawOnChartArea: false,
                                }
                            },
                            y2: {
                                type: 'linear',
                                display: false,
                                min: 0,
                                max: 30,
                                grid: {
                                    drawOnChartArea: false,
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'top'
                            }
                        }
                    }
                });

                // Gráfico de uso mensual de calefacción
                const monthlyCtx = document.getElementById('monthlyUsageChart').getContext('2d');
                this.monthlyUsageChart = new Chart(monthlyCtx, {
                    type: 'bar',
                    data: {
                        labels: [],
                        datasets: [
                            {
                                label: 'Horas de Uso',
                                data: [],
                                backgroundColor: [
                                    'rgba(231, 76, 60, 0.8)',
                                    'rgba(52, 152, 219, 0.8)',
                                    'rgba(46, 204, 113, 0.8)',
                                    'rgba(241, 196, 15, 0.8)',
                                    'rgba(155, 89, 182, 0.8)',
                                    'rgba(230, 126, 34, 0.8)',
                                    'rgba(26, 188, 156, 0.8)',
                                    'rgba(231, 76, 60, 0.6)',
                                    'rgba(52, 152, 219, 0.6)',
                                    'rgba(46, 204, 113, 0.6)',
                                    'rgba(241, 196, 15, 0.6)',
                                    'rgba(155, 89, 182, 0.6)'
                                ],
                                borderColor: [
                                    'rgba(231, 76, 60, 1)',
                                    'rgba(52, 152, 219, 1)',
                                    'rgba(46, 204, 113, 1)',
                                    'rgba(241, 196, 15, 1)',
                                    'rgba(155, 89, 182, 1)',
                                    'rgba(230, 126, 34, 1)',
                                    'rgba(26, 188, 156, 1)',
                                    'rgba(231, 76, 60, 1)',
                                    'rgba(52, 152, 219, 1)',
                                    'rgba(46, 204, 113, 1)',
                                    'rgba(241, 196, 15, 1)',
                                    'rgba(155, 89, 182, 1)'
                                ],
                                borderWidth: 2
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Horas de Uso'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Mes'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            }

            async loadData() {
                try {
                    const response = await fetch(`/heating/charts/api/data/?period=${this.currentPeriod}`, {
                        credentials: 'same-origin',
                        headers: {
                            'X-CSRFToken': this.csrfToken
                        }
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }

                    const data = await response.json();
                    this.updateCharts(data);
                    this.updateStats(data.current_stats);

                } catch (error) {
                    console.error('Error cargando datos:', error);
                }
            }

            updateCharts(data) {
                // Actualizar datos del gráfico
                this.tempHumidityChart.data.labels = data.sensor_data.labels;
                this.tempHumidityChart.data.datasets[0].data = data.sensor_data.temperature;
                this.tempHumidityChart.data.datasets[1].data = data.sensor_data.humidity;
                this.tempHumidityChart.data.datasets[2].data = data.sensor_data.heating_background;
                
                // Calcular y aplicar rangos dinámicos
                this.updateDynamicScales(data.sensor_data);
                
                this.tempHumidityChart.update('none');

                // Actualizar gráfico de uso mensual
                this.monthlyUsageChart.data.labels = data.monthly_usage.labels;
                this.monthlyUsageChart.data.datasets[0].data = data.monthly_usage.hours;
                this.monthlyUsageChart.update('none');
            }

            updateDynamicScales(sensorData) {
                // Calcular rango dinámico para temperatura (ventana de 10°C)
                const temperatures = sensorData.temperature.filter(t => t !== null && t !== undefined);
                let tempRange = this.calculateDynamicRange(temperatures, 10, 15, 25);
                
                // Calcular rango dinámico para humedad (ventana de 20%)
                const humidities = sensorData.humidity.filter(h => h !== null && h !== undefined);
                let humidityRange = this.calculateDynamicRange(humidities, 20, 40, 60);
                
                // Actualizar escalas del gráfico
                this.tempHumidityChart.options.scales.y.min = tempRange.min;
                this.tempHumidityChart.options.scales.y.max = tempRange.max;
                this.tempHumidityChart.options.scales.y1.min = humidityRange.min;
                this.tempHumidityChart.options.scales.y1.max = humidityRange.max;
            }

            calculateDynamicRange(values, windowSize, defaultMin, defaultMax) {
                if (!values || values.length === 0) {
                    return { min: defaultMin, max: defaultMax };
                }

                const minValue = Math.min(...values);
                const maxValue = Math.max(...values);
                const dataRange = maxValue - minValue;

                // Si el rango de datos cabe en la ventana predeterminada, usarla
                if (minValue >= defaultMin && maxValue <= defaultMax) {
                    return { min: defaultMin, max: defaultMax };
                }

                // Si el rango de datos es menor que el tamaño de ventana, centrar la ventana
                if (dataRange <= windowSize) {
                    const center = (minValue + maxValue) / 2;
                    const halfWindow = windowSize / 2;
                    return {
                        min: Math.max(0, center - halfWindow), // No bajar de 0 para humedad
                        max: center + halfWindow
                    };
                }

                // Si el rango de datos es mayor que la ventana, usar min/max reales con margen
                const margin = windowSize * 0.1; // 10% de margen
                return {
                    min: Math.max(0, minValue - margin),
                    max: maxValue + margin
                };
            }

            updateStats(stats) {
                // Actualizar solo el bloque de estado principal (las cards redundantes fueron eliminadas)
                document.getElementById('current-temp-main').textContent = 
                    stats.temperature ? `${stats.temperature}°C` : '--°C';
                document.getElementById('current-humidity-main').textContent = 
                    stats.humidity ? `${stats.humidity}%` : '--%';
                document.getElementById('target-temp-main').textContent = 
                    stats.target_temperature ? `${stats.target_temperature}°C` : '--°C';
                
                const statusMainElement = document.getElementById('heating-status-main');
                statusMainElement.textContent = stats.is_heating ? 'Calefacción encendida' : 'Sistema apagado';
                
                // Aplicar clase CSS para el color de la temperatura principal
                const tempMainElement = document.getElementById('current-temp-main');
                tempMainElement.className = stats.is_heating ? 'temperature heating-on' : 'temperature heating-off';
            }

            refreshData() {
                this.loadData();
            }
        }

        // Inicializar cuando se carga la página
        let charts;
        document.addEventListener('DOMContentLoaded', () => {
            charts = new ChartsManager();
        });
    </script>
</body>
</html>
    """
    
    # Reemplazar placeholders
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    html_content = html_content.replace('CSRF_TOKEN_PLACEHOLDER', csrf_token)
    
    from django.http import HttpResponse
    return HttpResponse(html_content)


@login_required
def charts_data_api(request):
    """API endpoint para obtener datos de gráficas"""
    try:
        period = request.GET.get('period', '24h')
        
        # Calcular rango de fechas
        now = timezone.now()
        if period == '24h':
            start_time = now - timedelta(hours=24)
        elif period == '7d':
            start_time = now - timedelta(days=7)
        elif period == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)
        
        # Obtener datos de sensores
        sensor_readings = SensorReading.objects.filter(
            created_at__gte=start_time,
            temperature__isnull=False
        ).order_by('created_at')
        
        # Obtener datos de calefacción
        heating_logs = HeatingLog.objects.filter(
            timestamp__gte=start_time
        ).order_by('timestamp')
        
        # Procesar datos de sensores
        sensor_data = {
            'labels': [],
            'temperature': [],
            'humidity': [],
            'heating_background': []
        }
        
        # Debug: añadir información sobre los datos encontrados
        sensor_count = sensor_readings.count()
        
        # Crear un diccionario de estado de calefacción por tiempo
        heating_status_by_time = {}
        for log in heating_logs:
            heating_status_by_time[log.timestamp] = log.is_heating
        
        for reading in sensor_readings:
            # Formato de fecha según el período
            if period == '24h':
                label = reading.created_at.strftime('%H:%M')
            elif period == '7d':
                label = reading.created_at.strftime('%d/%m %H:%M')
            else:  # 30d
                label = reading.created_at.strftime('%d/%m')
                
            sensor_data['labels'].append(label)
            sensor_data['temperature'].append(reading.temperature)
            sensor_data['humidity'].append(reading.humidity or 0)
            
            # Encontrar el estado de calefacción más cercano en tiempo
            closest_heating = None
            min_diff = float('inf')
            for log_time, is_heating in heating_status_by_time.items():
                diff = abs((reading.created_at - log_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_heating = is_heating
            
            # Agregar valor para fondo de calefacción (30 si está encendida, 0 si no)
            sensor_data['heating_background'].append(30 if closest_heating else 0)
        
        # Si no hay datos de sensores, crear datos de ejemplo
        if sensor_count == 0:
            # Generar algunas muestras de ejemplo
            for i in range(10):
                time_offset = timedelta(hours=i * (24 if period == '24h' else 24*7 if period == '7d' else 24*30) / 10)
                sample_time = start_time + time_offset
                sensor_data['labels'].append(sample_time.strftime('%H:%M' if period == '24h' else '%d/%m'))
                sensor_data['temperature'].append(20 + i * 0.5)
                sensor_data['humidity'].append(50 + i * 2)
                sensor_data['heating_background'].append(30 if i % 3 == 0 else 0)  # Ejemplo
        
        # Calcular uso mensual de calefacción (últimos 12 meses)
        # Simplificado para evitar problemas de compatibilidad con bases de datos
        
        monthly_data = {
            'labels': [],
            'hours': []
        }
        
        # Generar datos reales para los últimos 12 meses
        current_date = now.replace(day=1)  # Primer día del mes actual
        
        for i in range(12):
            month_date = current_date - timedelta(days=30*i)
            month_name = calendar.month_name[month_date.month][:3]  # Nov, Oct, etc.
            year = month_date.year
            
            # Generar etiqueta del mes
            monthly_data['labels'].insert(0, f"{month_name} {year}")
            
            # Calcular uso real del mes basado en períodos de calefacción activa
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1, day=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1, day=1)
            
            # Obtener todos los logs del mes ordenados por timestamp
            month_logs = HeatingLog.objects.filter(
                timestamp__gte=month_start,
                timestamp__lt=next_month
            ).order_by('timestamp')
            
            # Calcular tiempo real de uso basado en períodos ON/OFF
            real_hours = calculate_real_heating_time(month_logs)
            monthly_data['hours'].insert(0, round(real_hours, 1))
        
        # Obtener estadísticas actuales
        current_sensor = SensorReading.objects.filter(
            temperature__isnull=False
        ).first()
        
        current_heating = HeatingLog.objects.first()
        
        current_stats = {
            'temperature': current_sensor.temperature if current_sensor else None,
            'humidity': current_sensor.humidity if current_sensor else None,
            'is_heating': current_heating.is_heating if current_heating else False,
            'target_temperature': current_heating.target_temperature if current_heating else None,
        }
        
        return JsonResponse({
            'sensor_data': sensor_data,
            'monthly_usage': monthly_data,
            'current_stats': current_stats,
            'period': period
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def calculate_real_heating_time(logs_queryset):
    """
    Calcula el tiempo real que la calefacción estuvo encendida
    basándose en los períodos entre logs de ON y OFF
    """
    logs = list(logs_queryset.values('timestamp', 'is_heating').order_by('timestamp'))
    
    if not logs:
        return 0.0
    
    total_seconds = 0.0
    heating_start = None
    
    for log in logs:
        if log['is_heating'] and heating_start is None:
            # Comienza un período de calefacción
            heating_start = log['timestamp']
        elif not log['is_heating'] and heating_start is not None:
            # Termina un período de calefacción
            heating_end = log['timestamp']
            period_seconds = (heating_end - heating_start).total_seconds()
            total_seconds += period_seconds
            heating_start = None
    
    # Si la calefacción seguía encendida al final del período
    if heating_start is not None and logs:
        # Asumir que sigue encendida hasta el último log
        last_log_time = logs[-1]['timestamp']
        period_seconds = (last_log_time - heating_start).total_seconds()
        total_seconds += period_seconds
    
    return total_seconds / 3600.0  # Convertir a horas