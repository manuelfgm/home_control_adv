from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SensorReadingViewSet

router = DefaultRouter()
router.register(r'readings', SensorReadingViewSet)

app_name = 'sensors'
urlpatterns = [
    path('api/', include(router.urls)),
]