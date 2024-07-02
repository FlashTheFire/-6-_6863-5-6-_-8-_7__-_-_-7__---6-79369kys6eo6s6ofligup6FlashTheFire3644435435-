import json
import asyncio
import aiohttp
import time
import os
from aiohttp import ClientError

api_key = "UWjSzy23711328951174"
order_file = "CurrentDeposit.json"

get_links = {
    'UPI': {
        "url": f"https://paytm.udayscriptsx.workers.dev/?mid={api_key}&id={{order_id}}"
    }
}

def check_deposit_status(response, server, order_id, user_id):
    try:
        if response.get("STATUS") == "TXN_SUCCESS":
            return {
                'status': 'success',
                'order_id': order_id,
                'server': server,
                'user_id': user_id,
                'data': response
            }
        elif response.get("RESPCODE") == "334":
            return {'status': 'error', 'data': 'NOT:FOUND'}
        else:
            return {'status': 'error', 'data': 'NOT:FOUND'}
    except (KeyError, TypeError) as e:
        return {'status': 'error', 'data': 'NOT:FOUND'}

def load_orders(file_path):
    try:
        with open(file_path, 'r') as file:
            orders = json.load(file)
        if not isinstance(orders, dict):
            orders = {}
    except (FileNotFoundError, json.JSONDecodeError):
        orders = {}
    return orders

def save_orders(file_path, orders):
    with open(file_path, 'w') as file:
        json.dump(orders, file, indent=4)

def add_deposit(file_path, order):
    orders = load_orders(file_path)
    orders[order["order_id"]] = order
    save_orders(file_path, orders)

def remove_deposit(file_path, order_id):
    orders = load_orders(file_path)
    if order_id in orders:
        del orders[order_id]
    save_orders(file_path, orders)

async def check_order_status(session, server, order_id, user_id, start_time, timeout=1800, interval=10):
    urls = get_links[server]
    url = urls["url"].format(order_id=order_id)
    while time.time() - start_time < timeout:
        try:
            async with session.get(url=url, timeout=interval) as response:
                response.raise_for_status()
                response_json = await response.json()
                result = check_deposit_status(response_json, server, order_id, user_id)
                if result['status'] == 'success':
                    return result
                else:
                    return {'status':'waiting'}
        except (ClientError, aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            return {
                "status": "request:failed",
                "message": str(e),
                "server": server,
                "user_id":user_id,
                "order_id": order_id
            }
        except json.JSONDecodeError:
            return {
                "status": "json:decode_error",
                "message": "Error decoding JSON response",
                "server": server,
                "user_id":user_id,
                "order_id": order_id
            }

    return {
        "status": "timeout",
        "message": "No valid response within timeout period",
        "server": server,
        "user_id":user_id,
        "order_id": order_id
    }

async def main_for(file_path):
    from main import recieveDeposit
    while True:
        orders = load_orders(file_path)
        if not orders:
            recieveDeposit("No orders to process. Waiting for new orders.")
            await asyncio.sleep(60)
            continue

        async with aiohttp.ClientSession() as session:
            tasks = [check_order_status(session, order["server"], order_id, order["user_id"], order["time"])
                     for order_id, order in orders.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(results)
            for result in results:
                if isinstance(result, dict):
                    if result.get('status') != 'waiting':
                        recieveDeposit(result)
            await asyncio.sleep(10)

def mainForDeposit(order_file):
    asyncio.run(main_for(order_file))

