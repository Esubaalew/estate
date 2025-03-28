from rest_framework.routers import DefaultRouter
from .views import RequestViewSet, MessageViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'requests', RequestViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns =[
    path('live/', include(router.urls)),
]