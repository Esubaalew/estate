import aiohttp
import asyncio

BASE_URL = 'https://estate-r22a.onrender.com/live'

async def create_request(user_id, username, name, phone, address, additional_text):
    data = {
        "user_id": user_id,
        "username": username,
        "name": name,
        "phone": phone,
        "address": address,
        "additional_text": additional_text
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{BASE_URL}/requests/', json=data) as response:
            return await response.json() if response.status == 201 else None

async def create_message(request_id, sender_id, user_id, content):
    data = {
        "request": request_id,
        "sender_id": sender_id,
        "user_id": user_id,
        "content": content
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{BASE_URL}/messages/', json=data) as response:
            return await response.json() if response.status == 201 else None

async def get_all_requests():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{BASE_URL}/requests/') as response:
            return await response.json() if response.status == 200 else []

async def get_request_details(request_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{BASE_URL}/requests/{request_id}/') as response:
            return await response.json() if response.status == 200 else None

async def get_all_messages():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{BASE_URL}/messages/') as response:
            return await response.json() if response.status == 200 else []
