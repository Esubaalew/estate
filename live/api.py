import requests

BASE_URL = 'https://estate.4gmobiles.com/live'


# Add a new request


def create_request(user_id, username, name, phone, address, additional_text):
    data = {
        "user_id": user_id,
        "username": username,
        "name": name,
        "phone": phone,
        "address": address,
        "additional_text": additional_text
    }
    response = requests.post(f'{BASE_URL}/requests/', json=data)
    return response.json() if response.status_code == 201 else None

# Add a new message
def create_message(request_id, sender_id, user_id, content):
    data = {
        "request": request_id,
        "sender_id": sender_id,
        "user_id": user_id,
        "content": content
    }
    response = requests.post(f'{BASE_URL}/messages/', json=data)
    return response.json() if response.status_code == 201 else None

# Get all requests
def get_all_requests():
    response = requests.get(f'{BASE_URL}/requests/')
    return response.json() if response.status_code == 200 else []

# get request by ID
def get_request_details(request_id):
    response = requests.get(f'{BASE_URL}/requests/{request_id}/')
    return response.json() if response.status_code == 200 else None

# get all messages
def get_all_messages():
    response = requests.get(f'{BASE_URL}/messages/')
    return response.json() if response.status_code == 200 else []