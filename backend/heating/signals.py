from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='actuators.ActuatorStatus')
def on_actuator_status_saved(sender, instance, created, **kwargs):
    """
    Cuando llega un nuevo ActuatorStatus, si el estado anterior era
    'calefacción encendida', acumula el tiempo transcurrido en
    HeatingDailyUsage y HeatingMonthlyUsage.
    """
    if not created:
        return

    from actuators.models import ActuatorStatus
    from .models import record_heating_period

    # Registro anterior al nuevo (excluyendo el propio)
    prev = (
        ActuatorStatus.objects
        .filter(created_at__lt=instance.created_at)
        .order_by('-created_at')
        .first()
    )

    if prev is not None and prev.is_heating:
        record_heating_period(prev.created_at, instance.created_at)
