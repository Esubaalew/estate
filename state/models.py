from django.db import models
import uuid

class Customer(models.Model):
    USER_TYPE_CHOICES = [
        ('user', 'User'),
        ('agent', 'Agent'),
        ('owner', 'Owner'),
    ]

    telegram_id = models.CharField(max_length=255, unique=True, primary_key=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(default='Addis Ababa, Ethiopia')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='user')
    is_verified = models.BooleanField(default=False)
    legal_document = models.FileField(upload_to='do/legal_documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.full_name


class Property(models.Model):
    FOR_CHOICES = [
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('investment', 'For Investment'),
    ]

    TYPE_CHOICES = [
        ('residential', 'Residential'),
        # ('lease', 'Lease'),
        # ('commercial', 'Commercial'),
    ]

    USAGE_CHOICES = [
        ('villa', 'Villa'),
        ('apartmenent', 'Apartment'),
        ('duplex', 'Duplex'),
        ('condominium', 'Condominium'),
        ('townhouse', 'TownHouse'),
        ('other', 'Other')
    ]
    
    FEATURES_CHOICES = [
        ('finished', 'Finished'),
        ('semi_finished', 'Semi-finished'),
        ('furnished', 'Furnished'),
    ]
    
     # Choices for Kitchen Appliances
    KITCHEN_APPLIANCES_CHOICES = [
        ('oven', 'Oven'),
        ('fridge', 'Fridge'),
        ('microwave', 'Microwave'),
        ('dishwasher', 'Dishwasher'),
        ('other', 'Other'),
    ]
    
    # Choices for Laundry Facilities
    LAUNDRY_FACILITIES_CHOICES = [
        ('washing_machine', 'Washing Machine'),
        ('dryer', 'Dryer'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(Customer, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    for_property = models.CharField(max_length=10, choices=FOR_CHOICES)
    type_property = models.CharField(max_length=12, choices=TYPE_CHOICES)
    usage = models.CharField(max_length=12, choices=USAGE_CHOICES)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    subcity_zone = models.CharField(max_length=100)
    woreda = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    floor_level = models.CharField(max_length=20)
    total_area = models.FloatField()
    area = models.FloatField()
    google_map_link = models.URLField(max_length=200)
    living_rooms = models.IntegerField()
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    kitchens = models.IntegerField()
    built_date = models.DateField() 
    number_of_balconies = models.IntegerField()
    average_price_per_square_meter = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    computing_price = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    features_and_amenities = models.CharField(max_length=20, choices=FEATURES_CHOICES)
    heating_type = models.CharField(max_length=20, choices=[('gas', 'Gas'), ('electric', 'Electric')])
    cooling = models.CharField(max_length=20, choices=[('AC', 'AC'), ('electric', 'Electric')])
    nearest_residential = models.TextField()
    own_description = models.TextField()
    link_to_video_or_image = models.URLField(max_length=200, null=True, blank=True)
    ownership_of_property = models.FileField(upload_to='do/ownership_files/')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed')], default='pending')
       # New fields for kitchen appliances and laundry facilities (Text input)
    kitchen_appliances = models.CharField(max_length=255, blank=True, null=True)
    laundry_facilities = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class Tour(models.Model):
    class TourTime(models.IntegerChoices):
        ONE = 1, "1 AM"
        TWO = 2, "2 AM"
        THREE = 3, "3 AM"
        FOUR = 4, "4 AM"
        FIVE = 5, "5 AM"
        SIX = 6, "6 AM"
        SEVEN = 7, "7 AM"
        EIGHT = 8, "8 AM"
        NINE = 9, "9 AM"
        TEN = 10, "10 AM"
        ELEVEN = 11, "11 AM"
        TWELVE = 12, "12 PM"

    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    telegram_id = models.CharField(max_length=255, default="123456789")
    username = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255, default="John Doe")
    email = models.EmailField(default="mail@state.et")
    phone_number = models.CharField(max_length=15, default="+251911223344")
    tour_date = models.CharField(
        max_length=9,
        choices=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday")
        ],
        default="Monday"
    )
    tour_time = models.IntegerField(choices=TourTime.choices, default=TourTime.ONE)
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed')
        ],
        default='pending'
    )

    def __str__(self):
        return f"{self.property.name} - {self.full_name} ({self.telegram_id})"
        
class Favorite(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    telegram_post_url = models.URLField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('customer', 'property')

    def __str__(self):
        return f"{self.customer.full_name} - {self.property.name}"
