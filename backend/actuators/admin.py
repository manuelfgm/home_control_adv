from django.contrib import admin
from .models import ActuatorStatus


@admin.register(ActuatorStatus)
class ActuatorStatusAdmin(admin.ModelAdmin):
    list_display = ['actuator_id', 'is_heating', 'temperature', 'wifi_signal', 'created_at']
    list_filter = ['actuator_id', 'is_heating', 'source', 'created_at']
    search_fields = ['actuator_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
