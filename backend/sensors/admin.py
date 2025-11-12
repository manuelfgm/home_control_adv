from django.contrib import admin
from .models import SensorReading


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ['sensor_id', 'temperature', 'humidity', 'sensor_error', 'created_at']
    list_filter = ['sensor_id', 'sensor_error', 'source', 'created_at']
    search_fields = ['sensor_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
