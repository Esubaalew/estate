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
import aiohttp # <--- Import aiohttp instead of requests

# --- Assuming state.tools and live.api are now async ---
from state.tools import (
    register_user, is_user_registered, get_user_details,
    get_user_properties, get_user_tours, get_property_details,
    get_user_favorites, get_non_user_accounts, get_confirmed_user_properties
)
from live.api import (
    create_message, get_all_requests, get_request_details,
    get_all_messages, create_request
)

# Set up logging (Original)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
API_BASE_URL = "https://estate-r22a.onrender.com" # <--- CHANGED DOMAIN
BOT_TOKEN = os.getenv('TOKEN') # Defined for setup if needed

# Initialize persistence (Original)
persistence = PicklePersistence(filepath='bot_dat')
PAGE_SIZE = 2

# --- State Definitions --- CORRECTED RANGES
FULL_NAME, PHONE_NUMBER, TOUR_DATE, TOUR_TIME = range(4) # States 0, 1, 2, 3
# Original: LIVE_REQUEST, LIVE_PHONE, LIVE_ADDRESS, LIVE_ADDITIONAL_TEXT = range(3, 7) <--- COLLISION
LIVE_REQUEST, LIVE_PHONE, LIVE_ADDRESS, LIVE_ADDITIONAL_TEXT = range(4, 8) # States 4, 5, 6, 7 <-- CORRECTED
# Original: RESPOND_TO_REQUEST, RESPONSE_MESSAGE = range(2) <--- COLLISION
RESPOND_TO_REQUEST, RESPONSE_MESSAGE = range(8, 10) # States 8, 9 <-- CORRECTED

ADMINS = [1648265210]
LANGUAGES = ["Amharic", "English"] # Added definition based on usage

# --- Bot Functions --- (Applying async await)

# --- ASYNC CHANGE: Added async keyword ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None: # Added return hint
    """Start command with optional deep-linking for tour requests."""
    telegram_id = str(update.message.from_user.id)
    full_name = update.message.from_user.full_name
    username = update.message.from_user.username or "" # Original default logic

    context.user_data['telegram_id'] = telegram_id
    context.user_data['username'] = username

    args = context.args
    if args and args[0].startswith("request_tour_"):
        try: # Added try-except for safety
            property_id = args[0].split("_")[2]
            context.user_data['property_id'] = property_id
            await update.message.reply_text("Please provide your full name to start scheduling the tour.")
            return FULL_NAME # Original return
        except (IndexError, ValueError):
             await update.message.reply_text("Invalid tour request link format.")
             return ConversationHandler.END # Needs to end conversation

    # --- ASYNC CHANGE: Added await ---
    if await is_user_registered(telegram_id):
        # --- ASYNC CHANGE: Added await ---
        user_details = await get_user_details(telegram_id)
        if user_details:
            profile_token = user_details.get("profile_token") # Original variable
            await update.message.reply_text(f"Welcome back, {full_name}! Here are some quick options:", reply_markup=get_main_menu())
        else:
            await update.message.reply_text("Could not retrieve your details. Please try again later.")
    else:
        # --- ASYNC CHANGE: Added await ---
        result = await register_user(telegram_id, full_name, username) # Pass username
        # Original check (ensure result is dict)
        if isinstance(result, dict) and "message" in result:
             await update.message.reply_text(result["message"])
             await update.message.reply_text("You’re registered! Here are some quick options:", reply_markup=get_main_menu())
        else:
             logger.error(f"Registration result invalid: {result}")
             await update.message.reply_text("Registration failed.") # Simplified error

    # Return END if not entering conversation state
    if not (args and args[0].startswith("request_tour_")):
        return ConversationHandler.END


def get_main_menu():
    """Generate the main menu inline keyboard with descriptive emojis."""
    # Original buttons
    buttons = [
        [InlineKeyboardButton("➕ Add Property 🏡", callback_data="add_property")],
        [InlineKeyboardButton("✨ Upgrade Account ⭐", callback_data="upgrade_account")],
        [InlineKeyboardButton("👤 View Profile 🔍", callback_data="view_profile")],
        [InlineKeyboardButton("📋 List Properties 📂", callback_data="list_properties")], # Original callback
        [InlineKeyboardButton("❤️ List Favorites 💾", callback_data="list_favorites")], # Original callback
        [InlineKeyboardButton("📅 List Tours 🗓️", callback_data="list_tours")],       # Original callback
        [InlineKeyboardButton("💬 Live Agent 📞", callback_data="live_agent")],
        [InlineKeyboardButton("🌐 Change Language 🌍", callback_data="change_language")],
    ]

    # Original arrangement
    formatted_buttons = []
    for i in range(0, len(buttons) - 1, 2):
        formatted_buttons.append(buttons[i] + buttons[i + 1])
    if len(buttons) % 2 == 1:
        formatted_buttons.append(buttons[-1])

    return InlineKeyboardMarkup(formatted_buttons)

# --- ASYNC CHANGE: Added async keyword ---
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Profile command to handle user profile viewing and editing."""
    # Original source check
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    # Original log
    logger.info(f"Profile command triggered for user {telegram_id}")
    # --- ASYNC CHANGE: Added await ---
    user_details = await get_user_details(telegram_id)

    # Original check
    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)
        return

    # Original link generation
    profile_token = user_details.get("profile_token")
    # Use bot username dynamically as it's needed for the URL
    bot_username = context.bot.username or "yene_etbot" # Fallback if needed
    web_app_url = f"https://t.me/{bot_username}/state?startapp=edit-{profile_token}" # Keep original structure
    message = "You can edit your profile using the following link (click to open):"
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Edit Profile", url=web_app_url)]]
    )

    # Original send logic
    if update.callback_query: await query.edit_message_text(message, reply_markup=reply_markup)
    else: await update.message.reply_text(message, reply_markup=reply_markup)

# --- ASYNC CHANGE: Added async keyword ---
async def addproperty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add property command to check if the user can add properties."""
    # Original source check
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    # Original log
    logger.info(f"addproperty triggered for user {telegram_id}")
    # --- ASYNC CHANGE: Added await ---
    user_details = await get_user_details(telegram_id)

    # Original check
    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)
        return

    # Original user type and link generation
    user_type = user_details.get("user_type")
    profile_token = user_details.get("profile_token")

    if user_type == 'user':
        message = (
            "You can only browse or inquire about properties. To add your own property, "
            "please upgrade your account by using /upgrade and choosing the Agent or Company option."
        )
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)

    elif user_type in ['agent', 'owner', 'company']: # Keep original types check + company
        bot_username = context.bot.username or "yene_etbot"
        # Original URL structure (might point to edit instead of add?)
        web_app_url = f"https://t.me/{bot_username}/state?startapp=edit-{profile_token}"
        message = "You have permission to add properties! Use the following link to proceed:"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Add Property", url=web_app_url)]]
        )
        if update.callback_query: await query.edit_message_text(message, reply_markup=reply_markup)
        else: await update.message.reply_text(message, reply_markup=reply_markup)

    else:
        message = "User type not recognized. Please contact support for assistance."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)

# --- ASYNC CHANGE: Added async keyword ---
async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upgrade account command to handle user upgrades and profile management."""
    # Original source check
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    # Original log
    logger.info(f"Upgrade triggered for user {telegram_id}")
    # --- ASYNC CHANGE: Added await ---
    user_details = await get_user_details(telegram_id)

    # Original checks
    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)
        return

    user_type = user_details.get("user_type")
    profile_token = user_details.get("profile_token")

    if user_type in ['agent', 'owner', 'company']: # Keep original types + company
        message = "You are already upgraded to your current account type. Use /profile to manage your account."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)

    elif user_type == 'user':
        bot_username = context.bot.username or "yene_etbot"
        web_app_url = f"https://t.me/{bot_username}/state?startapp=edit-{profile_token}" # Original URL
        message = "Account upgrades are irreversible. To upgrade your account, please visit your profile:"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Edit Profile", url=web_app_url)]]
        )
        if update.callback_query: await query.edit_message_text(message, reply_markup=reply_markup)
        else: await update.message.reply_text(message, reply_markup=reply_markup)

    else:
        message = "User type not recognized. Please contact support for assistance."
        if update.callback_query: await query.edit_message_text(message)
        else: await update.message.reply_text(message)


# --- ASYNC CHANGE: Added async keyword ---
async def request_tour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Original parsing
    command_parts = update.message.text.split("_")

    # Original check adjusted slightly for index safety
    if len(command_parts) < 3 or not command_parts[2].isdigit():
        await update.message.reply_text("Please specify the property ID with the command, like this: /request_tour_<property_id>")
        return ConversationHandler.END

    property_id = command_parts[2] # ID is 3rd part
    context.user_data['property_id'] = property_id
    # Store user info from context
    context.user_data['telegram_id'] = str(update.effective_user.id)
    context.user_data['username'] = update.effective_user.username or ""

    await update.message.reply_text("Please provide your full name.")
    return FULL_NAME # Original return

# --- ASYNC CHANGE: Added async keyword ---
async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Thanks! Now, please provide your phone number.")
    return PHONE_NUMBER # Original return

# --- ASYNC CHANGE: Added async keyword ---
async def get_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['phone_number'] = update.message.text
    # Original keyboard
    days_keyboard = [
        [KeyboardButton("Monday"), KeyboardButton("Tuesday")],
        [KeyboardButton("Wednesday"), KeyboardButton("Thursday")],
        [KeyboardButton("Friday"), KeyboardButton("Saturday")],
        [KeyboardButton("Sunday")]
    ]
    await update.message.reply_text(
        "Great! Please select a date (day of the week) for your tour.",
        reply_markup=ReplyKeyboardMarkup(days_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return TOUR_DATE # Original return

# --- ASYNC CHANGE: Added async keyword ---
async def get_tour_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tour_date = update.message.text
    # Original validation
    if tour_date not in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        await update.message.reply_text("Invalid selection. Please select a valid day of the week.")
        # Re-show keyboard for invalid choice
        days_keyboard = [
            [KeyboardButton("Monday"), KeyboardButton("Tuesday")],
            [KeyboardButton("Wednesday"), KeyboardButton("Thursday")],
            [KeyboardButton("Friday"), KeyboardButton("Saturday")],
            [KeyboardButton("Sunday")]
        ]
        await update.message.reply_text( # Added prompt
            "Please select a date (day of the week) for your tour.",
            reply_markup=ReplyKeyboardMarkup(days_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return TOUR_DATE # Stay in state

    context.user_data['tour_date'] = tour_date
    await update.message.reply_text("Thank you! Now, please select a time for the tour.", reply_markup=ReplyKeyboardRemove())
    # Original time buttons
    time_buttons = [
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(6, 11)]
    ]
    await update.message.reply_text(
        "Finally, at what time (1-10) would you like to schedule the tour?",
        reply_markup=InlineKeyboardMarkup(time_buttons)
    )
    return TOUR_TIME # Original return

# --- ASYNC CHANGE: Added async keyword ---
async def get_tour_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query # Need query object
    await query.answer()  # Acknowledge the callback

    tour_time_str = query.data # Original data
    try:
        # Original validation
        tour_time_int = int(tour_time_str)
        if not 1 <= tour_time_int <= 10:
            raise ValueError
        context.user_data['tour_time'] = tour_time_int # Store integer
    except ValueError:
        # Original error message via answer()
        await query.answer("Invalid time. Please select a valid time from the options provided.", show_alert=True)
        return TOUR_TIME # Stay in state

    # --- ASYNC CHANGE: Call async version ---
    success = await register_tour_details_async(context.user_data) # Use the async version

    if success:
        await query.edit_message_text("Your tour request has been submitted!") # Original success message
    else:
        await query.edit_message_text("Failed to submit tour request.") # Simplified error

    return ConversationHandler.END # Original return

# --- ASYNC CHANGE: Made function async and use aiohttp ---
async def register_tour_details_async(user_data: dict) -> bool: # Renamed from original register_tour_details
    """Async version to register tour details"""
    telegram_id = str(user_data.get('telegram_id'))
    username = user_data.get('username', '')

    # Original data extraction
    data = {
        "property": user_data.get('property_id'), # Use get for safety
        "full_name": user_data.get('full_name'),
        "phone_number": user_data.get('phone_number'),
        "tour_date": user_data.get('tour_date'),
        "tour_time": user_data.get('tour_time'), # The integer 1-10
        "telegram_id": telegram_id,
        "username": username
    }
    # Basic check for essential data
    if not all(data.get(k) for k in ["property", "full_name", "phone_number", "tour_date", "tour_time", "telegram_id"]):
        logger.error(f"Missing data for tour registration: {data}")
        return False

    api_url = f"{API_BASE_URL}/api/tours/" # Use BASE URL
    try:
        # Use aiohttp session
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=data) as response:
                # Original didn't check status, just raised. Check status now.
                if response.status >= 200 and response.status < 300:
                    logger.info(f"Tour registered successfully via API. Status: {response.status}")
                    return True
                else:
                    # Log API error response
                    response_text = await response.text()
                    logger.error(f"Failed to submit tour request. Status: {response.status}, Response: {response_text}")
                    return False
    # Keep original error logging style
    except aiohttp.ClientError as e: # Catch async HTTP errors
        logger.error(f"HTTP Client Error submitting tour request: {e}")
        # Original didn't check if response object existed before logging
        # if response: logger.error(f"Response content: {response.text}") # Cannot access response here
        return False
    except Exception as e: # Catch other errors
         logger.error(f"Unexpected error in register_tour_details_async: {e}", exc_info=True)
         return False

# --- ASYNC CHANGE: Added async keyword and use aiohttp ---
async def handle_favorite_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query # Get query object
    await query.answer()
    data = query.data

    if data.startswith("make_favorite_"):
        try: # Added safety parse
            property_id = int(data.split("_")[2])
        except (IndexError, ValueError):
            logger.error(f"Bad favorite callback data: {data}")
            return

        telegram_id = str(query.from_user.id)

        try:
            # --- ASYNC CHANGE: Added await ---
            favorites = await get_user_favorites(telegram_id) or [] # Ensure list
            # --- ASYNC CHANGE: Added await ---
            property_details = await get_property_details(property_id)
            property_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'

            # Original check logic
            favorite_id = None
            for favorite in favorites:
                if favorite.get('property') == property_id: # Use get for safety
                    favorite_id = favorite.get('id') # Retrieve the favorite model ID
                    break

            async with aiohttp.ClientSession() as session:
                # Original delete logic
                if favorite_id:
                    delete_url = f"{API_BASE_URL}/api/favorites/{favorite_id}/" # Use BASE URL
                    try:
                        async with session.delete(delete_url) as response:
                            # Check status instead of relying on raise_for_status
                            if response.status == 204: # No Content
                                await context.bot.send_message(
                                    chat_id=telegram_id,
                                    text=f"❌ The property *{property_name}* has been removed from your favorites.",
                                    parse_mode=ParseMode.MARKDOWN # Original mode
                                )
                            else:
                                raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status, message=await response.text())
                    # Keep original error handling structure
                    except aiohttp.ClientError as e: # Catch async HTTP errors
                        logger.error(f"Failed to remove property from favorites: {e}")
                        # Original didn't check response obj
                        await context.bot.send_message(chat_id=telegram_id, text="❌ Failed to remove from favorites. Please try again later.")

                # Original add logic
                else:
                    post_url = f"{API_BASE_URL}/api/favorites/" # Use BASE URL
                    payload = {"property": property_id, "customer": telegram_id} # Original payload
                    try:
                        async with session.post(post_url, json=payload) as response:
                            # Check status
                            if response.status >= 200 and response.status < 300: # e.g. 201 Created
                                await context.bot.send_message(
                                    chat_id=telegram_id,
                                    text=f"❤️ The property *{property_name}* has been added to your favorites!",
                                    parse_mode=ParseMode.MARKDOWN # Original mode
                                )
                            else:
                                raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status, message=await response.text())
                    # Keep original error handling structure
                    except aiohttp.ClientError as e: # Catch async HTTP errors
                        logger.error(f"Failed to add property to favorites: {e}")
                        # Original didn't check response obj
                        await context.bot.send_message(chat_id=telegram_id, text="❌ Failed to add to favorites. Please try again later.")

        except aiohttp.ClientError as e: # Catch errors from get_user_favorites/get_property_details
            logger.error(f"API Error during favorite handling for {telegram_id}: {e}")
            await context.bot.send_message(chat_id=telegram_id, text="❌ Error updating favorites (connection).")
        except Exception as e: # Catch other errors
             logger.error(f"Unexpected error during favorite handling for {telegram_id}: {e}", exc_info=True)
             await context.bot.send_message(chat_id=telegram_id, text="❌ An unexpected error occurred.")


# --- ASYNC CHANGE: Added async keyword ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Original
    await update.message.reply_text("The tour scheduling process has been canceled. Use /start to begin again.", reply_markup=ReplyKeyboardRemove())
    # Clean context data associated with tour convo
    for key in ['property_id', 'full_name', 'phone_number', 'tour_date', 'tour_time']:
        context.user_data.pop(key, None)
    return ConversationHandler.END

# --- ASYNC CHANGE: Added async keyword ---
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # Added return hint
    """Cancels and ends the conversation."""
    # Original
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    # Clean context data associated with live/respond convo
    for key in ['name', 'phone', 'address', 'additional_text', 'request_id', 'user_id',
                'live_agent_name','live_agent_phone','live_agent_address','live_agent_additional_text',
                'respond_request_id','respond_user_id']:
        context.user_data.pop(key, None)
    return ConversationHandler.END

# --- ASYNC CHANGE: Added async keyword ---
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Original
    await update.message.reply_text("Please follow the instructions or use /cancel or /leave to exit.") # Added /leave

# --- ASYNC CHANGE: Added async keyword ---
async def list_properties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List properties associated with the user with pagination."""
    # Original source check and page logic
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        # Original callback parsing had ":", assume this remains
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    # Original log
    logger.info(f"List properties triggered for user {telegram_id} on page {current_page}")

    try: # Added basic try block
        # --- ASYNC CHANGE: Added await ---
        properties = await get_user_properties(telegram_id) or [] # Ensure list

        # Original check
        if not properties:
            message = "🏡 You don't have any properties listed yet! Use /addproperty to add one."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original pagination
        total_properties = len(properties) # Need total count before pagination
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_properties = properties[start_index:end_index]

        # Handle page number issues
        if not paginated_properties and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_properties = properties[start_index:end_index]

        if not paginated_properties: # If still empty
            message = f"No properties found on page {current_page}."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return


        # Original response text
        response_text = f"📝 Here are your properties (Page {current_page}):\n\n" # Add page num
        for i, prop in enumerate(paginated_properties, start=start_index + 1):
            # Basic Markdown escape
            prop_name = prop.get('name','N/A').replace("*","\\*").replace("_","\\_")
            prop_status = prop.get('status','N/A').replace("*","\\*").replace("_","\\_")
            response_text += f"{i}. 📍 *{prop_name}* - Status: *{prop_status}*\n"

        # Original pagination buttons
        buttons = []
        row = [] # Create row list
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_properties:{current_page - 1}"))
        if end_index < total_properties: # Use total_properties here
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_properties:{current_page + 1}"))
        if row: buttons.append(row) # Add row only if it has buttons
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        # Original send logic
        if update.callback_query:
            await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: # Basic catch-all
         logger.error(f"Error in list_properties for {telegram_id}: {e}", exc_info=True)
         err_msg = "Error fetching properties."
         if update.callback_query: await query.edit_message_text(err_msg)
         else: await update.message.reply_text(err_msg)


# --- ASYNC CHANGE: Added async keyword ---
async def list_tours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List tours associated with the user with pagination."""
    # Original source check and page logic
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    # Original log
    logger.info(f"List tours triggered for user {telegram_id} on page {current_page}")

    try: # Added basic try block
        # --- ASYNC CHANGE: Added await ---
        tours = await get_user_tours(telegram_id) or [] # Ensure list

        # Original check
        if not tours:
            message = "🚶‍♂️ You have no scheduled tours yet! Use /request_tour_<property_id> to schedule one."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original pagination
        total_tours = len(tours) # Need total count
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_tours = tours[start_index:end_index]

        if not paginated_tours and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_tours = tours[start_index:end_index]

        if not paginated_tours: # If still empty
            message = f"No tours found on page {current_page}."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original response text
        response_text = f"📅 Here are your scheduled tours (Page {current_page}):\n\n" # Add page num
        for i, tour in enumerate(paginated_tours, start=start_index + 1):
            prop_name = "Loading..." # Default while fetching
            try:
                # --- ASYNC CHANGE: Added await ---
                property_details = await get_property_details(tour.get('property')) # Safe get ID
                prop_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'
            except Exception as detail_err:
                 logger.error(f"Error fetching property details in list_tours: {detail_err}")
                 prop_name = "Error"

            # Basic Markdown escape
            prop_name_safe = prop_name.replace("*","\\*").replace("_","\\_")
            tour_date_safe = tour.get('tour_date','N/A').replace("*","\\*").replace("_","\\_")
            tour_time_safe = str(tour.get('tour_time','N/A')).replace("*","\\*").replace("_","\\_") # Ensure string

            response_text += f"{i}. 🏡 Property: *{prop_name_safe}* - Date: *{tour_date_safe}* - Time: *{tour_time_safe}*\n"

        # Original pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_tours:{current_page - 1}"))
        if end_index < total_tours: # Use total_tours
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_tours:{current_page + 1}"))
        if row: buttons.append(row)
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        # Original send logic
        if update.callback_query:
            await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: # Basic catch-all
         logger.error(f"Error in list_tours for {telegram_id}: {e}", exc_info=True)
         err_msg = "Error fetching tours."
         if update.callback_query: await query.edit_message_text(err_msg)
         else: await update.message.reply_text(err_msg)


# --- ASYNC CHANGE: Added async keyword ---
async def list_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List favorite properties associated with the user with pagination."""
    # Original source check and page logic
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    # Original log
    logger.info(f"List favorites triggered for user {telegram_id} on page {current_page}")

    try: # Added basic try block
        # --- ASYNC CHANGE: Added await ---
        favorites = await get_user_favorites(telegram_id) or [] # Ensure list

        # Original check
        if not favorites:
            message = "❤️ You have no favorite properties yet! Use the ❤️ button to add some."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original pagination
        total_favorites = len(favorites) # Need total count
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_favorites = favorites[start_index:end_index]

        if not paginated_favorites and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_favorites = favorites[start_index:end_index]

        if not paginated_favorites: # If still empty
            message = f"No favorites found on page {current_page}."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original response text
        response_text = f"🌟 Your Favorite Properties (Page {current_page}):\n\n" # Add page num
        for i, favorite in enumerate(paginated_favorites, start=start_index + 1):
            prop_name = "Loading..." # Default
            try:
                # --- ASYNC CHANGE: Added await ---
                property_details = await get_property_details(favorite.get('property')) # Safe get ID
                prop_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'
            except Exception as detail_err:
                 logger.error(f"Error fetching property details in list_favorites: {detail_err}")
                 prop_name = "Error"

            prop_name_safe = prop_name.replace("*","\\*").replace("_","\\_") # Basic escape
            response_text += f"{i}. 🏡 Property: *{prop_name_safe}*\n"

        # Original pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_favorites:{current_page - 1}"))
        if end_index < total_favorites: # Use total_favorites
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_favorites:{current_page + 1}"))
        if row: buttons.append(row)
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        # Original send logic
        if update.callback_query:
            await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: # Basic catch-all
         logger.error(f"Error in list_favorites for {telegram_id}: {e}", exc_info=True)
         err_msg = "Error fetching favorites."
         if update.callback_query: await query.edit_message_text(err_msg)
         else: await update.message.reply_text(err_msg)


# --- ASYNC CHANGE: Added async keyword ---
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all registered users with pagination."""
    # Original source check and page logic (Admin check needed)
    requesting_user_id = update.effective_user.id
    if requesting_user_id not in ADMINS:
        err_msg = "Access Denied."
        if update.callback_query: await update.callback_query.answer(err_msg, show_alert=True)
        else: await update.message.reply_text(err_msg)
        return

    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id) # Admin ID
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id) # Admin ID
        current_page = 1

    # Original log
    logger.info(f"Admin {telegram_id} listing users on page {current_page}") # Corrected log user

    try: # Added basic try block
        # --- ASYNC CHANGE: Added await ---
        users = await get_non_user_accounts() or [] # Fetch agents/owners, ensure list
        total_users = len(users) # Get total before check

        # Original check
        if not users:
            message = "There are no registered agents or owners."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original pagination
        start_index = (current_page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        paginated_users = users[start_index:end_index]

        if not paginated_users and current_page > 1:
             current_page -= 1
             start_index = (current_page - 1) * PAGE_SIZE
             end_index = start_index + PAGE_SIZE
             paginated_users = users[start_index:end_index]

        if not paginated_users: # If still empty
            message = f"No users found on page {current_page}."
            if update.callback_query: await query.edit_message_text(message)
            else: await update.message.reply_text(message)
            return

        # Original response text
        response_text = f"👥 *Registered Agents and Owners (Page {current_page})*:\n\n" # Add page num
        for i, user in enumerate(paginated_users, start=start_index + 1):
            prop_count = "N/A" # Default
            user_tg_id = user.get('telegram_id') # Use get
            if user_tg_id:
                 try:
                    # --- ASYNC CHANGE: Added await ---
                     confirmed_properties = await get_confirmed_user_properties(user_tg_id)
                     prop_count = len(confirmed_properties) if confirmed_properties else 0 # Handle None/empty
                 except Exception as e:
                      logger.error(f"Error fetching prop count for user {user_tg_id}: {e}")
                      prop_count = "Error"

            user_type = user.get("user_type", "N/A") # Use get
            user_type_icon = "👤" if user_type == "agent" else "🏢" if user_type in ["owner", "company"] else "❓" # Keep original logic + company
            # Basic Markdown escape
            full_name_safe = user.get("full_name","N/A").replace("*","\\*").replace("_","\\_")
            type_safe = user_type.capitalize().replace("*","\\*").replace("_","\\_")

            # Original format
            response_text += (
                f"{i}. {user_type_icon} *{full_name_safe}* - Type: *{type_safe}*\n"
                f"   🔑 Confirmed Properties: {prop_count}\n"
            )

        # Original pagination buttons
        buttons = []
        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_users:{current_page - 1}"))
        if end_index < total_users: # Use total_users
            row.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_users:{current_page + 1}"))
        if row: buttons.append(row)
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        # Original send logic
        if update.callback_query:
            await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e: # Basic catch-all
         logger.error(f"Error in list_users for admin {telegram_id}: {e}", exc_info=True)
         err_msg = "Error fetching users."
         if update.callback_query: await query.edit_message_text(err_msg)
         else: await update.message.reply_text(err_msg)


# --- ASYNC CHANGE: Added async keyword ---
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /changelang command to allow users to choose a language."""
    # Original keyboard setup
    keyboard = [[LANGUAGES[0], LANGUAGES[1]]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True) # Added one_time

    message_text = "Please choose a language:"

    # Original source check logic
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Original: Send new message for ReplyKeyboard
        await query.message.reply_text(message_text, reply_markup=reply_markup)
        # Optionally edit original inline keyboard away if needed
        # await query.edit_message_reply_markup(reply_markup=None)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

# --- ASYNC CHANGE: Added async keyword ---
async def handle_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's language selection."""
    # Original logic (triggered by filtered MessageHandler)
    user_choice = update.message.text

    if user_choice in LANGUAGES:
        context.user_data['language'] = user_choice # Store if needed
        # Original confirmation
        await update.message.reply_text(
            f"You have chosen {user_choice}.", reply_markup=ReplyKeyboardRemove()
        )
    # No else needed due to filter

# --- ASYNC CHANGE: Added async keyword ---
async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all user requests for the admin that have not been responded to."""
    # Original admin check
    admin_id_check = update.message.from_user.id # Renamed var
    if admin_id_check not in ADMINS:
        await update.message.reply_text("You do not have permission to access this command.")
        return

    # Original try-except block structure
    try:
        await update.message.chat.send_action(ChatAction.TYPING)
        # --- ASYNC CHANGE: Added await ---
        all_reqs = await get_all_requests() or [] # Ensure list

        # Original filter
        pending_requests = [req for req in all_reqs if not req.get('is_responded')] # Use get

        if pending_requests:
            message = "📨 *Unresponded Requests*\n\n"
            for req in pending_requests:
                # Original MarkdownV2 escaping
                request_id = str(req.get('id','N/A')).replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*','\\*').replace('[','\\[').replace(']','\\]').replace('(','\\(').replace(')','\\)').replace('~','\\~').replace('`','\\`').replace('>','\\>').replace('#','\\#').replace('+','\\+').replace('=','\\=').replace('|','\\|').replace('{','\\{').replace('}','\\}').replace('!','\\!')
                user_id = str(req.get('user_id','N/A')).replace('-', '\\-')
                additional_text = req.get('additional_text','').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*','\\*').replace('[','\\[').replace(']','\\]').replace('(','\\(').replace(')','\\)').replace('~','\\~').replace('`','\\`').replace('>','\\>').replace('#','\\#').replace('+','\\+').replace('=','\\=').replace('|','\\|').replace('{','\\{').replace('}','\\}').replace('!','\\!')
                name = req.get('name', 'User').replace('.', '\\.').replace('-', '\\-').replace('_', '\\_').replace('*','\\*').replace('[','\\[').replace(']','\\]').replace('(','\\(').replace(')','\\)').replace('~','\\~').replace('`','\\`').replace('>','\\>').replace('#','\\#').replace('+','\\+').replace('=','\\=').replace('|','\\|').replace('{','\\{').replace('}','\\}').replace('!','\\!')

                # Original message format
                message += (
                    f"❓ *Request ID:* `{request_id}`\n" # Use backticks
                    f"👤 *User:* {name} (ID: `{user_id}`)\n" # Add name, use backticks
                    f"📄 *Additional Text:* {additional_text}\n\n"
                    # Add suggestion to reply
                    f"👉 Use `/respond {request_id}` to reply\.\n\n"
                )

            # Original splitting logic
            if len(message) > 4096:
                for i in range(0, len(message), 4096):
                    await update.message.reply_text(message[i:i+4096], parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text("No pending requests found.")

    # Original exception handling
    except Exception as e:
        logger.error(f"Error listing requests for admin {admin_id_check}: {e}", exc_info=True) # Added logger
        await update.message.reply_text(f"An error occurred: {e}")


# --- ASYNC CHANGE: Added async keyword ---
async def live_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to request a live agent."""
    # Original source check
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    # Original log
    logger.info(f"Live agent request triggered for user {telegram_id}")

    # Original conditional text
    if update.callback_query:
        # Original text for callback was different, using the command text for consistency
        # await query.edit_message_text("Use /live_agent to connect with a live agent:")
        await query.edit_message_text("Please provide your name to connect with a live agent:") # Match command text
    else:
        await update.message.reply_text("Please provide your name to connect with a live agent:")

    return LIVE_REQUEST # Original return state (State 4)


# --- Live Agent Conversation Handlers ---
# --- ASYNC CHANGE: Added async keyword ---
async def live_agent_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input for live agent request."""
    # Original key storage
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Please provide your phone number:")
    return LIVE_PHONE # Original return state (State 5)

# --- ASYNC CHANGE: Added async keyword ---
async def live_agent_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone input for live agent request."""
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Please provide your address:")
    return LIVE_ADDRESS # Original return state (State 6)

# --- ASYNC CHANGE: Added async keyword ---
async def live_agent_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle address input for live agent request."""
    context.user_data['address'] = update.message.text
    await update.message.reply_text("Any additional details you would like to provide?")
    return LIVE_ADDITIONAL_TEXT # Original return state (State 7)

# --- ASYNC CHANGE: Added async keyword ---
async def live_agent_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final details and send the request to the admin."""
    context.user_data['additional_text'] = update.message.text
    user_id = str(update.message.from_user.id) # Ensure string
    username = update.message.from_user.username or "No username"
    name = context.user_data.get('name')
    phone = context.user_data.get('phone')
    address = context.user_data.get('address')
    additional_text = context.user_data.get('additional_text')

    # --- ASYNC CHANGE: Added await ---
    request_response = await create_request(
        user_id=user_id, # Pass user TG ID
        username=username,
        name=name,
        phone=phone,
        address=address,
        additional_text=additional_text
    )

    # Original check (assuming truthy return on success)
    if request_response and request_response.get('id'): # Check for ID
        await update.message.reply_text("Your request has been submitted successfully. We will get back to you soon.")

        # Original admin notification
        admin_target_id = ADMINS[0] if ADMINS else None # Target first admin
        if admin_target_id:
            # Original formatting using MarkdownV2
            req_id_safe = str(request_response['id']).replace('-','\\-')
            username_safe = username.replace('_','\\_')
            name_safe = name.replace('.','\\.').replace('-','\\-').replace('_','\\_').replace('*','\\*') # etc.
            phone_safe = phone.replace('.','\\.').replace('-','\\-').replace('_','\\_').replace('*','\\*') # etc.
            address_safe = address.replace('.','\\.').replace('-','\\-').replace('_','\\_').replace('*','\\*') # etc.
            additional_text_safe = additional_text.replace('.','\\.').replace('-','\\-').replace('_','\\_').replace('*','\\*') # etc.

            request_details_md = (
                f"📨 *New Live Agent Request*\n\n"
                f"*Request ID:* `{req_id_safe}`\n" # Backticks added
                f"*Username:* @{username_safe}\n" # Original had no @? Added it.
                f"*Name:* {name_safe}\n"
                f"*Phone:* {phone_safe}\n"
                f"*Address:* {address_safe}\n\n"
                f"📄 *Additional Information:* {additional_text_safe}"
            )
            try:
                await context.bot.send_message(chat_id=admin_target_id, text=request_details_md, parse_mode=ParseMode.MARKDOWN_V2)
            except Exception as e:
                 logger.error(f"Failed to notify admin {admin_target_id}: {e}") # Log error if notify fails
        else:
             logger.warning("No admin configured for live agent notification")


    else:
        await update.message.reply_text("There was an error submitting your request. Please try again later.")
        logger.error(f"API create_request failed: {request_response}") # Log failure

    # Clear context data for live agent convo
    for key in ['name','phone','address','additional_text']:
        context.user_data.pop(key, None)

    return ConversationHandler.END # Original return

# --- Admin Respond Conversation Handlers ---
# --- ASYNC CHANGE: Added async keyword ---
async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process to respond to a request."""
    # Original admin check
    admin_id_check = update.message.from_user.id
    if admin_id_check not in ADMINS:
        await update.message.reply_text("You do not have permission to access this command.")
        return ConversationHandler.END

    # Original prompt (doesn't handle args)
    await update.message.reply_text("Please enter the Request ID of the request you want to respond to:")
    return RESPOND_TO_REQUEST # Original return state (State 8)

# --- ASYNC CHANGE: Added async keyword ---
async def respond_request_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the request ID input and fetch user details."""
    request_id = update.message.text.strip() # Added strip
    context.user_data['request_id'] = request_id # Original key storage

    try: # Added basic try block for API call
        # --- ASYNC CHANGE: Added await ---
        request_details = await get_request_details(request_id)

        # Original check
        if request_details and request_details.get('user_id'): # Check user_id exists
            user_id = request_details['user_id'] # Target user's TG ID
            context.user_data['user_id'] = user_id # Original key storage
            name = request_details.get('name', 'User') # Default name
            await update.message.reply_text(f"Request ID `{request_id}` found for user *{name}* (User ID: `{user_id}`).\nPlease enter your response message:", parse_mode=ParseMode.MARKDOWN_V2) # Use MD V2
            return RESPONSE_MESSAGE # Original return state (State 9)
        else:
            await update.message.reply_text(f"Invalid Request ID: `{request_id}`. Please try again or use /cancel.", parse_mode=ParseMode.MARKDOWN_V2) # Use MD V2
            # Don't end conversation, allow re-entry or cancel
            return RESPOND_TO_REQUEST # Stay in state

    except Exception as e: # Basic catch-all
         logger.error(f"Error fetching request details for {request_id}: {e}", exc_info=True)
         await update.message.reply_text("Error fetching request details. Use /cancel.")
         # Clear context and end on error
         context.user_data.pop('request_id', None)
         return ConversationHandler.END


# --- ASYNC CHANGE: Added async keyword ---
async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the response message and send it to the user."""
    response_message = update.message.text
    request_id = context.user_data.get('request_id')
    user_id = context.user_data.get('user_id') # User TG ID to reply to
    admin_id = str(update.message.from_user.id)

    # Check context validity
    if not request_id or not user_id:
         logger.error(f"Missing context in send_response: {context.user_data}")
         await update.message.reply_text("Error sending: context missing. Start over with /respond.")
         return ConversationHandler.END

    api_logged = False
    try:
        # --- ASYNC CHANGE: Added await --- Log to API
        message_sent_response = await create_message(
            request_id=request_id,
            sender_id=admin_id, # Admin is sender
            user_id=user_id,    # User is recipient context
            content=response_message
        )
        # Original didn't check response, assume success if no error
        if message_sent_response and message_sent_response.get('id'): # Check ID
             api_logged = True
             logger.info(f"API logged response for req {request_id}")
             # Optionally mark req as responded via API call here
        else:
             logger.error(f"API failed to log response for {request_id}: {message_sent_response}")
             # Don't block sending to user

    except Exception as api_err: # Catch API log errors
         logger.error(f"Error logging response via API for req {request_id}: {api_err}")
         await update.message.reply_text("Warning: Failed to log response in system.")


    # Original send logic via Telegram
    try:
        # Original confirmation message assumes success logging? Adjusted slightly
        # await update.message.reply_text(f"Message sent successfully to user {user_id}.") # Original
        await context.bot.send_message(chat_id=user_id, text=f"Response regarding request {request_id}:\n\n{response_message}") # Add context
        await update.message.reply_text(f"Message sent to user {user_id} (Req ID: {request_id}).") # Confirm send
        if not api_logged:
            await update.message.reply_text("Note: Message was NOT logged in history.")

    # Original exception handling for Telegram send
    except Exception as e:
        logging.error(f"Failed to send message to user {user_id}: {e}")
        await update.message.reply_text(f"Failed to send message to user {user_id} on Telegram. Error: {e}")
        # Add info about logging status
        if api_logged: await update.message.reply_text("Message WAS logged in history.")
        else: await update.message.reply_text("Message was NOT logged in history either.")

    # Clear context for respond convo
    context.user_data.pop('request_id', None)
    context.user_data.pop('user_id', None)

    return ConversationHandler.END # Original return


# --- General Message Handler ---
# --- ASYNC CHANGE: Added async keyword ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages from users."""
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Original admin check
    if user_id in ADMINS:
        await update.message.reply_text("You are an admin. Use /requests to view pending requests and use /respond to respond to a request.")
        return

    try: # Add basic try block
        # --- ASYNC CHANGE: Added await ---
        messages = await get_all_messages() or [] # Ensure list
        # print(messages) # Original print

        # Original logic to find open message context
        open_message = None
        # This logic finds *any* message involving the user, not necessarily the latest or an open thread
        for msg in messages:
            # Original check compared int(msg['user_id']) == user_id
            # This seems flawed. Should check if user is sender OR recipient in an ongoing request.
            # Let's try the refined logic from previous attempts for finding context:
            if str(msg.get('user_id')) == str(user_id): # Find messages related to user's requests
                 open_message = msg # Keep the last matching message (might not be correct context)
                 # break # Original break finds first match only? Let it find last.

        # Refined context finding (find latest request involving user)
        user_related_messages = [msg for msg in messages if str(msg.get('user_id')) == str(user_id)]
        user_related_messages.sort(key=lambda x: x.get('timestamp', 0), reverse=True) # Requires timestamp

        active_request_id = None
        involved_admin_id = None
        if user_related_messages:
            latest_msg = user_related_messages[0]
            req_id = latest_msg.get('request')
            if req_id:
                 active_request_id = req_id
                 # Find admin in this thread
                 admin_msg = next((m for m in user_related_messages if m.get('request') == req_id and str(m.get('sender_id')) != str(user_id) and int(str(m.get('sender_id'))) in ADMINS), None)
                 if admin_msg: involved_admin_id = str(admin_msg.get('sender_id'))
                 elif ADMINS: involved_admin_id = str(ADMINS[0]) # Fallback admin


        # Check using refined context finding instead of original 'open_message'
        if active_request_id and involved_admin_id:
            # request_id = open_message['request'] # Original logic
            # sender_id = open_message['sender_id'] # Original logic - likely incorrect admin target

            logger.info(f"Forwarding user {user_id} msg for req {active_request_id} to admin {involved_admin_id}")
            # --- ASYNC CHANGE: Added await --- Log message
            await create_message(
                request_id=active_request_id, # Use correct request ID
                sender_id=str(user_id), # User is sender
                user_id=str(user_id),   # Context is user's
                content=user_message
            )

            # Forward to correct admin
            try:
                 username = update.effective_user.username or 'N/A'
                 await context.bot.send_message(
                    chat_id=involved_admin_id, # Use determined admin ID
                    text=f"💬 Msg from user {user_id} (@{username}) for Req ID `{active_request_id}`:\n\n{user_message}\n\n👉 Use `/respond {active_request_id}`", # Use MD V2
                    parse_mode=ParseMode.MARKDOWN_V2
                 )
                 await update.message.reply_text("Your message has been forwarded.") # Original confirmation
            except Exception as e:
                 logger.error(f"Failed forward msg from {user_id} to admin {involved_admin_id}: {e}")
                 await update.message.reply_text("Msg received, agent notify failed.")

        else:
            # Original fallback message
            await update.message.reply_text("No open messages found for you. Use /live_agent command to make a new request.")

    except Exception as e: # Basic catch-all
         logger.error(f"Error in handle_message for {user_id}: {e}", exc_info=True)
         await update.message.reply_text("Error processing message.")


# --- Main Menu Callback Handler ---
# --- ASYNC CHANGE: Added async keyword ---
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() # Acknowledge the callback
    data = query.data
    telegram_id = query.from_user.id
    # Original log
    logger.info(f"User {telegram_id} clicked on button: {data}")

    # --- ASYNC CHANGE: Call async functions ---
    # Original routing logic
    if data.startswith("make_favorite_"):
        logger.info(f"Handling 'Make Favorite' for user {telegram_id}")
        await handle_favorite_request(update, context)
    elif data == "add_property":
        logger.info(f"Handling 'Add Property' for user {telegram_id}")
        await addproperty(update, context)
    elif data == "upgrade_account":
        logger.info(f"Handling 'Upgrade Account' for user {telegram_id}")
        await upgrade(update, context)
    elif data == "view_profile":
        logger.info(f"Handling 'View Profile' for user {telegram_id}")
        await profile(update, context)
    # Keep original simple checks for list commands (no pagination parsing here)
    elif data == "list_properties":
        logger.info(f"Handling 'List Properties' for user {telegram_id}")
        await list_properties(update, context)
    elif data == "list_favorites":
        logger.info(f"Handling 'List Favorites' for user {telegram_id}")
        await list_favorites(update, context)
    elif data == "list_tours":
        logger.info(f"Handling 'List Tours' for user {telegram_id}")
        await list_tours(update, context)
    elif data == "live_agent":
        logger.info(f"Handling 'Live Agent' button for user {telegram_id}")
        # Let the ConversationHandler entry point handle this if pattern matches
        await live_agent(update, context) # Call entry point
    elif data == "change_language":
        logger.info(f"Handling 'Change Language' for user {telegram_id}")
        await change_language(update, context)
    # Handle list pagination explicitly if callbacks include ':'
    elif data.startswith("list_users:"): # Admin pagination
        logger.info(f"Handling pagination for 'List Users' for admin {telegram_id}")
        await list_users(update, context)
    elif data.startswith("list_properties:"):
        logger.info(f"Handling pagination for 'List Properties' for user {telegram_id}")
        await list_properties(update, context)
    elif data.startswith("list_tours:"):
        logger.info(f"Handling pagination for 'List Tours' for user {telegram_id}")
        await list_tours(update, context)
    elif data.startswith("list_favorites:"):
        logger.info(f"Handling pagination for 'List Favorites' for user {telegram_id}")
        await list_favorites(update, context)

    else: # Original fallback for unknown action
        logger.warning(f"Unknown action {data} received from user {telegram_id}")
        # Try editing, but catch potential errors if message changed
        try: await query.edit_message_text("Unknown action. Please try again.")
        except Exception: logger.warning(f"Failed to edit message for unknown action {data}")


# --- Original bot_tele Hosting Logic ---
# --- ASYNC CHANGE: Added async keyword ---
async def bot_tele(text: dict): # Expecting dict payload
    """Original function for webhook processing."""
    token = os.getenv('TOKEN')
    if not token:
        logger.critical("TOKEN missing!")
        return

    # Original application build inside function
    application = Application.builder().token(token).persistence(persistence).build()

    # --- Original Handler Definitions ---
    # --- Need to ensure handlers use async functions ---
    tour_request_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^/request_tour_(\d+)$'), request_tour), # Original Regex
            CommandHandler("start", start), # Start can trigger deep link
            # CallbackQueryHandler(handle_main_menu) # Original had this - might conflict
        ],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone_number)],
            TOUR_DATE: [MessageHandler(filters.TEXT & filters.Regex(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$'), get_tour_date)], # Added filter
            TOUR_TIME: [CallbackQueryHandler(get_tour_time)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.COMMAND | filters.TEXT, fallback)], # Original fallback
        persistent=True,
        name="tour_request_handler"
    )

    live_agent_conv_handler = ConversationHandler(
        entry_points=[
             CommandHandler("live_agent", live_agent),
             CallbackQueryHandler(live_agent, pattern='^live_agent$') # Allow button entry
             ],
        states={
            LIVE_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_name)],
            LIVE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_phone)],
            LIVE_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_address)],
            LIVE_ADDITIONAL_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, live_agent_complete)],
        },
        fallbacks=[CommandHandler("leave", leave), CommandHandler("cancel", leave)], # KEEP BOTH
        persistent=True,
        name="live_agent_conversation",
        # conversation_timeout=300 # Original timeout
    )

    respond_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("respond", respond)],
        states={
            RESPOND_TO_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, respond_request_id)],
            RESPONSE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_response)],
        },
        fallbacks=[CommandHandler("leave", leave), CommandHandler("cancel", leave)], # KEEP BOTH
        persistent=True,
        name="user_request_conversation",
    )

    # --- Original Handler Addition Order ---
    application.add_handler(live_agent_conv_handler) # Live agent first
    application.add_handler(respond_conv_handler)    # Respond second
    application.add_handler(tour_request_handler)    # Tour third

    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("addproperty", addproperty))
    application.add_handler(CommandHandler("upgrade", upgrade))
    application.add_handler(CommandHandler("list_properties", list_properties))
    application.add_handler(CommandHandler("requests", list_requests, filters.User(ADMINS))) # Added filter
    application.add_handler(CommandHandler("list_tours", list_tours))
    application.add_handler(CommandHandler("list_favorites", list_favorites))
    # application.add_handler(CallbackQueryHandler(handle_favorite_request)) # Keep commented if handle_main_menu covers it
    application.add_handler(CallbackQueryHandler(handle_main_menu)) # Keep broad handler

    application.add_handler(CommandHandler("list_users", list_users, filters.User(ADMINS))) # Added filter
    application.add_handler(CommandHandler("changelang", change_language))

    # Message handlers last
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(f'^({"|".join(LANGUAGES)})$'), handle_language_choice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


    # --- Original Webhook Processing Logic ---
    try:
        # No webhook setting needed here if webhook is set externally
        # webhook_url = os.getenv('webhook')
        # await application.bot.set_webhook(url=webhook_url)

        # Original queue logic
        update = Update.de_json(data=text, bot=application.bot)
        await application.update_queue.put(update)

        # Original start/stop - this will process the queue until empty
        async with application:
            await application.start()
            await application.stop()

        # Original log
        logger.info("Bot has started and stopped successfully.") # For this single run

    except Exception as e:
         logger.error(f"Error in bot_tele processing: {e}", exc_info=True)
    finally:
         # Ensure persistence is saved
         await application.persistence.flush()
