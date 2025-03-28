from typing import Any, List
import aiohttp
import asyncio

API_URL = "https://estate-r22a.onrender.com/api/customers/"
TOUR_URL = "https://estate-r22a.onrender.com/api/tours/"
PROPERTY_URL = "https://estate-r22a.onrender.com/api/properties/"

async def make_request(method: str, url: str, **kwargs) -> Any:
    """Generic async request handler with timeout and error handling"""
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(method, url, **kwargs) as response:
            if response.status == 200 or response.status == 201:
                return await response.json()
            return None

async def register_user(telegram_id: str, full_name: str) -> dict:
    """Register a new user with the Telegram bot."""
    data = {
        "telegram_id": telegram_id,
        "full_name": full_name,
    }
    result = await make_request('POST', API_URL, json=data)
    if result:
        return {"success": True, "message": f"Welcome, {full_name}!"}
    return {"success": False, "message": "Registration failed. Please try again later."}

async def is_user_registered(telegram_id: str) -> bool:
    """Check if the user is already registered."""
    result = await make_request('GET', f"{API_URL}{telegram_id}/")
    return result is not None

async def get_user_details(telegram_id: str) -> Any | None:
    """Fetch user details by Telegram ID."""
    return await make_request('GET', f"{API_URL}{telegram_id}/")

async def get_property_details(property_id: int) -> Any | None:
    """Fetch property details by property ID."""
    return await make_request('GET', f"{PROPERTY_URL}{property_id}/")

async def upgrade_user(telegram_id: str, new_user_type: str) -> dict:
    """Upgrade the user's account to 'agent' or 'owner'."""
    url = f"{API_URL}{telegram_id}/"
    data = {"user_type": new_user_type}
    
    result = await make_request('PATCH', url, json=data)
    if result:
        return {"success": True, "message": "Your account has been upgraded successfully."}
    return {"success": False, "message": "Failed to upgrade account."}

async def get_user_properties(telegram_id: str) -> List[dict]:
    """Fetch properties associated with a specific user by Telegram ID."""
    result = await make_request('GET', f"{API_URL}{telegram_id}/properties/")
    return result if result else []

async def get_user_tours(telegram_id: str) -> List[dict]:
    """Fetch tours associated with a specific user by Telegram ID."""
    result = await make_request('GET', f"{TOUR_URL}telegram/{telegram_id}/")
    return result if result else []

async def get_user_favorites(telegram_id: str) -> List[dict]:
    """Fetch favorite properties for a specific user by Telegram ID."""
    result = await make_request('GET', f"{API_URL}{telegram_id}/favorites/")
    return result if result else []

async def get_all_users() -> List[dict]:
    """Fetch all users from the API."""
    result = await make_request('GET', API_URL)
    return result if result else []

async def get_non_user_accounts() -> List[dict]:
    """Filter out users with a user_type of 'agent' or 'owner'."""
    all_users = await get_all_users()
    return [user for user in all_users if user.get("user_type") in ["agent", "owner"]]

async def get_confirmed_user_properties(telegram_id: str) -> List[dict]:
    """Fetch confirmed properties associated with a specific user."""
    user_properties = await get_user_properties(telegram_id)
    if not user_properties:
        return []
    
    # Process properties concurrently
    tasks = [get_property_details(prop['id']) for prop in user_properties]
    properties = await asyncio.gather(*tasks)
    
    return [
        prop for prop in properties 
        if prop and prop.get("status") == "confirmed"
    ]
