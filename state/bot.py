from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, PicklePersistence, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
import logging
import asyncio
from state.tools import (
    register_user, 
    is_user_registered, 
    get_user_details, 
    get_user_properties,
    get_user_tours,
    get_property_details,
    get_user_favorites,
    get_non_user_accounts,
    get_confirmed_user_properties
)
from live.api import (
    create_message,
    get_all_requests,
    get_request_details,
    get_all_messages,
    create_request
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize persistence
persistence = PicklePersistence(filepath='bot_dat')
PAGE_SIZE = 2

# Define states for conversation flows
FULL_NAME, PHONE_NUMBER, TOUR_DATE, TOUR_TIME = range(4)
LIVE_REQUEST, LIVE_PHONE, LIVE_ADDRESS, LIVE_ADDITIONAL_TEXT = range(3, 7)
RESPOND_TO_REQUEST, RESPONSE_MESSAGE = range(2)

ADMINS = [1648265210]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command with optional deep-linking for tour requests."""
    telegram_id = str(update.message.from_user.id)
    full_name = update.message.from_user.full_name
    username = update.message.from_user.username

    context.user_data['telegram_id'] = telegram_id
    context.user_data['username'] = username

    args = context.args
    if args and args[0].startswith("request_tour_"):
        property_id = args[0].split("_")[2]
        context.user_data['property_id'] = property_id
        await update.message.reply_text("Please provide your full name to start scheduling the tour.")
        return FULL_NAME

    if await is_user_registered(telegram_id):
        user_details = await get_user_details(telegram_id)
        if user_details:
            profile_token = user_details.get("profile_token")
            await update.message.reply_text(
                f"Welcome back, {full_name}! Here are some quick options:",
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text("Could not retrieve your details. Please try again later.")
    else:
        result = await register_user(telegram_id, full_name)
        await update.message.reply_text(result["message"])
        await update.message.reply_text(
            "You're registered! Here are some quick options:",
            reply_markup=get_main_menu()
        )

def get_main_menu():
    """Generate the main menu inline keyboard with descriptive emojis."""
    buttons = [
        [InlineKeyboardButton("➕ Add Property 🏡", callback_data="add_property")],
        [InlineKeyboardButton("✨ Upgrade Account ⭐", callback_data="upgrade_account")],
        [InlineKeyboardButton("👤 View Profile 🔍", callback_data="view_profile")],
        [InlineKeyboardButton("📋 List Properties 📂", callback_data="list_properties")],
        [InlineKeyboardButton("❤️ List Favorites 💾", callback_data="list_favorites")],
        [InlineKeyboardButton("📅 List Tours 🗓️", callback_data="list_tours")],
        [InlineKeyboardButton("💬 Live Agent 📞", callback_data="live_agent")],
        [InlineKeyboardButton("🌐 Change Language 🌍", callback_data="change_language")],
    ]

    # Arrange buttons in two columns
    formatted_buttons = []
    for i in range(0, len(buttons) - 1, 2):
        formatted_buttons.append(buttons[i] + buttons[i + 1])
    if len(buttons) % 2 == 1:
        formatted_buttons.append(buttons[-1])

    return InlineKeyboardMarkup(formatted_buttons)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Profile command to handle user profile viewing and editing."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    logger.info(f"Profile command triggered for user {telegram_id}")
    user_details = await get_user_details(telegram_id)

    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    profile_token = user_details.get("profile_token")
    web_app_url = f"https://t.me/yene_etbot/state?startapp=edit-{profile_token}"
    message = "You can edit your profile using the following link (click to open):"
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Edit Profile", url=web_app_url)]]
    )

    if update.callback_query:
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

async def addproperty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add property command to check if the user can add properties."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)
    
    logger.info(f"addproperty triggered for user {telegram_id}")
    user_details = await get_user_details(telegram_id)

    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    user_type = user_details.get("user_type")
    profile_token = user_details.get("profile_token")

    if user_type == 'user':
        message = (
            "You can only browse or inquire about properties. To add your own property, "
            "please upgrade your account by using /upgrade and choosing the Agent or Company option."
        )
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)

    elif user_type in ['agent', 'owner']:
        web_app_url = f"https://t.me/yene_etbot/state?startapp=edit-{profile_token}"
        message = "You have permission to add properties! Use the following link to proceed:"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Add Property", url=web_app_url)]]
        )
        if update.callback_query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    else:
        message = "User type not recognized. Please contact support for assistance."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upgrade account command to handle user upgrades and profile management."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    logger.info(f"Upgrade triggered for user {telegram_id}")
    user_details = await get_user_details(telegram_id)

    if not user_details:
        message = "Could not retrieve your details. Please make sure you're registered using /start."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    user_type = user_details.get("user_type")
    profile_token = user_details.get("profile_token")

    if user_type in ['agent', 'owner']:
        message = "You are already upgraded to your current account type. Use /profile to manage your account."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)

    elif user_type == 'user':
        web_app_url = f"https://t.me/yene_etbot/state?startapp=edit-{profile_token}"
        message = "Account upgrades are irreversible. To upgrade your account, please visit your profile:"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Edit Profile", url=web_app_url)]]
        )
        if update.callback_query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    else:
        message = "User type not recognized. Please contact support for assistance."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)

async def request_tour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the tour request conversation."""
    command_parts = update.message.text.split("_")

    if len(command_parts) < 2:
        await update.message.reply_text("Please specify the property ID with the command, like this: /request_tour_<property_id>")
        return ConversationHandler.END

    property_id = command_parts[1]
    context.user_data['property_id'] = property_id

    await update.message.reply_text("Please provide your full name.")
    return FULL_NAME

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the user's full name for tour request."""
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Thanks! Now, please provide your phone number.")
    return PHONE_NUMBER

async def get_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the user's phone number for tour request."""
    context.user_data['phone_number'] = update.message.text

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
    return TOUR_DATE

async def get_tour_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the tour date from user."""
    tour_date = update.message.text
    if tour_date not in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        await update.message.reply_text("Invalid selection. Please select a valid day of the week.")
        return TOUR_DATE

    context.user_data['tour_date'] = tour_date
    await update.message.reply_text("Thank you! Now, please select a time for the tour.", reply_markup=ReplyKeyboardRemove())

    time_buttons = [
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(6, 11)]
    ]
    await update.message.reply_text(
        "Finally, at what time (1-10) would you like to schedule the tour?",
        reply_markup=InlineKeyboardMarkup(time_buttons)
    )
    return TOUR_TIME

async def get_tour_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the tour time and complete the request."""
    await update.callback_query.answer()
    tour_time = update.callback_query.data
    try:
        tour_time = int(tour_time)
        if not 1 <= tour_time <= 10:
            raise ValueError
    except ValueError:
        await update.callback_query.answer("Invalid time. Please select a valid time from the options provided.")
        return TOUR_TIME

    context.user_data['tour_time'] = tour_time
    telegram_id = str(update.callback_query.from_user.id)
    username = update.callback_query.from_user.username or ""

    data = {
        "property": context.user_data['property_id'],
        "full_name": context.user_data['full_name'],
        "phone_number": context.user_data['phone_number'],
        "tour_date": context.user_data['tour_date'],
        "tour_time": context.user_data['tour_time'],
        "telegram_id": telegram_id,
        "username": username
    }

    try:
        response = await create_request(data)
        if response:
            await update.callback_query.edit_message_text("Your tour request has been submitted!")
        else:
            await update.callback_query.edit_message_text("Failed to submit tour request. Please try again.")
    except Exception as e:
        logger.error(f"Failed to submit tour request: {e}")
        await update.callback_query.edit_message_text("An error occurred while submitting your request. Please try again later.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current conversation."""
    await update.message.reply_text("The operation has been canceled. Use /start to begin again.")
    return ConversationHandler.END

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unexpected input during conversations."""
    await update.message.reply_text("Please follow the instructions or use /cancel to exit.")

async def list_properties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List properties associated with the user with pagination."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    logger.info(f"List properties triggered for user {telegram_id} on page {current_page}")
    properties = await get_user_properties(telegram_id)

    if not properties:
        message = "🏡 You don't have any properties listed yet! Use /addproperty to add one."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    start_index = (current_page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    paginated_properties = properties[start_index:end_index]

    response_text = "📝 Here are your properties:\n\n"
    for i, prop in enumerate(paginated_properties, start=start_index + 1):
        response_text += f"{i}. 📍 *{prop['name']}* - Status: *{prop['status']}*\n"

    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_properties:{current_page - 1}"))
    if end_index < len(properties):
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_properties:{current_page + 1}"))
    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    if update.callback_query:
        await query.edit_message_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )

async def list_tours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List tours associated with the user with pagination."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    logger.info(f"List tours triggered for user {telegram_id} on page {current_page}")
    tours = await get_user_tours(telegram_id)
    
    if not tours:
        message = "🚶‍♂️ You have no scheduled tours yet! Use /request_tour_<property_id> to schedule one."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    start_index = (current_page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    paginated_tours = tours[start_index:end_index]

    response_text = "📅 Here are your scheduled tours:\n\n"
    for i, tour in enumerate(paginated_tours, start=start_index + 1):
        property_details = await get_property_details(tour['property'])
        property_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'
        response_text += f"{i}. 🏡 Property: *{property_name}* - Date: *{tour['tour_date']}* - Time: *{tour['tour_time']}*\n"

    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_tours:{current_page - 1}"))
    if end_index < len(tours):
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_tours:{current_page + 1}"))
    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    if update.callback_query:
        await query.edit_message_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )

async def list_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List favorite properties associated with the user with pagination."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    logger.info(f"List favorites triggered for user {telegram_id} on page {current_page}")
    favorites = await get_user_favorites(telegram_id)
    
    if not favorites:
        message = "❤️ You have no favorite properties yet! Use the ❤️ button to add some."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    start_index = (current_page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    paginated_favorites = favorites[start_index:end_index]

    response_text = "🌟 Your Favorite Properties:\n\n"
    for i, favorite in enumerate(paginated_favorites, start=start_index + 1):
        property_details = await get_property_details(favorite['property'])
        property_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'
        response_text += f"{i}. 🏡 Property: *{property_name}*\n"

    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_favorites:{current_page - 1}"))
    if end_index < len(favorites):
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_favorites:{current_page + 1}"))
    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    if update.callback_query:
        await query.edit_message_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all registered users with pagination."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
        current_page = int(query.data.split(":")[1]) if ":" in query.data else 1
    else:
        telegram_id = str(update.message.from_user.id)
        current_page = 1

    logger.info(f"List users triggered for user {telegram_id} on page {current_page}")
    users = await get_non_user_accounts()
    total_users = len(users)
    
    if not users:
        message = "There are no registered agents or owners."
        if update.callback_query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    start_index = (current_page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    paginated_users = users[start_index:end_index]

    response_text = "👥 *Registered Agents and Owners:*\n\n"
    for i, user in enumerate(paginated_users, start=start_index + 1):
        confirmed_properties = await get_confirmed_user_properties(user['telegram_id'])
        property_count = len(confirmed_properties)
        user_type_icon = "👤" if user["user_type"] == "agent" else "🏢"
        response_text += (
            f"{i}. {user_type_icon} *{user['full_name']}* - Type: *{user['user_type'].capitalize()}*\n"
            f"   🔑 Confirmed Properties: {property_count}\n"
        )

    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_users:{current_page - 1}"))
    if end_index < total_users:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"list_users:{current_page + 1}"))
    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    if update.callback_query:
        await query.edit_message_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )

async def handle_favorite_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle adding/removing properties from favorites."""
    await update.callback_query.answer()
    data = update.callback_query.data

    if data.startswith("make_favorite_"):
        property_id = int(data.split("_")[2])
        telegram_id = str(update.callback_query.from_user.id)

        favorites = await get_user_favorites(telegram_id)
        logger.info(f"User's favorites for {telegram_id}: {favorites}")

        property_details = await get_property_details(property_id)
        property_name = property_details.get('name', 'Unknown Property') if property_details else 'Unknown Property'

        favorite_id = None
        for favorite in favorites:
            if favorite['property'] == property_id:
                favorite_id = favorite['id']
                break

        if favorite_id:
            try:
                response = await delete_favorite(favorite_id)
                if response:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=f"❌ The property *{property_name}* has been removed from your favorites."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text="❌ Failed to remove from favorites. Please try again later."
                    )
            except Exception as e:
                logger.error(f"Failed to remove property from favorites: {e}")
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text="❌ Failed to remove from favorites. Please try again later."
                )
        else:
            try:
                response = await add_favorite(telegram_id, property_id)
                if response:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=f"🏡 The property *{property_name}* has been added to your favorites!"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text="❌ Failed to add to favorites. Please try again later."
                    )
            except Exception as e:
                logger.error(f"Failed to add property to favorites: {e}")
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text="❌ Failed to add to favorites. Please try again later."
                )

async def live_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to request a live agent."""
    if update.callback_query:
        query = update.callback_query
        telegram_id = str(query.from_user.id)
        await query.answer()
    else:
        telegram_id = str(update.message.from_user.id)

    logger.info(f"Live agent request triggered for user {telegram_id}")

    if update.callback_query:
        await query.edit_message_text("Please provide your name to connect with a live agent:")
    else:
        await update.message.reply_text("Please provide your name to connect with a live agent:")

    return LIVE_REQUEST

async def live_agent_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input for live agent request."""
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Please provide your phone number:")
    return LIVE_PHONE

async def live_agent_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone input for live agent request."""
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Please provide your address:")
    return LIVE_ADDRESS

async def live_agent_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle address input for live agent request."""
    context.user_data['address'] = update.message.text
    await update.message.reply_text("Any additional details you would like to provide?")
    return LIVE_ADDITIONAL_TEXT

async def live_agent_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final details and send the request to the admin."""
    context.user_data['additional_text'] = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "No username"
    name = context.user_data.get('name')
    phone = context.user_data.get('phone')
    address = context.user_data.get('address')
    additional_text = context.user_data.get('additional_text')

    request = await create_request({
        'user_id': user_id,
        'username': username,
        'name': name,
        'phone': phone,
        'address': address,
        'additional_text': additional_text
    })

    if request:
        await update.message.reply_text("Your request has been submitted successfully. We will get back to you soon.")
        
        # Notify the admin
        admin_id = 1648265210
        request_details = (
            f"📨 *New Live Agent Request*\n\n"
            f"*Username:* {username}\n"
            f"*Name:* {name}\n"
            f"*Phone:* {phone}\n"
            f"*Address:* {address}\n\n"
            f"📄 *Additional Information:* {additional_text}"
        )
        await context.bot.send_message(
            chat_id=admin_id,
            text=request_details,
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text("There was an error submitting your request. Please try again later.")
    
    return ConversationHandler.END

async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process to respond to a request."""
    admin_id = 1648265210  

    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You do not have permission to access this command.")
        return ConversationHandler.END

    await update.message.reply_text("Please enter the Request ID of the request you want to respond to:")
    return RESPOND_TO_REQUEST

async def respond_request_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the request ID input and fetch user details."""
    request_id = update.message.text
    context.user_data['request_id'] = request_id

    request_details = await get_request_details(request_id)
    if request_details:
        user_id = request_details['user_id']
        context.user_data['user_id'] = user_id
        await update.message.reply_text(
            f"Request found for user {request_details['name']} (User ID: {user_id}).\n"
            "Please enter your response message:"
        )
        return RESPONSE_MESSAGE
    else:
        await update.message.reply_text("Invalid Request ID. Please try again.")
        return ConversationHandler.END

async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the response message and send it to the user."""
    response_message = update.message.text
    request_id = context.user_data.get('request_id')
    user_id = context.user_data.get('user_id')
    admin_id = update.message.from_user.id 

    message_sent = await create_message({
        'request_id': request_id,
        'sender_id': admin_id,
        'user_id': user_id,
        'content': response_message
    })
    
    if message_sent:
        await update.message.reply_text(f"Message sent successfully to user {user_id}.")
        try:
            await context.bot.send_message(chat_id=user_id, text=response_message)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            await update.message.reply_text(
                f"Failed to send message to user {user_id} on Telegram. Error: {e}"
            )
    else:
        await update.message.reply_text("Failed to record the message. Please try again.")
    
    return ConversationHandler.END

async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all user requests for the admin that have not been responded to."""
    admin_id = 1648265210
    
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You do not have permission to access this command.")
        return
    
    try:
        await update.message.chat.send_action(ChatAction.TYPING)
        requests = await get_all_requests()
        
        pending_requests = [req for req in requests if not req['is_responded']]

        if pending_requests:
            message = "📨 *Unresponded Requests*\n\n"
            for req in pending_requests:
                request_id = str(req['id']).replace('.', '\\.').replace('-', '\\-').replace('_', '\\_')
                user_id = str(req['user_id']).replace('-', '\\-')
                additional_text = req['additional_text'].replace('.', '\\.').replace('-', '\\-').replace('_', '\\_')

                message += (
                    f"❓ *Request ID:* {request_id}\n"
                    f"👤 *User ID:* {user_id}\n"
                    f"📄 *Additional Text:* {additional_text}\n\n"
                )
            
            if len(message) > 4096:
                for i in range(0, len(message), 4096):
                    await update.message.reply_text(message[i:i+4096], parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(message, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text("No pending requests found.")
    
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages from users."""
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    if user_id in ADMINS:
        await update.message.reply_text(
            "You are an admin. Use /requests to view pending requests and use /respond to respond to a request."
        )
        return

    messages = await get_all_messages()
    open_message = None
    for msg in messages:
        if int(msg['user_id']) == user_id:
            open_message = msg
            break

    if open_message:
        request_id = open_message['request']
        sender_id = open_message['sender_id']

        await create_message({
            'request_id': request_id,
            'sender_id': sender_id,
            'user_id': user_id,
            'content': user_message
        })

        await context.bot.send_message(
            chat_id=sender_id,
            text=f"Message from user {user_id} (Request ID: {request_id}):\n\n{user_message}"
        )
        await update.message.reply_text("Your message has been forwarded to the appropriate sender.")
    else:
        await update.message.reply_text("No open messages found for you. Use /live_agent command to make a new request.")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all main menu callback queries."""
    query = update.callback_query
    await query.answer()
    data = query.data
    telegram_id = query.from_user.id
    logger.info(f"User {telegram_id} clicked on button: {data}")

    if data.startswith("make_favorite_"):
        await handle_favorite_request(update, context)
    elif data == "add_property":
        await addproperty(update, context)
    elif data == "upgrade_account":
        await upgrade(update, context)
    elif data == "view_profile":
        await profile(update, context)
    elif data == "list_properties":
        await list_properties(update, context)
    elif data == "list_favorites":
        await list_favorites(update, context)
    elif data == "list_tours":
        await list_tours(update, context)
    elif data == "live_agent":
        await live_agent(update, context)
    elif data == "change_language":
        await change_language(update, context)
    elif data.startswith("list_users"):
        await list_users(update, context)
    elif data.startswith("list_properties"):
        await list_properties(update, context)
    elif data.startswith("list_tours"):
        await list_tours(update, context)
    elif data.startswith("list_favorites"):
        await list_favorites(update, context)
    else:
        logger.warning(f"Unknown action {data} received from user {telegram_id}")
        await query.edit_message_text("Unknown action. Please try again.")

    
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
