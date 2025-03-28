from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Customer, Property, Tour, Favorite  

admin.site.site_header = "Real Estate Admin Portal"
admin.site.site_title = "Real Estate Admin"
admin.site.index_title = "Welcome to the Real Estate Admin Dashboard"

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'email', 'user_type', 'is_verified', 'created_at')
    list_filter = ('user_type', 'is_verified')
    search_fields = ('telegram_id', 'full_name', 'email')
    readonly_fields = ('created_at', 'telegram_id',)

@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = ('name', 'owner', 'for_property', 'type_property', 'city', 'selling_price', 'status')
    list_filter = ('for_property', 'type_property', 'status', 'city')
    search_fields = ('name', 'owner__full_name', 'city', 'region', 'address')
    readonly_fields = ('built_date',)
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'for_property', 'type_property', 'usage', 'status')
        }),
        ('Location Details', {
            'fields': ('country', 'region', 'city', 'subcity_zone', 'woreda', 'address', 'floor_level')
        }),
        ('Property Details', {
            'fields': ('total_area', 'area', 'google_map_link', 'living_rooms', 'bedrooms', 'bathrooms', 
                       'kitchens', 'built_date', 'number_of_balconies')
        }),
        ('Pricing', {
            'fields': ('average_price_per_square_meter', 'selling_price', 'computing_price', 'monthly_rent')
        }),
        ('Additional Info', {
            'fields': ('features_and_amenities', 'heating_type', 'cooling', 'nearest_residential', 
                       'own_description', 'link_to_video_or_image', 'ownership_of_property')
        }),
    )

@admin.register(Tour)
class TourAdmin(ModelAdmin):
    list_display = ('property', 'full_name', 'phone_number', 'tour_date', 'tour_time', 'status', 'telegram_id', 'username')
    list_filter = ('tour_date', 'tour_time', 'status', 'property')
    search_fields = ('property__name', 'full_name', 'phone_number', 'telegram_id', 'username')
    readonly_fields = ('property', 'telegram_id', 'username')
    fieldsets = (
        (None, {
            'fields': ('property', 'full_name', 'phone_number', 'telegram_id', 'username', 'tour_date', 'tour_time', 'status')
        }),
    )

@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ('customer', 'property') 
    readonly_fields = ('customer', 'property')
    search_fields = ('customer__full_name', 'property__name')  
    fieldsets = (
        (None, {
            'fields': ('customer', 'property')
        }),
    )
