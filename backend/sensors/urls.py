from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SensorReadingViewSet, SensorStatusViewSet

router = DefaultRouter()
router.register(r'readings', SensorReadingViewSet)
router.register(r'status', SensorStatusViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]