from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActuatorStatusViewSet

router = DefaultRouter()
router.register(r'status', ActuatorStatusViewSet)

app_name = 'actuators'
urlpatterns = [
    path('api/', include(router.urls)),
]