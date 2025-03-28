import os
import requests
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer, Property, Tour
import telegram
from telegram.constants import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Customer)
def user_type_upgrade(sender, instance, created, **kwargs):
    if not created and instance.user_type in ['agent', 'owner']:
        send_telegram_message(instance.telegram_id, instance.user_type)

def send_telegram_message(telegram_id, user_type):
    token = os.getenv('TOKEN')
    message = (
        f"✨ Your account has been upgraded to the new user type: *{user_type}*.\n\n"
        "You can now use the /addproperty command to list properties.\n"
        "This action is *irreversible*."
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': telegram_id,
        'text': message,
        'parse_mode': ParseMode.MARKDOWN,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")

@receiver(post_save, sender=Property)
def post_property_to_telegram(sender, instance, **kwargs):
    if instance.status == "confirmed":
        bot_token = os.getenv("TOKEN")
        bot = telegram.Bot(token=bot_token)

        owner = instance.owner
        confirmed_properties_count = Property.objects.filter(owner=owner, status="confirmed").count()
        verified_status = "Verified Client ✅" if owner.is_verified else "Unverified Client ❌"

        message = (
            f"🏠 *Property Name:* {instance.name}\n\n"
            f"📍 *Location:* {instance.city}, {instance.region}\n\n"
            f"🗺️ *Google Map Link:* {instance.google_map_link}\n\n"
            f"📏 *Total Area:* {instance.total_area} sqm\n\n"
            f"💵 *Selling Price:* ${instance.selling_price}\n\n"
            f"💲 *Average Price per sqm:* ${instance.average_price_per_square_meter}\n\n"
            f"🏢 *Type:* {instance.get_type_property_display()}\n\n"
            f"🏘️ *Usage:* {instance.get_usage_display()}\n\n"
            f"🛌 *Bedrooms:* {instance.bedrooms}\n\n"
            f"🛁 *Bathrooms:* {instance.bathrooms}\n\n"
            f"🍳 *Kitchens:* {instance.kitchens}\n\n"
            f"🌡️ *Heating Type:* {instance.heating_type}\n\n"
            f"❄️ *Cooling:* {instance.cooling}\n\n"
            f"🏙️ *Subcity/Zone:* {instance.subcity_zone}, Woreda {instance.woreda}\n\n"
            f"🏗️ *Built Date:* {instance.built_date}\n\n"
            f"🌄 *Balconies:* {instance.number_of_balconies}\n\n"
            f"📜 *Description:* {instance.own_description}\n\n"
            f"🔗 *Additional Media:* {instance.link_to_video_or_image}\n\n"
            f"*Owner Details:*\n"
            f"{verified_status}\n\n"
            f"🔢 *Properties Listed:* {confirmed_properties_count}\n\n"
            f"---\n\n"
            f"Contact us for more details or view on the map!\n"
        )

        # Send a congratulatory message to the owner
        congratulatory_message = (
            f"🎉 Congratulations, {owner.full_name}! 🎉\n"
            f"Your property *{instance.name}* has been approved and is now live on the channel! 🌟\n"
            f"View it here: [View on Channel](https://t.me/yene_et)\n"
        )

        # Sending the congratulatory message to the property owner
        owner_message_payload = {
            'chat_id': owner.telegram_id,
            'text': congratulatory_message,
            'parse_mode': ParseMode.MARKDOWN,
        }

        try:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=owner_message_payload)
        except requests.exceptions.RequestException as e:
            print(f"Failed to send congratulatory message to owner: {e}")

        # Adding the 'View' button and other buttons
        keyboard = [
            [
                InlineKeyboardButton("Request Tour", url=f"https://t.me/yene_etbot?start=request_tour_{instance.id}"),
                InlineKeyboardButton("Make Favorite", callback_data=f"make_favorite_{instance.id}")
            ],
            [
                InlineKeyboardButton("View Property", url=f"https://estate-show.onrender.com/property/{instance.id}")  # Direct URL to property page
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        async_to_sync(bot.send_message)(
            chat_id="@yene_et",
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


@receiver(post_save, sender=Tour)
def notify_admin_on_tour_request(sender, instance, created, **kwargs):
    """Send a notification to the admin when a new tour request is created."""
    if created:
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        bot_token = os.getenv("TOKEN")
        bot = telegram.Bot(token=bot_token)

        # Get tour and property details
        property_details = (
            f"🏠 *Property Name:* {instance.property.name}\n"
            f"📍 *Location:* {instance.property.city}, {instance.property.region}\n"
            f"🔢 *Property ID:* {instance.property.id}\n"
            f"🗺️ *Google Map Link:* {instance.property.google_map_link}\n"
        )
        request_details = (
            f"👤 *Requested By:* {instance.full_name}\n"
            f"📞 *Contact Number:* {instance.phone_number}\n"
            f"📅 *Requested Date:* {instance.tour_date}\n"
            f"⏰ *Requested Time:* {instance.tour_time}\n"
        )

        message = (
            f"🚨 *New Tour Request Notification*\n\n"
            f"{property_details}\n"
            f"{request_details}\n"
            "Please review and manage this request accordingly."
        )

        try:
            async_to_sync(bot.send_message)(
                chat_id=admin_chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
            )
        except telegram.error.TelegramError as e:
            print(f"Failed to send admin notification: {e}")
            
def send_verification_message(telegram_id):
    token = os.getenv('TOKEN')
    message = (
        "🎉 Congratulations! 🎉\n"
        "Your account has been verified! 🎖️\n"
        "As a verified client, you are more trusted than regular users. This means you can enjoy enhanced services and opportunities!\n"
        "Thank you for being a valued part of our community! 🌟"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': telegram_id,
        'text': message,
        'parse_mode': ParseMode.MARKDOWN,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send verification message: {e}")
        
@receiver(post_save, sender=Customer)
def notify_user_on_verification(sender, instance, created, **kwargs):
    """Send a congratulatory message to the user when their account is verified."""
    if not created and instance.is_verified:  # Check if it's not a new instance and is_verified is True
        send_verification_message(instance.telegram_id)

