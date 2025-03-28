from django.conf import settings
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView
from django.conf.urls.static import static
from .views import CustomerViewSet, PropertyViewSet, TourViewSet, FavoriteViewSet
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'properties', PropertyViewSet)
router.register(r'tours', TourViewSet)
router.register(r'favorites', FavoriteViewSet)
urlpatterns = [
path('api/', include(router.urls)),
path("", views.index),
path("user/", views.profile, name="profile"),
path('add-property/', views.add_property, name='add_property'),
path('property-success/', TemplateView.as_view(template_name="success.html"), name='property_success'),
path('my-properties/', views.my_properties, name='my_properties'),
path('api/tours/telegram/<str:telegram_id>/', views.get_tours_by_telegram_id, name='get_tours_by_telegram_id'),
path('api/tours/check/', views.check_existing_tour, name='check_existing_tour'),
path('property/<int:pk>/', views.property_detail, name='property_detail'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)