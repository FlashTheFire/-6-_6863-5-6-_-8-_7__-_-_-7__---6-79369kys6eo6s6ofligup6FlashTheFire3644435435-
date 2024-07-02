import json
import asyncio
import aiohttp
import time
import os
from aiohttp import ClientError

OrderFile = "CurrentOrders.json"
SERVERS = {
    1: {
        "url": "https://fastsms.su/stubs/handler_api.php",
        "params": lambda api_key, order_id: {"api_key": api_key, "action": "getStatus", "id": order_id},
        "method": "get"
    },
    2: {
        "url": "http://api1.5sim.net/stubs/handler_api.php",
        "params": lambda api_key, order_id: {"api_key": api_key, "action": "getStatus", "id": order_id},
        "method": "get"
    },
    3: {
        "url": "https://smshub.org/stubs/handler_api.php",
        "params": lambda api_key, order_id: {"api_key": api_key, "action": "getStatus", "id": order_id},
        "method": "get"
    },
    4: {
        "url": "https://api.sms-activate.io/stubs/handler_api.php",
        "params": lambda api_key, order_id: {"api_key": api_key, "action": "getStatus", "id": order_id},
        "method": "get"
    }
}

# Function to parse responses
def parse_response(text, server_id, order_id, user_id):
    status_map = {
        "STATUS_OK": ("received", lambda x: x.split(':')[1].strip()),
        "STATUS_WAIT_CODE": ("waiting", lambda x: "waiting"),
        "STATUS_WAIT_RETRY": ("waiting:next", lambda x: "waitingNext"),
        "STATUS_WAIT_RESEND": ("waiting:next", lambda x: "waitingNext"),
        "STATUS_CANCEL": ("canceled", lambda x: "canceled"),
        "NO_ACTIVATION": ("no:activation", lambda x: "noActivation"),
        "ERROR_SQL": ("server:error", lambda x: "serverError"),
        "BAD_KEY": ("bad:key", lambda x: "badKey"),
        "BAD_ACTION": ("bad:action", lambda x: "badAction"),
    }
    
    status, extractor = status_map.get(text.split(':')[0], ("unknown", lambda x: x))
    return {
        'status': status,
        'sms': extractor(text),
        'server': server_id,
        'order_id': order_id,
        'user_id': user_id
    }

def load_orders(file_path):
    try:
        with open(file_path, 'r') as file:
            orders = json.load(file)
        # Ensure that orders is a dictionary
        if not isinstance(orders, dict):
            orders = {}
    except FileNotFoundError:
        orders = {}
    except json.JSONDecodeError:
        orders = {}
    return orders

def save_orders(file_path, orders):
    with open(file_path, 'w') as file:
        json.dump(orders, file, indent=4)

def add_order(file_path, order):
    orders = load_orders(file_path)
    orders[order["order_id"]] = order
    save_orders(file_path, orders)
# Function to remove an order from the JSON file
def remove_order(file_path, order_id):
    orders = load_orders(file_path)
    if order_id in orders:
        del orders[order_id]
    save_orders(file_path, orders)

# Asynchronous function to check order status
async def check_order_status(session, server_id, api_key, order_id, user_id, start_time, timeout=1230, interval=4):
    server = SERVERS[server_id]
    url = server["url"]
    params = server["params"](api_key, order_id)
    
    while time.time() - start_time < timeout:
        try:
            async with session.get(url, params=params, timeout=interval) as response:
                response_text = await response.text()
                #response_text = "STATUS_OK:700211"
                #print(f"{response_text}:{order_id}")
                result = parse_response(response_text, server_id, order_id, user_id)
                if result['status'] == 'received' or result['status'] != 'waiting':
                    result = result
                else:
                    return {'status':'waiting'}
                return result
                #await asyncio.sleep(interval)
        except ClientError as e:
            return {"status": "request:failed", "message": str(e), "server": server_id, "order_id": order_id}
    
    return {"status": "timeout", "message": "No valid response within timeout period", "server": server_id, "order_id": order_id}

async def main_for(file_path):
    from main import recieveMessage

    while True:
        orders = load_orders(file_path)
        if not orders:
            recieveMessage("No orders to process. Waiting for new orders.")
            await asyncio.sleep(20)
            continue

        async with aiohttp.ClientSession() as session:
            tasks = [check_order_status(session, order["server_id"], order["api_key"], order_id, order["user_id"], order["time"]) for order_id, order in orders.items()]
            results = await asyncio.gather(*tasks)
            print(results)
            if results:
                for result in results:
                    if result['status'] != 'waiting' and result['status'] != 'waiting:next':
                        recieveMessage(result)
                    #else:
                        #recieveMessage({"status": "waiting", "order_id": result["order_id"]})
            await asyncio.sleep(4)

def mainForOrders(order_file):
    asyncio.run(main_for(order_file))