from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Customer, Property, Tour, Favorite
from .serializers import CustomerSerializer, PropertySerializer, TourSerializer, FavoriteSerializer
from django.urls import reverse
import logging
import asyncio
import json
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .bot import bot_tele
from django.contrib import messages

from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

@csrf_exempt
def index(request):
    if request.method == 'POST':
        data = request.body
        res = json.loads(data.decode('utf-8'))

        # Log the JSON data to avoid print issues
        logger.info(json.dumps(res, ensure_ascii=False, indent=4))

        asyncio.run(bot_tele(res))
        return HttpResponse("ok")
    else:
        return render(request, 'index.html')

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def properties(self, request, pk=None):
        customer = self.get_object()
        properties = Property.objects.filter(owner=customer)
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'])
    def favorites(self, request, pk=None):
        customer = self.get_object()
        favorites = Favorite.objects.filter(customer=customer)
        serializer = FavoriteSerializer(favorites, many=True)
        return Response(serializer.data)


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    
    @action(detail=True, methods=['get'])
    def tours(self, request, pk=None):
        property_y = self.get_object()
        tours = Tour.objects.filter(property=property_y)
        serializer = TourSerializer(tours, many=True)
        return Response(serializer.data)

class TourViewSet(viewsets.ModelViewSet):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer

class FavoriteViewSet(viewsets.ModelViewSet):
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    
@csrf_exempt
def profile(request):
    start_param = request.GET.get('tgWebAppStartParam', '')
    profile_token = start_param.replace('edit-', '')  # Assuming profile_token is in the format 'edit-<token>'

    # Assuming you have a function to fetch user based on profile token
    user = get_object_or_404(Customer, profile_token=profile_token)  # Fetch user by profile token

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        user_type = request.POST.get('user_type', user.user_type)
        legal_document = request.FILES.get('legal_document')

        # Basic validation
        if not full_name:
            return render_profile_with_error(request, user, "Full Name cannot be empty.")

        # Additional checks based on user_type
        if user_type == 'owner':
            if not phone_number:
                return render_profile_with_error(request, user, "Phone Number is required for owners.")
            if not legal_document:
                return render_profile_with_error(request, user, "Legal Document is required for owners.")
        elif user_type == 'agent' and not phone_number:
            return render_profile_with_error(request, user, "Phone Number is required for agents.")

        # Update user fields
        user.full_name = full_name
        user.email = email
        user.phone_number = phone_number
        user.address = address
        user.is_verified = False  # Assuming this is set to false when profile is updated
        user.user_type = user_type

        if legal_document:
            user.legal_document = legal_document

        # Save changes to user
        user.save()

        # Redirect to profile page with the start parameter
        return HttpResponseRedirect(reverse('profile') + f"?tgWebAppStartParam={start_param}")

    # Render the profile template with user data
    return render_profile(request, user)




def render_profile_with_error(request, user, error):
    return render(request, 'profile.html', {
        'telegram_id': user.telegram_id,
        'full_name': user.full_name,
        'email': user.email,
        'phone_number': user.phone_number,
        'address': user.address,
        'is_verified': user.is_verified,
        'user_type': user.user_type,
        'legal_document': user.legal_document,
        'error': error,
        'profile_token': user.profile_token,  # Ensure profile token is passed here
    })

def render_profile(request, user):
    return render(request, 'profile.html', {
        'telegram_id': user.telegram_id,
        'full_name': user.full_name,
        'email': user.email,
        'phone_number': user.phone_number,
        'address': user.address,
        'is_verified': user.is_verified,
        'user_type': user.user_type,
        'legal_document': user.legal_document,
        'profile_token': user.profile_token,  
    })

    
@csrf_exempt
def add_property(request):
    if request.method == 'POST':
        # Extract data from POST request
        logger.info(f"GET parameters: {request.GET}")
        logger.info(f"POST parameters: {request.POST}")
        profile_token = request.GET.get('profile_token')
        logging.info(profile_token)
        print(profile_token)
        
        owner = get_object_or_404(Customer, profile_token=profile_token) 

        data = {
            'owner': owner,  # Set the owner from the retrieved Customer instance
            'name': request.POST.get('name'),
            'for_property': request.POST.get('for_property'),
            'type_property': request.POST.get('type_property'),
            'usage': request.POST.get('usage'),  # Include usage
            'country': request.POST.get('country'),  # Include country
            'region': request.POST.get('region'),  # Include region
            'city': request.POST.get('city'),  # Include city
            'subcity_zone': request.POST.get('subcity_zone'),  # Include subcity zone
            'woreda': request.POST.get('woreda'),  # Include woreda
            'address': request.POST.get('address'),  # Include address
            'floor_level': request.POST.get('floor_level'),  # Include floor level
            'total_area': request.POST.get('total_area'),
            'area': request.POST.get('area'),
            'google_map_link': request.POST.get('google_map_link'),
            'living_rooms': request.POST.get('living_rooms'),
            'bedrooms': request.POST.get('bedrooms'),
            'bathrooms': request.POST.get('bathrooms'),
            'kitchens': request.POST.get('kitchens'),  # Include kitchens
            'built_date': request.POST.get('built_date'),  # Include built date
            'number_of_balconies': request.POST.get('number_of_balconies'),  # Include balconies
            'average_price_per_square_meter': request.POST.get('average_price_per_square_meter'),
            'selling_price': request.POST.get('selling_price'),
            'computing_price': request.POST.get('computing_price'),  # Include computing price
            'monthly_rent': request.POST.get('monthly_rent'),
            'features_and_amenities': request.POST.get('features_and_amenities'),
            'heating_type': request.POST.get('heating_type'),  # Include heating type
            'cooling': request.POST.get('cooling'),  # Include cooling
            'nearest_residential': request.POST.get('nearest_residential'),
            'own_description': request.POST.get('own_description'),  # Include own description

            'link_to_video_or_image': request.POST.get('link_to_video_or_image'),  # Include video/image link
            'ownership_of_property': request.FILES.get('ownership_of_property'),  # Include ownership document
            
            'kitchen_appliances': request.POST.get('kitchen_appliances', ''),
            'laundry_facilities': request.POST.get('laundry_facilities', ''),
        }

        # Create Property instance and save
        property_instance = Property(**data)
        property_instance.save()

        messages.success(request, "Property added successfully!")
        return redirect('property_success')  # Redirect to success page

    return render(request, 'property_form.html')
    

@csrf_exempt  # Only if absolutely necessary
def my_properties(request):
    # Get the profile token from the request parameters
    profile_token = request.GET.get('profile_token')
    
    # Log the profile token for debugging purposes
    logger.info(f"Received profile token: {profile_token}")

  

    # Fetch the owner using the profile token
    owner = get_object_or_404(Customer, profile_token=profile_token)
    
    # Fetch properties associated with the owner
    properties = Property.objects.filter(owner=owner)

    # Prepare context data for the template
    context = {
        'properties': properties,
        'owner': owner,
    }
    
    # Render the my_properties.html template with the context
    return render(request, 'my_properties.html', context)


@api_view(['GET'])
def get_tours_by_telegram_id(request, telegram_id):
    """Fetch tours associated with a specific user by Telegram ID."""
    tours = Tour.objects.filter(telegram_id=telegram_id)  # Query using the telegram_id directly
    serializer = TourSerializer(tours, many=True)
    
    return Response(serializer.data)
    
@api_view(['GET'])
def check_existing_tour(request):
    telegram_id = request.GET.get('telegram_id')
    property_id = request.GET.get('property')

    if not telegram_id or not property_id:
        return Response({'error': 'telegram_id and property are required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Filter using property_id (note the use of _id for foreign key)
    existing_tours = Tour.objects.filter(telegram_id=telegram_id, property_id=property_id)

    if existing_tours.exists():
        return Response({'exists': True, 'tours': list(existing_tours.values())}, status=status.HTTP_200_OK)

    return Response({'exists': False}, status=status.HTTP_200_OK)
    
from django.shortcuts import render, get_object_or_404
from .models import Property

def property_detail(request, pk):
    # Fetch the property by its primary key (pk)
    property_instance = get_object_or_404(Property, pk=pk)

    # Render a template with the property details
    return render(request, 'property_detail.html', {
        'property': property_instance
    })
