from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActuatorStatusViewSet, ActuatorReadingsViewSet

router = DefaultRouter()
router.register(r'status', ActuatorStatusViewSet)
router.register(r'readings', ActuatorReadingsViewSet)

app_name = 'actuators'
urlpatterns = [
    path('api/', include(router.urls)),
]