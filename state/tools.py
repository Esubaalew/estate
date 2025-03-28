from typing import Any, List, Dict
import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

API_BASE_URL = "https://estate-r22a.onrender.com/api"
CUSTOMER_API_URL = f"{API_BASE_URL}/customers/"
TOUR_API_URL = f"{API_BASE_URL}/tours/"
PROPERTY_API_URL = f"{API_BASE_URL}/properties/"
FAVORITE_API_URL = f"{API_BASE_URL}/favorites/"

async def make_request(method: str, url: str, timeout_seconds: int = 30, **kwargs) -> Any | None:
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.debug(f"Requesting: {method} {url} with args {kwargs}")
            async with session.request(method, url, **kwargs) as response:
                logger.debug(f"Response status from {url}: {response.status}")
                if response.status in [200, 201]:
                    try:
                        json_response = await response.json()
                        logger.debug(f"Response JSON from {url}: {str(json_response)[:200]}...")
                        return json_response
                    except aiohttp.ContentTypeError:
                        logger.warning(f"Response from {url} was not JSON (status {response.status}).")
                        return await response.text()
                elif response.status == 204:
                    logger.debug(f"Received 204 No Content from {url}")
                    return True
                elif response.status == 404:
                    logger.warning(f"Resource not found (404) at {url}")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"HTTP Error {response.status} from {url}: {error_text}")
                    return None

    except asyncio.TimeoutError:
        logger.error(f"Request timed out after {timeout_seconds}s for {method} {url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"aiohttp Client Error for {method} {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in make_request for {method} {url}: {e}", exc_info=True)
        return None

async def register_user(telegram_id: str, full_name: str, username: str = "") -> dict:
    data = {
        "telegram_id": telegram_id,
        "full_name": full_name,
        "username": username
    }
    result = await make_request('POST', CUSTOMER_API_URL, json=data)
    if result:
        logger.info(f"User {telegram_id} registered successfully.")
        return {"success": True, "message": f"Welcome, {full_name}! Registration successful."}
    else:
        logger.error(f"Registration failed for user {telegram_id}.")
        return {"success": False, "message": "Registration failed. Please try again later."}

async def is_user_registered(telegram_id: str) -> bool:
    user_data = await make_request('GET', f"{CUSTOMER_API_URL}{telegram_id}/")
    is_registered = user_data is not None
    logger.debug(f"is_user_registered check for {telegram_id}: {is_registered}")
    return is_registered

async def get_user_details(telegram_id: str) -> Dict | None:
    return await make_request('GET', f"{CUSTOMER_API_URL}{telegram_id}/")

async def get_property_details(property_id: int | str) -> Dict | None:
    return await make_request('GET', f"{PROPERTY_API_URL}{property_id}/")

async def upgrade_user(telegram_id: str, new_user_type: str) -> dict:
    url = f"{CUSTOMER_API_URL}{telegram_id}/"
    data = {"user_type": new_user_type}
    result = await make_request('PATCH', url, json=data)
    if result:
        logger.info(f"User {telegram_id} upgraded to {new_user_type}")
        return {"success": True, "message": "Your account has been upgraded successfully."}
    else:
        logger.error(f"Failed to upgrade user {telegram_id}")
        return {"success": False, "message": "Failed to upgrade account."}

async def get_user_properties(telegram_id: str) -> List[dict]:
    result = await make_request('GET', f"{CUSTOMER_API_URL}{telegram_id}/properties/")
    return result if isinstance(result, list) else []

async def get_user_tours(telegram_id: str) -> List[dict]:
    result = await make_request('GET', f"{TOUR_API_URL}telegram/{telegram_id}/")
    return result if isinstance(result, list) else []

async def get_user_favorites(telegram_id: str) -> List[dict]:
    result = await make_request('GET', f"{CUSTOMER_API_URL}{telegram_id}/favorites/")
    return result if isinstance(result, list) else []

async def get_all_users() -> List[dict]:
    result = await make_request('GET', CUSTOMER_API_URL)
    return result if isinstance(result, list) else []

async def get_non_user_accounts() -> List[dict]:
    all_users = await get_all_users()
    return [user for user in all_users if user and user.get("user_type") in ["agent", "owner", "company"]]

async def get_confirmed_user_properties(telegram_id: str) -> List[dict]:
    user_property_list = await get_user_properties(telegram_id)
    if not user_property_list:
        return []

    tasks = []
    for prop_summary in user_property_list:
        prop_id = prop_summary.get('id')
        if prop_id:
            tasks.append(get_property_details(prop_id))

    if not tasks:
        return []

    properties_details = await asyncio.gather(*tasks)

    return [
        prop for prop in properties_details
        if prop and prop.get("status") == "confirmed"
    ]
