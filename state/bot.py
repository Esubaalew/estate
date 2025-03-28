# -*- coding: utf-8 -*-
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters, PicklePersistence, CallbackQueryHandler
)
from telegram.constants import ParseMode, ChatAction
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
import os
import logging
import aiohttp  # Import aiohttp

# Assume state.tools and live.api are now async modules using aiohttp
# Make sure these modules are correctly placed relative to this script
# or installed in the Python environment.
# We will call their functions using 'await'.
from state.tools import (
    register_user, is_user_registered, get_user_details,
    get_user_properties, get_user_tours, get_property_details,
    get_user_favorites, get_non_user_accounts, get_confirmed_user_properties
)
from live.api import (
    create_message, get_all_requests, get_request_details,
    get_all_messages, create_request
)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('webhook')
API_BASE_URL = "https://estate-r22a.onrender.com"  # New API Base URL
PERSISTENCE_FILE = 'bot_dat'
PAGE_SIZE = 2
ADMINS = [1648265210] # Example Admin ID - Replace with actual admin IDs

# Initialize persistence
persistence = PicklePersistence(filepath=PERSISTENCE_FILE)

# Define states for conversation flows
FULL_NAME, PHONE_NUMBER, TOUR_DATE, TOUR_TIME = range(4)
LIVE_REQUEST, LIVE_PHONE, LIVE_ADDRESS, LIVE_ADDITIONAL_TEXT = range(4, 8) # Renumbered to avoid overlap
RESPOND_TO_REQUEST, RESPONSE_MESSAGE = range(8, 10) # Renumbered to avoid overlap

# Define available languages
LANGUAGES = ["Amharic", "English"]

# --- Helper Functions ---

def get_main_menu():
    """Generate the main menu inline keyboard with descriptive emojis."""
    buttons = [
        [InlineKeyboardButton("➕ Add Property 🏡", callback_data="add_property")],
        [InlineKeyboardButton("✨ Upgrade Account ⭐", callback_data="upgrade_account")],
        [InlineKeyboardButton("👤 View Profile 🔍", callback_data="view_profile")],
        [InlineKeyboardButton("📋 List Properties 📂", callback_data="list_properties:1")], # Start on page 1
        [InlineKeyboardButton("❤️ List Favorites 💾", callback_data="list_favorites:1")], # Start on page 1
        [InlineKeyboardButton("📅 List Tours 🗓️", callback_data="list_tours:1")],       # Start on page 1
        [InlineKeyboardButton("💬 Live Agent 📞", callback_data="live_agent")],
        [InlineKeyboardButton("🌐 Change Language 🌍", callback_data="change_language")],
    ]
    # Admin-specific buttons
    # Assuming ADMINS list contains integer IDs
    # We need context to check user_id, so this might be better placed within the command handler
    # For simplicity, let's add a general admin command instead of modifying the main menu dynamically here.

    # Arrange buttons (example: 2 columns)
    formatted_buttons = []
    for i in range(0, len(buttons), 2):
        row = buttons[i]
        if i + 1 < len(buttons):
            row += buttons[i + 1]
        formatted_buttons.append(row)

    return InlineKeyboardMarkup(formatted_buttons)

async def send_or_edit(update: Update, text: str, reply_markup=None, parse_mode=None):
    """Helper to send or edit a message based on update type."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command: Handles registration, deep-linking, and main menu."""
    user = update.effective_user
    telegram_id = str(user.id)
    full_name = user.full_name
    username = user.username or "" # Handle cases where username is not set

    context.user_data['telegram_id'] = telegram_id
    context.user_data['username'] = username

    args = context.args
    if args and args[0].startswith("request_tour_"):
        try:
            property_id = args[0].split("_")[2]
            context.user_data['property_id'] = property_id
            await update.message.reply_text("Welcome! To schedule a tour for this property, please provide your full name.")
            return FULL_NAME # Start tour request conversation
        except (IndexError, ValueError):
            await update.message.reply_text("Invalid tour request link. Use /start to begin.")
            return ConversationHandler.END

    try:
        # Use await for the async function is_user_registered
        registered = await is_user_registered(telegram_id)

        if registered:
            # Use await for the async function get_user_details
            user_details = await get_user_details(telegram_id)
            if user_details:
                # profile_token = user_details.get("profile_token") # Not used directly here
                await update.message.reply_text(
                    f"Welcome back, {full_name}! Here are some quick options:",
                    reply_markup=get_main_menu()
                )
            else:
                await update.message.reply_text("Could not retrieve your details. Please try again later or contact support.")
        else:
            # Use await for the async function register_user
            result = await register_user(telegram_id, full_name, username)
            if result and result.get("status") == "success":
                 await update.message.reply_text(result.get("message", "Registration successful!"))
                 await update.message.reply_text("You’re registered! Here are some quick options:", reply_markup=get_main_menu())
            else:
                 await update.message.reply_text(result.get("message", "Registration failed. Please try again later."))

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during start for user {telegram_id}: {e}")
        await update.message.reply_text("Sorry, I couldn't connect to the service right now. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error during start for user {telegram_id}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred. Please try again.")

    # If it's part of a conversation, return END, otherwise None is fine.
    # Since it can start a conversation via deep link, we need to handle the return value carefully.
    # If not starting the tour convo, it shouldn't return a state.
    if not (args and args[0].startswith("request_tour_")):
         return ConversationHandler.END # Explicitly end if not starting tour convo


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Profile command: Show profile edit link."""
    telegram_id = str(update.effective_user.id)
    logger.info(f"Profile command triggered for user {telegram_id}")

    if update.callback_query:
        await update.callback_query.answer()

    try:
        # Use await for the async function get_user_details
        user_details = await get_user_details(telegram_id)

        if not user_details:
            message = "Could not retrieve your details. Are you registered? Use /start."
            await send_or_edit(update, message)
            return

        profile_token = user_details.get("profile_token")
        if not profile_token:
             message = "Could not find your profile identifier. Please contact support."
             await send_or_edit(update, message)
             return

        # Ensure the web app URL is correctly formatted
        # The example URL structure might need adjustment based on your web app's routing
        web_app_url = f"https://t.me/{context.bot.username}/state?startapp=edit-{profile_token}" # Example structure
        message = "Click the button below to view or edit your profile:"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👤 Edit Profile", web_app_url=web_app_url)]] # Use web_app_url
        )
        await send_or_edit(update, message, reply_markup=reply_markup)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during profile for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during profile for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred.")


async def addproperty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add property command: Check permissions and provide link."""
    telegram_id = str(update.effective_user.id)
    logger.info(f"addproperty triggered for user {telegram_id}")

    if update.callback_query:
        await update.callback_query.answer()

    try:
        # Use await for the async function get_user_details
        user_details = await get_user_details(telegram_id)

        if not user_details:
            message = "Could not retrieve your details. Are you registered? Use /start."
            await send_or_edit(update, message)
            return

        user_type = user_details.get("user_type")
        profile_token = user_details.get("profile_token")

        if not profile_token:
             message = "Could not find your profile identifier. Please contact support."
             await send_or_edit(update, message)
             return

        if user_type == 'user':
            message = (
                "You can only browse properties. To add your own, "
                "please upgrade your account first using the 'Upgrade Account' option or /upgrade."
            )
            await send_or_edit(update, message)

        elif user_type in ['agent', 'owner', 'company']: # Added company
             # Adjust the web app URL as needed
            web_app_url = f"https://t.me/{context.bot.username}/state?startapp=add-{profile_token}" # Example: separate 'add' startapp param
            message = "You can add properties! Use the button below:"
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("➕ Add Property", web_app_url=web_app_url)]] # Use web_app_url
            )
            await send_or_edit(update, message, reply_markup=reply_markup)

        else:
            message = f"Your user type ('{user_type}') is not recognized for adding properties. Please contact support."
            await send_or_edit(update, message)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during addproperty for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during addproperty for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred.")


async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upgrade account command: Provide link to profile for upgrade."""
    telegram_id = str(update.effective_user.id)
    logger.info(f"Upgrade triggered for user {telegram_id}")

    if update.callback_query:
        await update.callback_query.answer()

    try:
        # Use await for the async function get_user_details
        user_details = await get_user_details(telegram_id)

        if not user_details:
            message = "Could not retrieve your details. Are you registered? Use /start."
            await send_or_edit(update, message)
            return

        user_type = user_details.get("user_type")
        profile_token = user_details.get("profile_token")

        if not profile_token:
             message = "Could not find your profile identifier. Please contact support."
             await send_or_edit(update, message)
             return

        if user_type in ['agent', 'owner', 'company']:
            message = f"You are already an upgraded user ({user_type.capitalize()}). Use /profile to manage your account."
            await send_or_edit(update, message)

        elif user_type == 'user':
            # Point to the general profile edit link where upgrade options should be
            web_app_url = f"https://t.me/{context.bot.username}/state?startapp=edit-{profile_token}" # Example structure
            message = (
                "Account upgrades allow you to list properties. Note: Upgrades might be irreversible. "
                "Visit your profile via the button below to choose an upgrade option (e.g., Agent, Owner):"
            )
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("👤 Edit Profile to Upgrade", web_app_url=web_app_url)]] # Use web_app_url
            )
            await send_or_edit(update, message, reply_markup=reply_markup)

        else:
            message = f"User type ('{user_type}') not recognized. Please contact support."
            await send_or_edit(update, message)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during upgrade for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during upgrade for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred.")

# --- Tour Request Conversation Handlers ---

async def request_tour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the tour request conversation (entry point via command)."""
    # This handler is triggered by /request_tour_<id> command regex
    command_parts = update.message.text.split("_")

    if len(command_parts) != 3: # Expects /request_tour_<id>
        await update.message.reply_text("Invalid command format. Use /start or the buttons.")
        return ConversationHandler.END

    property_id = command_parts[2]
    context.user_data['property_id'] = property_id
    # Store user info from the start
    context.user_data['telegram_id'] = str(update.effective_user.id)
    context.user_data['username'] = update.effective_user.username or ""

    await update.message.reply_text("Please provide your full name for the tour booking.")
    return FULL_NAME

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores full name and asks for phone number."""
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Thanks! Now, please provide your phone number (e.g., +251...).")
    return PHONE_NUMBER

async def get_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores phone number and asks for tour date."""
    # Basic validation could be added here
    context.user_data['phone_number'] = update.message.text

    days_keyboard = [
        ["Monday", "Tuesday", "Wednesday"],
        ["Thursday", "Friday", "Saturday"],
        ["Sunday", "/cancel"] # Add cancel option
    ]
    await update.message.reply_text(
        "Great! Please select a preferred day for your tour:",
        reply_markup=ReplyKeyboardMarkup(days_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return TOUR_DATE

async def get_tour_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores tour date and asks for tour time."""
    tour_date = update.message.text
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if tour_date not in valid_days:
        # Re-prompt with the keyboard if invalid day
        await update.message.reply_text(
            "Invalid selection. Please choose a day from the buttons.",
            reply_markup=ReplyKeyboardMarkup(
                [["Monday", "Tuesday", "Wednesday"],
                 ["Thursday", "Friday", "Saturday"],
                 ["Sunday", "/cancel"]], one_time_keyboard=True, resize_keyboard=True
            )
        )
        return TOUR_DATE # Stay in the same state

    context.user_data['tour_date'] = tour_date

    # Remove the reply keyboard before showing inline keyboard
    await update.message.reply_text("Thank you! Now, please select a time slot.", reply_markup=ReplyKeyboardRemove())

    # Example time slots (adjust as needed)
    time_buttons = [
        [InlineKeyboardButton("9:00 - 11:00", callback_data="9-11")],
        [InlineKeyboardButton("11:00 - 13:00", callback_data="11-13")],
        [InlineKeyboardButton("14:00 - 16:00", callback_data="14-16")],
        [InlineKeyboardButton("16:00 - 18:00", callback_data="16-18")],
        # Add a cancel button?
        # [InlineKeyboardButton("Cancel Request", callback_data="tour_cancel")]
    ]
    await update.message.reply_text(
        "Finally, select a preferred time slot for the tour:",
        reply_markup=InlineKeyboardMarkup(time_buttons)
    )
    return TOUR_TIME

async def get_tour_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores tour time, submits the request, and ends conversation."""
    query = update.callback_query
    await query.answer()

    tour_time_slot = query.data # e.g., "9-11"
    # Add validation if needed, e.g., check if data is one of the expected slots
    valid_slots = ["9-11", "11-13", "14-16", "16-18"]
    if tour_time_slot not in valid_slots:
        await query.edit_message_text("Invalid time slot selected. Please try scheduling again or /cancel.")
        # Maybe re-show the time buttons? For simplicity, ending here.
        return ConversationHandler.END

    context.user_data['tour_time'] = tour_time_slot # Store the selected slot string

    # Submit the tour details using the async function
    success = await register_tour_details(context.user_data)

    if success:
        await query.edit_message_text(
            "✅ Your tour request has been submitted successfully! "
            "The agent/owner will contact you to confirm."
            "\nYou can view your pending tours with /list_tours."
        )
    else:
        await query.edit_message_text(
            "❌ Sorry, there was an error submitting your tour request. "
            "Please try again later or contact support."
        )

    # Clean up user_data specific to this conversation if needed
    # context.user_data.pop('property_id', None)
    # context.user_data.pop('full_name', None)
    # etc.

    return ConversationHandler.END

async def register_tour_details(user_data: dict) -> bool:
    """Asynchronously submits tour details to the API using aiohttp."""
    telegram_id = str(user_data.get('telegram_id'))
    username = user_data.get('username', '')
    property_id = user_data.get('property_id')
    full_name = user_data.get('full_name')
    phone_number = user_data.get('phone_number')
    tour_date = user_data.get('tour_date')
    tour_time = user_data.get('tour_time') # This is the time slot string

    if not all([property_id, full_name, phone_number, tour_date, tour_time, telegram_id]):
        logger.error(f"Missing data for tour registration: {user_data}")
        return False

    api_url = f"{API_BASE_URL}/api/tours/"
    payload = {
        "property": property_id, # Assuming API expects property ID directly
        "full_name": full_name,
        "phone_number": phone_number,
        "tour_date": tour_date, # Send the day name string
        "tour_time_slot": tour_time, # Send the time slot string
        "telegram_id": telegram_id,
        "username": username
    }
    logger.info(f"Submitting tour request to {api_url} with data: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                if response.status == 201: # Check for 'Created' status
                    logger.info(f"Tour request submitted successfully for user {telegram_id}, property {property_id}")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to submit tour request. Status: {response.status}, Response: {response_text}, Data: {payload}")
                    return False
    except aiohttp.ClientError as e:
        logger.error(f"API connection error during tour registration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during tour registration: {e}", exc_info=True)
        return False

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the current conversation."""
    await update.message.reply_text(
        "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    # Clean up conversation-specific data
    keys_to_remove = ['property_id', 'full_name', 'phone_number', 'tour_date', 'tour_time', 'name', 'phone', 'address', 'additional_text', 'request_id', 'user_id']
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    return ConversationHandler.END

# Renamed from 'leave' to avoid conflict if used elsewhere
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generic cancellation handler for conversations."""
    await update.message.reply_text(
        "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
    )
     # Clean up conversation-specific data
    keys_to_remove = ['property_id', 'full_name', 'phone_number', 'tour_date', 'tour_time', 'name', 'phone', 'address', 'additional_text', 'request_id', 'user_id']
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback handler for conversations."""
    await update.message.reply_text(
        "Sorry, I didn't understand that. Please follow the instructions or use /cancel to exit."
    )


# --- Listing Handlers ---

async def list_properties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List properties associated with the user with pagination."""
    telegram_id = str(update.effective_user.id)
    current_page = 1

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            # Extract page number from callback_data like "list_properties:2"
            current_page = int(query.data.split(":")[1])
        except (IndexError, ValueError):
            current_page = 1 # Default to page 1 if parsing fails
    logger.info(f"List properties triggered for user {telegram_id} on page {current_page}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function get_user_properties
        properties = await get_user_properties(telegram_id)

        if not properties:
            message = "🏡 You don't have any properties listed yet! Use the 'Add Property' button or /addproperty."
            await send_or_edit(update, message)
            return

        # Calculate pagination
        total_properties = len(properties)
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_properties = properties[start_index:end_index]

        if not paginated_properties and current_page > 1:
             # If current page is empty but not the first page, maybe user deleted items? Go back.
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_properties = properties[start_index:end_index]

        if not paginated_properties:
             message = "🏡 You don't have any properties listed on this page."
             await send_or_edit(update, message)
             return


        # Prepare the response text
        response_text = f"📝 *Your Properties (Page {current_page})*:\n\n"
        for i, prop in enumerate(paginated_properties, start=start_index + 1):
            # Escape markdown characters in property name
            prop_name_safe = prop.get('name', 'N/A').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            status_safe = prop.get('status', 'N/A').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            # Add more details if available and desired
            response_text += f"{i}. 📍 *{prop_name_safe}* - Status: `{status_safe}`\n" # Use MarkdownV2 safe formatting

        # Create pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_properties:{current_page - 1}"))
        if end_index < total_properties:
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_properties:{current_page + 1}"))
        if row:
            buttons.append(row)
        # Add a button to go back to the main menu maybe?
        buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])

        keyboard = InlineKeyboardMarkup(buttons)

        # Send the response using MarkdownV2
        await send_or_edit(update, response_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during list_properties for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during list_properties for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred while fetching your properties.")


async def list_tours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List tours associated with the user with pagination."""
    telegram_id = str(update.effective_user.id)
    current_page = 1

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            current_page = int(query.data.split(":")[1])
        except (IndexError, ValueError):
            current_page = 1
    logger.info(f"List tours triggered for user {telegram_id} on page {current_page}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function get_user_tours
        tours = await get_user_tours(telegram_id)

        if not tours:
            message = "🚶‍♂️ You have no scheduled tours yet! Find a property and request a tour."
            await send_or_edit(update, message)
            return

        # Calculate pagination
        total_tours = len(tours)
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_tours = tours[start_index:end_index]

        if not paginated_tours and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_tours = tours[start_index:end_index]

        if not paginated_tours:
             message = "📅 You don't have any tours listed on this page."
             await send_or_edit(update, message)
             return

        # Prepare the response text
        response_text = f"📅 *Your Scheduled Tours (Page {current_page})*:\n\n"
        for i, tour in enumerate(paginated_tours, start=start_index + 1):
            # Use await for the async function get_property_details
            property_details = await get_property_details(tour.get('property')) # Safely get property ID
            prop_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'
            # Escape markdown
            prop_name_safe = prop_name.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            tour_date_safe = tour.get('tour_date', 'N/A').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            tour_time_safe = tour.get('tour_time_slot', 'N/A').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`") # Use tour_time_slot
            tour_status = tour.get('status', 'Pending').capitalize() # Assuming a status field exists
            tour_status_safe = tour_status.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")

            response_text += (
                f"{i}\\. 🏡 Property: *{prop_name_safe}*\n"
                f"   🗓️ Date: `{tour_date_safe}`\n"
                f"   ⏰ Time Slot: `{tour_time_safe}`\n"
                f"   Status: `{tour_status_safe}`\n\n" # Added status
            )

        # Create pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_tours:{current_page - 1}"))
        if end_index < total_tours:
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_tours:{current_page + 1}"))
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])

        keyboard = InlineKeyboardMarkup(buttons)

        await send_or_edit(update, response_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during list_tours for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during list_tours for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred while fetching your tours.")


async def list_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List favorite properties associated with the user with pagination."""
    telegram_id = str(update.effective_user.id)
    current_page = 1

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            current_page = int(query.data.split(":")[1])
        except (IndexError, ValueError):
            current_page = 1
    logger.info(f"List favorites triggered for user {telegram_id} on page {current_page}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function get_user_favorites
        favorites = await get_user_favorites(telegram_id)

        if not favorites:
            message = "❤️ You have no favorite properties yet! Use the ❤️ button on property listings to add some."
            await send_or_edit(update, message)
            return

        # Calculate pagination
        total_favorites = len(favorites)
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_favorites = favorites[start_index:end_index]

        if not paginated_favorites and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_favorites = favorites[start_index:end_index]

        if not paginated_favorites:
             message = "❤️ You don't have any favorites listed on this page."
             await send_or_edit(update, message)
             return


        # Prepare the response text
        response_text = f"🌟 *Your Favorite Properties (Page {current_page})*:\n\n"
        prop_ids = [fav.get('property') for fav in paginated_favorites if fav.get('property')]

        # Batch fetch property details if possible, otherwise fetch one by one
        property_details_map = {}
        for prop_id in prop_ids:
            details = await get_property_details(prop_id) # Use await
            if details:
                property_details_map[prop_id] = details

        for i, favorite in enumerate(paginated_favorites, start=start_index + 1):
            prop_id = favorite.get('property')
            details = property_details_map.get(prop_id)
            prop_name = details.get('name', 'Unknown Property') if details else 'Unknown Property'
            # Escape markdown
            prop_name_safe = prop_name.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            # You could add a link or button to view the property here
            response_text += f"{i}\\. 🏡 *{prop_name_safe}* (ID: `{prop_id}`)\n"


        # Create pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_favorites:{current_page - 1}"))
        if end_index < total_favorites:
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_favorites:{current_page + 1}"))
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])

        keyboard = InlineKeyboardMarkup(buttons)

        await send_or_edit(update, response_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during list_favorites for user {telegram_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during list_favorites for user {telegram_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred while fetching your favorites.")


async def handle_favorite_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles adding/removing a property from favorites via callback query."""
    query = update.callback_query
    await query.answer() # Acknowledge immediately
    data = query.data # e.g., "make_favorite_123"

    if not data.startswith("make_favorite_"):
        logger.warning(f"Invalid favorite callback data received: {data}")
        return # Should not happen if buttons are generated correctly

    try:
        property_id = int(data.split("_")[2])
        telegram_id = str(query.from_user.id)
        logger.info(f"Favorite request for property {property_id} by user {telegram_id}")

        # Use await for async functions
        favorites = await get_user_favorites(telegram_id)
        property_details = await get_property_details(property_id)

        property_name = property_details.get('name', 'this property') if property_details else 'this property'
        # Escape markdown for property name
        property_name_safe = property_name.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")


        # Check if already favorited and get the favorite record ID (if API provides it)
        favorite_record = next((fav for fav in favorites if fav.get('property') == property_id), None)

        api_base = f"{API_BASE_URL}/api/favorites"
        action_taken = ""

        async with aiohttp.ClientSession() as session:
            if favorite_record:
                # Already a favorite, so remove it
                favorite_id = favorite_record.get('id') # Assumes API includes 'id' in favorite list response
                if favorite_id:
                    delete_url = f"{api_base}/{favorite_id}/"
                    async with session.delete(delete_url) as response:
                        if response.status == 204: # No Content on success
                            action_taken = f"❌ Property *{property_name_safe}* removed from your favorites\\."
                            logger.info(f"Removed favorite {favorite_id} for user {telegram_id}")
                        else:
                            response_text = await response.text()
                            action_taken = "❌ Failed to remove from favorites. Please try again."
                            logger.error(f"Failed to remove favorite {favorite_id}. Status: {response.status}, Response: {response_text}")
                else:
                     action_taken = "❌ Could not identify the favorite record to remove. Contact support."
                     logger.error(f"Favorite record for property {property_id} for user {telegram_id} lacks an 'id'. Record: {favorite_record}")

            else:
                # Not a favorite, so add it
                post_url = f"{api_base}/"
                payload = {"property": property_id, "customer_telegram_id": telegram_id} # Adjust payload key if needed
                async with session.post(post_url, json=payload) as response:
                    if response.status == 201: # Created
                        action_taken = f"❤️ Property *{property_name_safe}* added to your favorites\\!"
                        logger.info(f"Added favorite for property {property_id}, user {telegram_id}")
                    else:
                        response_text = await response.text()
                        action_taken = "❌ Failed to add to favorites. Please try again."
                        logger.error(f"Failed to add favorite for property {property_id}. Status: {response.status}, Response: {response_text}, Payload: {payload}")

        # Send feedback message to the user (not editing the original property message)
        await context.bot.send_message(
            chat_id=telegram_id,
            text=action_taken,
            parse_mode=ParseMode.MARKDOWN_V2
        )

    except (IndexError, ValueError):
        logger.error(f"Could not parse property ID from favorite callback data: {data}")
        await context.bot.send_message(chat_id=query.from_user.id, text="❌ Error processing favorite request.")
    except aiohttp.ClientError as e:
        logger.error(f"API connection error during favorite request: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text="❌ Network error. Could not update favorites.")
    except Exception as e:
        logger.error(f"Unexpected error during favorite request: {e}", exc_info=True)
        await context.bot.send_message(chat_id=query.from_user.id, text="❌ An unexpected error occurred.")

# --- Admin Handlers ---

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin) List non-'user' type accounts with pagination."""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await send_or_edit(update, "🚫 Access denied. This command is for administrators only.")
        return

    current_page = 1
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            current_page = int(query.data.split(":")[1])
        except (IndexError, ValueError):
            current_page = 1
    logger.info(f"Admin {user_id} listing users on page {current_page}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function get_non_user_accounts
        users = await get_non_user_accounts() # Fetches agents, owners, etc.

        if not users:
            message = "👥 No registered agents, owners, or companies found."
            await send_or_edit(update, message)
            return

        # Filter/sort if needed, e.g., by user_type or name
        users.sort(key=lambda u: u.get('full_name', ''))

        # Calculate pagination
        total_users = len(users)
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_users = users[start_index:end_index]

        if not paginated_users and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_users = users[start_index:end_index]

        if not paginated_users:
             message = "👥 No users found on this page."
             await send_or_edit(update, message)
             return

        # Prepare the response text
        response_text = f"👥 *Registered Agents/Owners/Companies (Page {current_page})*:\n\n"
        for i, user in enumerate(paginated_users, start=start_index + 1):
            # Use await for the async function get_confirmed_user_properties
            try:
                confirmed_properties = await get_confirmed_user_properties(user.get('telegram_id'))
                property_count = len(confirmed_properties) if confirmed_properties else 0
            except Exception: # Handle cases where the function might fail for a user
                property_count = 'Error'

            user_type_icon = "👤" if user.get("user_type") == "agent" else "🏢" if user.get("user_type") in ["owner", "company"] else "❓"
            full_name_safe = user.get('full_name', 'N/A').replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            user_type_safe = user.get('user_type', 'N/A').capitalize().replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            telegram_id_safe = str(user.get('telegram_id', 'N/A')).replace("-", "\\-")

            response_text += (
                f"{i}\\. {user_type_icon} *{full_name_safe}*\n"
                f"   Type: `{user_type_safe}`\n"
                f"   Telegram ID: `{telegram_id_safe}`\n"
                f"   🔑 Confirmed Properties: `{property_count}`\n\n"
            )

        # Create pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_users:{current_page - 1}"))
        if end_index < total_users:
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_users:{current_page + 1}"))
        if row:
            buttons.append(row)
        # Add a button to go back to the admin menu or main menu?
        # buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]) # Example

        keyboard = InlineKeyboardMarkup(buttons)

        await send_or_edit(update, response_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during list_users for admin {user_id}: {e}")
        await send_or_edit(update, "Sorry, I couldn't connect to the service right now.")
    except Exception as e:
        logger.error(f"Unexpected error during list_users for admin {user_id}: {e}", exc_info=True)
        await send_or_edit(update, "An unexpected error occurred while fetching users.")


async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin) List pending (unresponded) live agent requests."""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 Access denied. This command is for administrators only.")
        return

    logger.info(f"Admin {user_id} listing pending live agent requests.")

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
        # Use await for the async function get_all_requests
        all_reqs = await get_all_requests()

        if not all_reqs:
             await update.message.reply_text("No live agent requests found at all.")
             return

        # Filter for requests where is_responded is False
        pending_requests = [req for req in all_reqs if not req.get('is_responded', False)] # Safely get is_responded

        if not pending_requests:
            await update.message.reply_text("✅ No pending live agent requests found.")
            return

        message = "📨 *Pending Live Agent Requests*\n\n"
        for req in pending_requests:
            # Escape special characters for MarkdownV2
            # Make sure request_id is treated as string for replacement
            request_id = str(req.get('id', 'N/A')).replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('!', '\\!')
            user_tg_id = str(req.get('user_id', 'N/A')).replace('-', '\\-') # API returns user_id as the telegram id
            name = req.get('name', 'N/A').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('!', '\\!')
            phone = req.get('phone', 'N/A').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('!', '\\!')
            address = req.get('address', 'N/A').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('!', '\\!')
            additional_text = req.get('additional_text', 'None').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('!', '\\!')


            message += (
                f"🆔 *Request ID:* `{request_id}`\n"
                f"👤 *User TG ID:* `{user_tg_id}`\n"
                f"   *Name:* {name}\n"
                f"   *Phone:* {phone}\n"
                f"   *Address:* {address}\n"
                f"💬 *Details:* {additional_text}\n"
                f"👉 Use `/respond {request_id}` to reply\n" # Use backticks for ID in command suggestion
                f"\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\n\n" # Separator
            )

        # Split message if too long
        max_len = 4096
        if len(message) > max_len:
            for i in range(0, len(message), max_len):
                await update.message.reply_text(message[i:i+max_len], parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during list_requests for admin {user_id}: {e}")
        await update.message.reply_text("Sorry, I couldn't connect to the service to fetch requests.")
    except Exception as e:
        logger.error(f"Unexpected error during list_requests for admin {user_id}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while fetching requests.")

# --- Live Agent Conversation Handlers ---

async def live_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to request a live agent (entry point)."""
    telegram_id = str(update.effective_user.id)
    logger.info(f"Live agent request started by user {telegram_id}")

    prompt_message = "Okay, let's connect you with support. First, please provide your full name:"

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Edit the message that had the button
        await query.edit_message_text(prompt_message)
    elif update.message:
         # Reply to the command /live_agent
        await update.message.reply_text(prompt_message)
    else:
        # Should not happen, but good practice to handle
        logger.warning("live_agent handler triggered without callback_query or message.")
        return ConversationHandler.END

    return LIVE_REQUEST # State asking for name

async def live_agent_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input, ask for phone."""
    context.user_data['live_agent_name'] = update.message.text # Use specific keys for this convo
    await update.message.reply_text("Thanks! Please provide your phone number:")
    return LIVE_PHONE

async def live_agent_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone input, ask for address."""
    context.user_data['live_agent_phone'] = update.message.text
    await update.message.reply_text("Got it. Please provide your current address or general location:")
    return LIVE_ADDRESS

async def live_agent_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle address input, ask for additional details."""
    context.user_data['live_agent_address'] = update.message.text
    await update.message.reply_text("Finally, please describe your issue or question briefly:")
    return LIVE_ADDITIONAL_TEXT

async def live_agent_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final details, submit request via API, and end conversation."""
    context.user_data['live_agent_additional_text'] = update.message.text
    user_id = str(update.effective_user.id) # Ensure string
    username = update.effective_user.username or "No username"

    # Retrieve data stored in context.user_data
    name = context.user_data.get('live_agent_name')
    phone = context.user_data.get('live_agent_phone')
    address = context.user_data.get('live_agent_address')
    additional_text = context.user_data.get('live_agent_additional_text')

    if not all([name, phone, address, additional_text]):
         logger.warning(f"Incomplete live agent data for user {user_id}. Data: {context.user_data}")
         await update.message.reply_text("Something went wrong, some information was missing. Please start over with /live_agent or use the menu.")
         # Clean up potentially partial data
         for key in ['live_agent_name', 'live_agent_phone', 'live_agent_address', 'live_agent_additional_text']:
             context.user_data.pop(key, None)
         return ConversationHandler.END

    logger.info(f"Submitting live agent request for user {user_id}: Name={name}, Phone={phone}")

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
        # Use await for the async API call create_request
        request_data = await create_request(
            user_id=user_id,
            username=username,
            name=name,
            phone=phone,
            address=address,
            additional_text=additional_text
        )

        if request_data and request_data.get('id'): # Check if API returned the created request object with an ID
            await update.message.reply_text(
                "✅ Your request has been submitted successfully! "
                "An agent will review it and get back to you via Telegram message soon."
            )

            # Notify the admin(s)
            admin_message = (
                f"📨 *New Live Agent Request Received*\n\n"
                f"*Request ID:* `{request_data.get('id')}`\n" # Show the ID from response
                f"*User TG ID:* `{user_id}`\n"
                f"*Username:* @{username}\n"
                f"*Name:* {name}\n" # Already escaped in create_request? Assume yes for now, or escape here.
                f"*Phone:* {phone}\n"
                f"*Address:* {address}\n\n"
                f"📄 *Details:* {additional_text}\n\n"
                f"👉 Use `/respond {request_data.get('id')}` to reply\\."
            )

            for admin_id in ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as admin_notify_err:
                    logger.error(f"Failed to notify admin {admin_id} about new request {request_data.get('id')}: {admin_notify_err}")

        else:
            await update.message.reply_text("❌ There was an error submitting your request. Please try again later or contact support directly.")
            logger.error(f"Failed to create live agent request via API. Response: {request_data}")

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during live_agent_complete for user {user_id}: {e}")
        await update.message.reply_text("❌ Network error. Could not submit your request.")
    except Exception as e:
        logger.error(f"Unexpected error during live_agent_complete for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An unexpected error occurred. Please try again.")
    finally:
        # Clean up user_data for this conversation
        for key in ['live_agent_name', 'live_agent_phone', 'live_agent_address', 'live_agent_additional_text']:
            context.user_data.pop(key, None)

    return ConversationHandler.END


# --- Admin Response Conversation Handlers ---

async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """(Admin) Start the process to respond to a live agent request (entry point)."""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 Access denied.")
        return ConversationHandler.END

    args = context.args
    if args:
        # User provided ID directly, e.g., /respond 123
        request_id = args[0]
        context.user_data['respond_request_id'] = request_id
        logger.info(f"Admin {user_id} initiated response for request ID {request_id} via args.")
        return await proceed_to_response_message(update, context, request_id) # Skip asking for ID
    else:
        # Ask for the ID
        logger.info(f"Admin {user_id} initiated response command, asking for request ID.")
        await update.message.reply_text("Please enter the *Request ID* you want to respond to (from /requests):", parse_mode=ParseMode.MARKDOWN)
        return RESPOND_TO_REQUEST

async def respond_request_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """(Admin) Handle the request ID input and proceed."""
    request_id = update.message.text.strip()
    if not request_id.isdigit():
        await update.message.reply_text("Invalid Request ID format. Please enter a number.")
        # Optionally, re-prompt or end
        return ConversationHandler.END # End here for simplicity

    context.user_data['respond_request_id'] = request_id
    admin_id = update.effective_user.id
    logger.info(f"Admin {admin_id} entered request ID {request_id} for response.")
    return await proceed_to_response_message(update, context, request_id)

async def proceed_to_response_message(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: str) -> int:
    """(Admin) Helper to fetch request details and ask for response message."""
    admin_id = update.effective_user.id
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function get_request_details
        request_details = await get_request_details(request_id)

        if request_details and request_details.get('user_id'):
            user_tg_id_to_respond = request_details['user_id'] # This is the user's Telegram ID
            context.user_data['respond_user_tg_id'] = user_tg_id_to_respond # Store user's TG ID
            name = request_details.get('name', 'the user')
            # Maybe show the original query?
            original_text = request_details.get('additional_text', '')
            await update.message.reply_text(
                f"Responding to Request ID `{request_id}` from *{name}* (TG ID: `{user_tg_id_to_respond}`)\n"
                f"Original query: \"_{original_text}_\"\n\n"
                f"Please enter your response message now:",
                 parse_mode=ParseMode.MARKDOWN_V2 # Use V2 for consistency
            )
            return RESPONSE_MESSAGE
        else:
            await update.message.reply_text(f"❌ Could not find details for Request ID `{request_id}`. Was it entered correctly? Check `/requests`.")
            logger.warning(f"Admin {admin_id} tried to respond to non-existent/invalid request ID {request_id}. API response: {request_details}")
            # Clean up context
            context.user_data.pop('respond_request_id', None)
            return ConversationHandler.END

    except aiohttp.ClientError as e:
        logger.error(f"API connection error fetching details for request {request_id} (Admin {admin_id}): {e}")
        await update.message.reply_text("❌ Network error. Could not fetch request details.")
        context.user_data.pop('respond_request_id', None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected error fetching details for request {request_id} (Admin {admin_id}): {e}", exc_info=True)
        await update.message.reply_text("❌ An unexpected error occurred.")
        context.user_data.pop('respond_request_id', None)
        return ConversationHandler.END

async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """(Admin) Handle the response message, send it via API and directly to the user."""
    response_message = update.message.text
    request_id = context.user_data.get('respond_request_id')
    user_tg_id_to_respond = context.user_data.get('respond_user_tg_id')
    admin_id = str(update.effective_user.id) # Sender is the admin

    if not request_id or not user_tg_id_to_respond:
        logger.error(f"Missing request_id or user_tg_id in context for admin {admin_id}. Context: {context.user_data}")
        await update.message.reply_text("❌ Error: Missing context information. Cannot send response. Please start over.")
        return ConversationHandler.END

    logger.info(f"Admin {admin_id} sending response for request {request_id} to user {user_tg_id_to_respond}.")

    message_sent_to_api = False
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Use await for the async function create_message
        # Note: API needs request_id, sender_id (admin), recipient_user_id (user), content
        message_api_response = await create_message(
            request_id=request_id,
            sender_id=admin_id,       # Admin sending
            user_id=user_tg_id_to_respond, # User receiving
            content=response_message
        )

        if message_api_response and message_api_response.get('id'):
             logger.info(f"Response message recorded in API for request {request_id}. Message ID: {message_api_response.get('id')}")
             message_sent_to_api = True
             # Optionally update the request status to 'responded' via another API call if needed
             # Example: await update_request_status(request_id, is_responded=True)
        else:
            logger.error(f"Failed to record response message in API for request {request_id}. Response: {message_api_response}")
            # Decide if we should still try to send to user directly

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during send_response for request {request_id} (Admin {admin_id}): {e}")
        await update.message.reply_text("❌ Network error. Failed to record message in API. Trying to send directly...")
    except Exception as e:
        logger.error(f"Unexpected error recording response in API for request {request_id} (Admin {admin_id}): {e}", exc_info=True)
        await update.message.reply_text("❌ Error recording message in API. Trying to send directly...")

    # Try sending the message directly to the user via Telegram, regardless of API success (maybe?)
    try:
        await context.bot.send_message(
            chat_id=user_tg_id_to_respond,
            text=f"ℹ️ Response regarding your support request (ID: {request_id}):\n\n{response_message}"
        )
        # Confirm to admin
        await update.message.reply_text(f"✅ Message sent successfully to user {user_tg_id_to_respond} (Request ID: {request_id}).")
        if not message_sent_to_api:
             await update.message.reply_text("⚠️ *Warning:* Failed to record this message in the API history.", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Failed to send response message directly to user {user_tg_id_to_respond} for request {request_id}: {e}")
        await update.message.reply_text(
            f"❌ *Failed* to send message directly to user {user_tg_id_to_respond} on Telegram.\n"
            f"Error: {e}\n"
            f"Please check the user ID or contact them manually.",
            parse_mode=ParseMode.MARKDOWN
            )
        # Log API status as well
        if message_sent_to_api:
             await update.message.reply_text("ℹ️ Note: The message *was* recorded in the API history.")
        else:
             await update.message.reply_text("⚠️ *Warning:* The message was *not* recorded in the API history either.")


    # Clean up context
    context.user_data.pop('respond_request_id', None)
    context.user_data.pop('respond_user_tg_id', None)

    return ConversationHandler.END

# --- General Message Handling ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages that are not commands or part of other conversations."""
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    # Ignore admins in this handler, they use commands
    if int(user_id) in ADMINS:
        # Maybe provide a hint?
        # await update.message.reply_text("Admin commands: /requests, /respond <id>, /list_users")
        return

    logger.info(f"Received general message from user {user_id}.")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # Check if there's an ongoing conversation context with an admin (based on existing messages)
        # Use await for the async function get_all_messages
        all_messages = await get_all_messages() # Fetch all messages (potentially inefficient, needs filtering in API ideally)

        # Find the LATEST request associated with this user that has messages
        # This logic might need refinement based on how `live.api.get_all_messages` works
        # and how requests/conversations are tracked.
        # Let's assume `get_all_messages` can be filtered by user_id or we filter here.
        user_related_messages = [msg for msg in all_messages if str(msg.get('user_id')) == user_id]

        # Find the request ID associated with the most recent message thread for this user
        # This assumes messages are sorted by timestamp descending or we sort them
        user_related_messages.sort(key=lambda x: x.get('timestamp', 0), reverse=True) # Requires timestamp field

        active_request_id = None
        admin_responder_id = None
        if user_related_messages:
            latest_message = user_related_messages[0]
            active_request_id = latest_message.get('request') # Assumes message object links to request ID
            # Find the admin involved in this request thread (sender_id != user_id)
            admin_message_in_thread = next((msg for msg in user_related_messages if str(msg.get('sender_id')) != user_id and msg.get('request') == active_request_id), None)
            if admin_message_in_thread:
                admin_responder_id = admin_message_in_thread.get('sender_id')
            else:
                 # If no admin message yet, maybe notify all admins? Or a default one?
                 # For now, let's use the first admin as a fallback if no specific one found
                 admin_responder_id = str(ADMINS[0]) if ADMINS else None


        if active_request_id and admin_responder_id:
            logger.info(f"User {user_id} message relates to active request {active_request_id}. Forwarding to admin {admin_responder_id}.")
            # Record the message using the API
            # Use await for the async function create_message
            await create_message(
                request_id=active_request_id,
                sender_id=user_id, # User is sending
                user_id=user_id,   # Belongs to this user's request context
                content=user_message
            )

            # Forward the message content to the relevant admin
            try:
                await context.bot.send_message(
                    chat_id=admin_responder_id,
                    text=(
                        f"💬 New message from user {user_id} regarding Request ID: `{active_request_id}`\n"
                        f"(Username: @{update.effective_user.username or 'N/A'})\n\n"
                        f"{user_message}\n\n"
                        f"👉 Use `/respond {active_request_id}` to reply."
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2 # Use V2
                )
                await update.message.reply_text("✅ Your message has been sent to the support agent.")
            except Exception as forward_err:
                logger.error(f"Failed to forward message from {user_id} to admin {admin_responder_id}: {forward_err}")
                await update.message.reply_text("⚠️ Your message was recorded, but there was an issue notifying the agent immediately. They will see it later.")

        else:
            logger.info(f"User {user_id} sent a message, but no active support request found. Prompting to start.")
            await update.message.reply_text(
                "Thanks for your message! If you need support, please use the 'Live Agent' button or /live_agent to start a new request.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Request Live Agent", callback_data="live_agent")]])
                )

    except aiohttp.ClientError as e:
        logger.error(f"API connection error during handle_message for user {user_id}: {e}")
        await update.message.reply_text("Sorry, I'm having trouble connecting to the support system right now.")
    except Exception as e:
        logger.error(f"Unexpected error during handle_message for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while processing your message.")

# --- Language Handlers ---

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /changelang command or callback to show language options."""
    # Using ReplyKeyboardMarkup for simplicity as requested in original code
    keyboard = [[lang] for lang in LANGUAGES] # One button per row
    keyboard.append(["/cancel"]) # Add cancel option
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    message_text = "Please choose your preferred language:"

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Send a new message with the ReplyKeyboard, cannot edit to add ReplyKeyboard easily
        await query.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    # This is not part of a conversation state machine in this setup

async def handle_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's language selection from ReplyKeyboard."""
    user_choice = update.message.text

    if user_choice in LANGUAGES:
        # Here you would typically store the user's preference, e.g., in context.user_data
        context.user_data['language'] = user_choice
        logger.info(f"User {update.effective_user.id} chose language: {user_choice}")
        # Confirm selection and remove the keyboard
        await update.message.reply_text(
            f"✅ Language set to {user_choice}.", reply_markup=ReplyKeyboardRemove()
        )
        # You might want to show the main menu again here
        await update.message.reply_text("Here are your options:", reply_markup=get_main_menu())

    elif user_choice == "/cancel":
        await update.message.reply_text("Language selection cancelled.", reply_markup=ReplyKeyboardRemove())

    # No else needed: if it wasn't a language or cancel, the general handle_message might catch it,
    # or if using filters, it won't trigger this handler. We added filters below.


# --- Main Menu Callback Handler ---

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callbacks from the main inline keyboard."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    logger.info(f"Main menu callback: User {user_id} clicked '{data}'")

    # Simple router based on callback data
    if data == "add_property":
        await addproperty(update, context)
    elif data == "upgrade_account":
        await upgrade(update, context)
    elif data == "view_profile":
        await profile(update, context)
    elif data.startswith("list_properties"): # Handles "list_properties:1" etc.
        await list_properties(update, context)
    elif data.startswith("list_favorites"): # Handles "list_favorites:1" etc.
        await list_favorites(update, context)
    elif data.startswith("list_tours"): # Handles "list_tours:1" etc.
        await list_tours(update, context)
    elif data == "live_agent":
        # Need to start the live agent conversation
        # We'll trigger the entry point handler manually - slightly hacky but works
        await live_agent(update, context) # Directly call the async function
        # Important: Because live_agent is an entry point to a ConversationHandler,
        # calling it directly like this doesn't automatically enter the conversation state.
        # A better approach is needed if mixing callbacks and ConversationHandler entry points.
        # For now, let's just show the initial prompt but not enter the state machine.
        # A cleaner way: make live_agent command ONLY the entry point, and the button sends the command text?
        # Or have the callback *send* the /live_agent command to the bot (complex).
        # --> Let's adjust: live_agent button directly starts the conversation.
        # --> This requires adding CallbackQueryHandler(live_agent, pattern='^live_agent$') to entry_points.
        # --> See `setup_application` function.
        pass # The ConversationHandler entry point will handle this if set up correctly
    elif data == "change_language":
        await change_language(update, context)
    elif data == "main_menu": # Handle "Back to Main Menu" button
        await query.edit_message_text("Here are your options:", reply_markup=get_main_menu())

    # Handle pagination callbacks delegated from list commands if not handled by specific handlers already
    # (Our specific list handlers already handle their pagination callbacks)
    elif data.startswith("list_users"): # Example if list_users was triggered by callback
        await list_users(update, context)

    # Handle favorite button clicks separately if they use a different pattern
    elif data.startswith("make_favorite_"):
        await handle_favorite_request(update, context)

    else:
        logger.warning(f"Unhandled main menu callback data: {data}")
        try:
            await query.edit_message_text("Sorry, that action is not recognized or implemented yet.")
        except Exception as e:
            logger.error(f"Error trying to edit message for unhandled callback {data}: {e}")


    
async def bot_tele(text):
    application = Application.builder().token(os.getenv('TOKEN')).persistence(persistence).build()

    tour_request_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^/request_tour_(\d+)$'), request_tour),
            CommandHandler("start", start),
            CallbackQueryHandler(handle_main_menu)
            
        ],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone_number)],
            TOUR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tour_date)],
            TOUR_TIME: [CallbackQueryHandler(get_tour_time)]  # Handle callbacks for tour time
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.COMMAND, fallback)],
        persistent=True,
        name="tour_request_handler"
    )
    
    # Define the conversation handler for live agent request
    live_agent_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("live_agent", live_agent)],
    states={
        LIVE_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_name)],
        LIVE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_phone)],
        LIVE_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_address)],
        LIVE_ADDITIONAL_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_complete)],
    },
    fallbacks=[CommandHandler("leave", leave)],
    persistent=True,  # Ensure persistence is enabled
    name="live_agent_conversation",
    conversation_timeout=300  # Optional: Set a timeout for conversations
)

    application.add_handler(live_agent_conv_handler)
    
    # Conversation handler for responding to a user's request
    respond_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("respond", respond)],
        states={
            RESPOND_TO_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, respond_request_id)],
            RESPONSE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_response)],
        },
        fallbacks=[CommandHandler("leave", leave)],
        persistent=True,
    name="user_request_conversation",
    )
    
    # Add the respond conversation handler
    application.add_handler(respond_conv_handler)


    application.add_handler(tour_request_handler)
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("addproperty", addproperty))
    application.add_handler(CommandHandler("upgrade", upgrade))
    application.add_handler(CommandHandler("list_properties", list_properties))
    application.add_handler(CommandHandler("requests", list_requests))
    application.add_handler(CommandHandler("list_tours", list_tours))
    application.add_handler(CommandHandler("list_favorites", list_favorites))
    application.add_handler(CallbackQueryHandler(handle_favorite_request))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_choice))
    application.add_handler(CommandHandler("changelang", change_language))



    webhook_url = os.getenv('webhook')
    await application.bot.set_webhook(url=webhook_url)

    await application.update_queue.put(
        Update.de_json(data=text, bot=application.bot)
    )

    async with application:
        await application.start()
        await application.stop()

    logger.info("Bot has started and stopped successfully.")
