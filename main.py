import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, InputTextMessageContent, InlineQueryResultArticle
import time
import requests
import difflib
from telebot import TeleBot, types
import json
from requests.exceptions import RequestException
from typing import Union
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from urllib.parse import urlparse, parse_qs
import re
import phonenumbers
from phonenumbers import NumberParseException
from datetime import datetime, timedelta
from SmsChecker import mainForOrders, remove_order, add_order
import asyncio
import aiohttp
from aiohttp import ClientError
import traceback
import threading
from datetime import datetime, timedelta
import pytz
import random
import threading
from DepositChecker import mainForDeposit, add_deposit, remove_deposit






def load_data(FILENAME,TYPE):
    if TYPE == 'r':
        if os.path.exists(FILENAME):
            with open(FILENAME, TYPE) as file:
                return json.load(file)
        else:
            return {}
         
response = load_data('BotDetails.json','r')
BotToken = response["BotToken"]
comissionPurchase = response["comissionPurchase"]
AdminId = response["AdminId"]
ApiKeyForWeb = response["ApiKeyForWeb"]
smsactivate = ApiKeyForWeb["smsactivate"]
smshub = ApiKeyForWeb["smshub"]
Fivesim = ApiKeyForWeb["5sim"]["v1"]
fivesim = ApiKeyForWeb["5sim"]["v2"]
fastsms = ApiKeyForWeb["fastsms"]
UserDataFile = response["UserDataFile"]
OrderFile = response["OrderFile"]
DepositFile = response["DepositFile"]



bot = telebot.TeleBot(BotToken)


def currentTime():
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    return ist_now.strftime('%Y-%m-%d %I:%M:%S %p')


def AfterMin(minutes):
    utc_now = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)
    ist_future = ist_now + timedelta(minutes=minutes)
    hour = ist_future.hour % 12 or 12
    am_pm = "Aᴍ" if ist_future.hour < 12 else "Pᴍ"
    formatted_time = f"<code>{hour:02}</code><b>:</b><code>{ist_future.minute:02}</code> <code>{am_pm}</code>"
    
    return formatted_time


def convertTime(timestamp):
    utc_time = datetime.utcfromtimestamp(timestamp)
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime('%Y-%m-%d %I:%M:%S %p')
        

def time_ago(buyed_time):
    current_time = currentTime()
    buyed_time_dt = datetime.strptime(buyed_time, "%Y-%m-%d %I:%M:%S %p")
    current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %I:%M:%S %p")
    time_difference = current_time_dt - buyed_time_dt
    days = time_difference.days
    seconds = time_difference.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    months, days = divmod(days, 30)
    
    if months > 0:
        return f"{months} Mᴏɴᴛʜ{'s' if months > 1 else ''} {days} Dᴀʏ{'s' if days > 1 else ''}"
    elif days > 0:
        return f"{days} Dᴀʏ{'s' if days > 1 else ''} {hours} Hᴏᴜʀ{'s' if hours > 1 else ''}"
    elif hours > 0:
        return f"{hours} Hᴏᴜʀ{'s' if hours > 1 else ''} {minutes} Mɪɴᴜᴛᴇ{'s' if minutes > 1 else ''}"
    else:
        return f"{minutes} Mɪɴᴜᴛᴇ{'s' if minutes > 1 else ''} {seconds} Sᴇᴄᴏɴᴅ{'s' if seconds > 1 else ''}"

#START SAVING DATA
wait_time_after_purchase = 10


def load_user_data():
    """Load user data from a JSON file."""
    if not os.path.exists(UserDataFile):
        return {"users": {}}
    try:
        with open(UserDataFile, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": {}}


def save_user_data(data):
    """Save user data to a JSON file."""
    with open(UserDataFile, 'w') as file:
        json.dump(data, file, indent=2)

def update_user(user_id, new_data):
    """Update user data and save it."""
    data = load_user_data()
    user_id = str(user_id)
    if user_id in data['users']:
        data['users'][user_id].update(new_data)
    else:
        pass
    save_user_data(data)


def get_user(user_id):
    """Retrieve user data or initialize it if the user doesn't exist."""
    data = load_user_data()
    user_id = str(user_id)
    if user_id not in data['users']:
        user_name = bot.get_chat(user_id).first_name
        data['users'][user_id] = {
            'username': f'{user_name}',
            'balance': 0,
            'total_numbers_purchased': 0,
            'total_spend': 0,
            'total_deposit_amount': 0,
            'current_deposit_address':{"UPI":"NONE","TRX":"NONE"},
            'deposit': {},
            'orders': {},
            'last_purchase_time': currentTime()
        }
        save_user_data(data)
        
    return data['users'][user_id]




def update_balance(user_id, action_type, amount, method_or_card=None):
    """Update user balance and perform action based on action_type."""
    data = load_user_data()
    user = get_user(user_id)
    current_balance = user['balance']
    if action_type == 'checking':
        if amount > 0 and float(current_balance) <= amount:
            return {'status': 'error', 'message': 'InsufficientBalance', 'balance': f"{current_balance:.2f}"}
        elif amount > 0 and amount <= float(current_balance):
            return {'status': 'success', 'message': 'SufficientBalance'}

    elif action_type == 'purchase':
        last_purchase_time_str = user.get('last_purchase_time')
        if last_purchase_time_str:
            last_purchase_time = datetime.strptime(last_purchase_time_str, '%Y-%m-%d %I:%M:%S %p')
            last_purchase_time = pytz.timezone('Asia/Kolkata').localize(last_purchase_time)
            current_time_now = datetime.now(pytz.timezone('Asia/Kolkata'))
            time_elapsed = current_time_now - last_purchase_time
            if time_elapsed < timedelta(seconds=wait_time_after_purchase):
                wait_time = wait_time_after_purchase - int(time_elapsed.total_seconds())
                return {'status': 'error', 'message': f'{wait_time}'}
        return {'status': 'success', 'message': 'Purchase successful'}

    
    if action_type == 'create':
        user['deposit'][amount] = {
            'amount': 0,
            'datetime':0,
            'status': 'WAITING',
            'server': f'{method_or_card}',
            'time': time.time(),
            'history': [{
                'datetime': currentTime(),
                'action': 'ORDER_CREATED'
            }]
        }
        user['current_deposit_address'][method_or_card] = f"{amount}"
        new_data = {'deposit': user['deposit'],'current_deposit_address':user['current_deposit_address']}
        update_user(user_id, new_data)
        return {'status': 'success','orderId':amount}

    if action_type == 'cancel':
        del user['deposit'][amount] 
        user['current_deposit_address'][method_or_card] = f"NONE"
        new_data = {'deposit': user['deposit'],'current_deposit_address':user['current_deposit_address']}
        update_user(user_id, new_data)
        return {'status': 'success','orderId':amount}
    
    if action_type == 'deposit':
        order_id = method_or_card
        amount = float(amount)
        user['balance'] += amount
        user['total_deposit_amount'] += amount 
        details = user['deposit'][order_id]
        details['status'] = 'CONFIRMED'
        user['current_deposit_address']['UPI'] = "NONE"
        details['amount'] = amount
        details['datetime'] = currentTime()
        details['history'].append({'datetime': currentTime(),'action': 'ORDER_CONFIRMED:ADDED'})
        del details['time']
        new_data = {'balance': user['balance'],'total_dposit_amount':user['total_deposit_amount'],'deposit':user['deposit'],'current_deposit_address':user['current_deposit_address']}
        update_user(user_id, new_data)
        return {'status': 'success','orderId':order_id}
    

def format_message(original_text):
    modified_text = re.sub(r'⏱ Nᴜᴍʙᴇʀ Is Vᴀʟɪᴅ Tɪʟʟ \d{2}:\d{2} [AP]M', '⏱ Number is Cancelled (💰 Refund ).', original_text)
    modified_text_lines = modified_text.splitlines()
    modified_text_lines[0] = f"<blockquote>{modified_text_lines[0]}</blockquote>"
    formatted_text = '\n'.join(modified_text_lines)
    return formatted_text


def manage_order(user_id, order_id, action,amount,server=None,sms=None,number=None, message_id=None,buttonText=None):
    """Create, update, finish, or cancel an order."""
    data = load_user_data()
    user = get_user(user_id)
    
    if action == 'create':
        user['orders'][order_id] = {
            'number': number,
            'message_id':message_id,
            'sms': sms,
            'buttonText':buttonText,
            'status': 'WAITING',
            'datetime': currentTime(),
            'amount': amount,
            'server': server,
            'history': [{
                'datetime': currentTime(),
                'action': 'ORDER_CREATED'
            }]
        }
        user['total_numbers_purchased'] += 1
        user['balance'] += -float(amount)
        user['total_spend'] += +float(amount)
        user['last_purchase_time'] = currentTime()
        new_data = {'balance': user['balance'], 'orders': user['orders'],'total_spend':user['total_spend'],'last_purchase_time': user['last_purchase_time'],'total_numbers_purchased':user['total_numbers_purchased']}
        update_user(user_id, new_data)
        return {'status': 'success','orderId':order_id,'number':number}
    
    elif action == 'update':
        orderId = user['orders'][order_id]
        status = orderId.get('status')
        if order_id in user['orders'] and status not in ['FINISHED','CANCELED'] and orderId.get('status') == 'WAITING':
            current_sms = user['orders'][order_id]['sms']
            if sms not in current_sms:
                orderId['sms'] = f"{current_sms}, {sms}" if orderId['sms'] != 'WAITING' else sms
                orderId['history'].append({'datetime': currentTime(),'action': f"SMS received: {sms}"})
                orderId['status'] = 'WAITING'
                message = {'status':'success','message':'UPDATED'}
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("✆ Sᴍs Lɪsᴛ",switch_inline_query_current_chat=f'#OʀᴅᴇʀIᴅ:{order_id}'),InlineKeyboardButton("↻ Bᴜʏ Aɢᴀɪɴ", callback_data=orderId.get('buttonText')))
                try:
                    bot.edit_message_reply_markup(chat_id=user_id, message_id=orderId.get('message_id'), reply_markup=markup)
                except Exception as e:
                    pass
                new_data = {'orders': user['orders']}
                update_user(user_id,new_data)
                return message
            return {'status':'error','message':'SMS_ALLREDY_RECEVIED'}
        return {'status':'error','message':'ORDER_NOT_FOUND'}
        
    
    elif action == 'cancel':
        if user['orders'][order_id]['status'] != 'FINISHED' and user['orders'][order_id]['status'] == 'WAITING':
            amount_refunded_str = user['orders'][order_id]['amount']
            amount_refunded = float(amount_refunded_str)
            user['balance'] += amount_refunded
            user['total_spend'] -= amount_refunded 
            user['total_numbers_purchased'] -= 1
            #user['orders'][order_id]['status'] = 'REFUNDED'
            #user['orders'][order_id]['sms'] = 'CANCELED'
            #user['orders'][order_id]['history'].append({'datetime': currentTime(),'action': 'ORDER_CANCELED:REFUNDED'})
            del user['orders'][order_id]
            message = {'status': 'success', 'message': 'ORDER_CANCELED:REFUNDED'}
            new_data = {'balance': user['balance'],'orders': user['orders'],'total_spend': user['total_spend'],'total_numbers_purchased':user['total_numbers_purchased']}
            update_user(user_id, new_data)
            return message
        return {'status': 'error', 'message': 'Order not found or cannot be canceled'}
    else:
        return {'status': 'error', 'message': 'Order not found or cannot be canceled'}






# Example usage
#user_id = "user_id1"
#order_id = "order_id1"
#server = "server1"
#sms_received = "SMS received"
# Example of creating an order
#success, message = manage_order(user_id, order_id, 'create', 5, server)
#print(message) if success else print(f"Failed to create order: {message}")
# Example of updating order status
#success, message = manage_order(user_id, order_id, 'update', sms=sms_received)
#print(message) if success else print(f"Failed to update order status: {message}")
# Example of finishing an order
#success, message = manage_order(user_id, order_id, 'finish')
#print(message) if success else print(f"Failed to finish order: {message}")
# Example of canceling an order
#success, message = manage_order(user_id, order_id, 'cancel')
#print(message) if success else print(f"Failed to cancel order: {message}")
# Display user's current state
#user = get_user(user_id)
#print(f"User {user['username']} Balance: {user['balance']}")




#get value
def get_value(mapping, key):
    try:
        if isinstance(mapping[key], list):
            return mapping[key][1]
        else:
            return mapping[key]
    except:
        return None


#start Handle
def startHandle(message,type):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🛒 Sᴇʀᴠɪᴄᴇs",switch_inline_query_current_chat=''),InlineKeyboardButton("🔥 Tᴏᴘ Sᴇʀᴠɪᴄᴇs",callback_data=f"/topService"))
    keyboard.row(InlineKeyboardButton("👨‍💻 Wᴀʟʟᴇᴛ",callback_data=f"USER:PROFILE"),InlineKeyboardButton("💰 Rᴇᴄʜᴀʀɢᴇ",callback_data=f"USER:DEPOSIT"))
    keyboard.row(InlineKeyboardButton("🔗 Rᴇғғᴇʀᴀʟ",callback_data=f"/refferal"),InlineKeyboardButton("🎁 Rᴇᴡᴀʀᴅs",callback_data=f"/rewards"))
    keyboard.row(InlineKeyboardButton("⁉️ Hᴇʟᴘ",callback_data=f"USER:SUPPORT"),InlineKeyboardButton("⚙️ Sᴇᴛᴛɪɴɢs",callback_data=f"/settings"))
    link = 'https://i.postimg.cc/9fyK1yCK/IMG-20240607-023137-160.jpg'
    chat_id = message.chat.id
    first_name = message.chat.first_name
    message_id = message.message_id
    
    user = get_user(chat_id)
    purchase = f"{user['total_numbers_purchased']:.0f}"
    balance = f"{user['balance']:.2f}"
    rank = 'Bronze'
    caption=f'''<b>Hᴇʟʟᴏ</b> {first_name} <b>!</b>

<b>💰 Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ :</b> <code>{balance}</code> 💎
<b>📊 Tᴏᴛᴀʟ Nᴜᴍʙᴇʀ Pᴜʀᴄʜᴀsᴇᴅ :</b> <code>{purchase}</code>

<b>🎰 Yᴏᴜʀ Rᴀɴᴋ :</b> “<code>{rank}</code>”

<b>📌 Rᴀɴᴋ Hᴇʟᴘs Tᴏ Iɴᴄʀᴇᴀsᴇ Dɪsᴄᴏᴜɴᴛ Oɴ Sᴇʀᴠɪᴄᴇs...</b>'''
    if type == "start":
        bot.send_photo(chat_id=chat_id, photo=link, caption=caption,parse_mode="HTML",reply_markup=keyboard)
    elif type == 'edit':
        try:
            bot.edit_message_media(
        media=InputMediaPhoto(media=link, caption=caption, parse_mode='HTML'),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
        )
        except Exception as e:
            return
        
    
#profile image
def get_telegram_profile_photo(bot_token, user_id):
    url = f'https://api.telegram.org/bot{bot_token}/getUserProfilePhotos'
    response = requests.get(url, params={'user_id': user_id, 'limit': 1}).json()
    if response['ok'] and response['result']['total_count'] > 0:
        file_id = response['result']['photos'][0][0]['file_id']
        file_url = f'https://api.telegram.org/bot{bot_token}/getFile'
        file_response = requests.get(file_url, params={'file_id': file_id}).json()
        if file_response['ok']:
            photo_url = f"https://api.telegram.org/file/bot{bot_token}/{file_response['result']['file_path']}"
            photo_response = requests.get(photo_url)
            if photo_response.status_code == 200:
                return Image.open(BytesIO(photo_response.content))
    return None


#edit profile image 
def create_and_send_image(message,landscape_path, user_image, text_position, text_size, text_font_path, bot_token, chat_id, message_id):
    landscape_img = Image.open(landscape_path).convert("RGBA")
    user_id = message.chat.id
    user = get_user(user_id)
    balance = f"{user['balance']:.2f}"
    total_spend = f"{user['total_spend']:.2f}"
    total_deposit = f"{user['total_deposit_amount']:.2f}"
    text = f"""Balance : {float(balance):.0f}
Deposit  : {float(total_deposit):.0f}
Spend    : {float(total_spend):.0f}"""

    if user_image:
        square_size = 165
        user_image = user_image.resize((square_size, square_size), Image.LANCZOS)
        mask = Image.new('L', (square_size, square_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, square_size, square_size), fill=255)
        circular_img = Image.new("RGBA", (square_size, square_size))
        circular_img.paste(user_image, (0, 0), mask)
        circular_position = (275, 168)
        landscape_img.paste(circular_img, circular_position, circular_img)
    draw = ImageDraw.Draw(landscape_img)
    font = ImageFont.truetype(text_font_path, text_size)
    draw.text(text_position, text, font=font, fill="white")
    output_image = BytesIO()
    landscape_img.save(output_image, format='PNG')
    output_image.seek(0)
    API_TOKEN = bot_token
    bot = telebot.TeleBot(API_TOKEN)
    output_image.seek(0)
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("💰 Dᴇᴘᴏsɪᴛ", callback_data='USER:DEPOSIT'),
                 InlineKeyboardButton("📑 Hɪsᴛᴏʀʏ", callback_data="USER:HISTORY"))
    keyboard.row(InlineKeyboardButton("🔙 Bᴀᴄᴋ Tᴏ Hᴏᴍᴇ Pᴀɢᴇ [ Mᴀɪɴ-Mᴇɴᴜ ]", callback_data='MAIN:MENU'))
    caption = f"""<b>🔥 Yᴏᴜʀ Fʟᴀsʜ-Wᴀʟʟᴇᴛ 》</b>

💰 <b>Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ  »</b>  <code>{balance}</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>
📊 <b>Tᴏᴛᴀʟ Sᴘᴇɴᴅ  »</b>  <code>{total_spend}</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>
📈 <b>Tᴏᴛᴀʟ Dᴇᴘᴏsɪᴛ  »</b>  <code>{total_deposit}</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>

📌 <b>Yᴏᴜ Cᴀɴ Rᴇᴄʜᴀʀɢᴇ Yᴏᴜʀ Wᴀʟʟᴇᴛ Fʀᴏᴍ Hᴇʀᴇ.</b>.."""
    try:
        bot.edit_message_media(
        media=InputMediaPhoto(media=output_image, caption=caption, parse_mode='HTML'),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )
    except Exception as e:
        return


#qr code
def qr_code(rect_img_path, order_id, size, position, radius):
    square_img_url = requests.get(f'https://dynamic.udayscriptsx.workers.dev/?data=upi%3A%2F%2Fpay%3Fpa%3Dpaytmqr281005050101nbxw0hx35cpo%40paytm%26pn%3DPaytm%2520Merchant%26tr%3D{order_id}%26tn%3DAdding%2520Fund&body=dot&eye=frame13&eyeball=ball14&col1=121f28&col2=121f28&logo=https://i.postimg.cc/cCrHr3TQ/1000011838-removebg.png').json()['image']
    rect_img = Image.open(rect_img_path)
    response = requests.get(square_img_url)
    square_img = Image.open(BytesIO(response.content)).convert("RGBA")
    square_img = square_img.resize((size, size), Image.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius, fill=255)
    square_img.putalpha(mask)
    rect_img.paste(square_img, position, square_img)
    img_byte_arr = BytesIO()
    rect_img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr



#fetch url
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.replace('\n', '')  # Remove newlines immediately after fetching
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None


#fetch url
def fetch_url(server,status,id):
    if server in ["1","2","3","4"] and status == 'CANCEL':
        status ={
            '1':'8',
            '2':'-1',
            '3':'8',
            '4':'8'
                }
    if server in ["1","2","3","4"] and status == 'NEXT':
        status ={
            '1':'3',
            '2':'3',
            '3':'3',
            '4':'3'
                } 
    if server == "1":
        url = f"https://fastsms.su/stubs/handler_api.php?api_key={fastsms}&action=setStatus&status={status[server]}&id={id}"

    if server == "2":
        url = f"http://api1.5sim.net/stubs/handler_api.php?api_key={fivesim}&action=setStatus&status={status[server]}&id={id}"
            
    if server == "3":
        url = f"https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=setStatus&status={status[server]}&id={id}"

    if server == "4":
        url = f"https://api.sms-activate.io/stubs/handler_api.php?api_key={smsactivate}&action=setStatus&status={status[server]}&id={id}"
            
        
    response = requests.get(url)
    response.raise_for_status()
    response_text = response.text.strip()
    response_mapping = {
        'ACCESS_READY': {'status': 'success', 'message': 'Number ready confirmed'},
        'ACCESS_RETRY_GET': {'status': 'success', 'message': 'Waiting for a new SMS'},
        'STATUS_CANCEL':{'status': 'error', 'message': 'ALLREDY_CANCELED'},
        'ACCESS_ACTIVATION': {'status': 'error', 'message': 'ORDER_FINISHED'},
        'ACCESS_CANCEL': {'status': 'success', 'message': 'ACTIVATION_CANCELED'},
        'ACCESS_CANCEL_ALREADY': {'status': 'error', 'message': 'ALLREDY_CANCELED'},
        'ALREADY_CANCELED': {'status': 'error', 'message': 'ALLREDY_CANCELED'},
        'BAD_ACTION': {'status': 'error', 'message': 'Incorrect action'},
        'BAD_SERVICE': {'status': 'error', 'message': 'Incorrect service name'},
        'BAD_KEY': {'status': 'error', 'message': 'Invalid API key'},
        'NO_ACTIVATION': {'status': 'error', 'message': 'Activation ID does not exist'},
        'TIMED_OUT': {'status': 'error', 'message': 'TIMED_OUT'},
        'ERROR_SQL': {'status': 'error', 'message': 'SQL server database error, contact your administrator'},
        'EARLY_CANCEL_DENIED': {'status': 'error', 'message': 'Not allowed to cancel within first 2 minutes'},
        'BAD_STATUS': {'status': 'error', 'message': 'ALLREDY_CANCELED'},
    }
    return response_mapping.get(response_text, {'status': 'error', 'message': f"Unexpected response: {response_text}"})
    


#fetch service 
def fetch_service(name, service,code):
    urls = [
        f'https://flashsms.in/BotFile/serviceList.php?service={code}',
        f'https://api1.5sim.net/stubs/handler_api.php?api_key={fivesim}&action=getPrices&service={name}',
        f'https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=getPrices&service={service}',
        f'https://api.sms-activate.org/stubs/handler_api.php?api_key={smsactivate}&action=getPrices&service={service}'
    ]
    responses = [fetch_data(url) for url in urls if fetch_data(url)]
    result = {str(i + 1): json.loads(response) for i, response in enumerate(responses)}
    json_result = json.dumps(result, indent=4)
    parsed_result = json.loads(json_result)
    return parsed_result


#sort list 1 and 2
def sort_data_ser1or3(url, server):
    data = requests.get(url).json()
    if server in ['1', '3']:
        multiplier = 86.9565 if server == '3' else 1
        price_map = {}
        for country_code, app_data in data.items():
            for prices in app_data.values():
                for price in prices:
                    adjusted_price = float(price) * float(comissionPurchase) * multiplier
                    price_str = f'{adjusted_price:.2f}'
                    if country_code not in price_map or float(price_map[country_code]) < float(price_str):
                        price_map[country_code] = price_str
        return sorted([{price: [country_code]} for country_code, price in price_map.items()], key=lambda x: float(list(x.keys())[0]))

    output = []
    service = parse_qs(urlparse(url).query)['service'][0]
    if server == '2':
        if service in data:
            for country, products in data[service].items():
                lowest_cost = float('inf')
                lowest_cost_virtual = None
                for virtual_id, info in products.items():
                    cost = info['cost']
                    if cost < lowest_cost:
                        lowest_cost = cost
                        lowest_cost_virtual = virtual_id
                if lowest_cost_virtual:
                    
                    output.append({lowest_cost: [f"{lowest_cost_virtual}_{country}"]})
            output.sort(key=lambda x: list(x.keys())[0])
            return output

    if server == '4':
        cost_id_pairs = [(comissionPurchase * data[service]['cost'], key) for key, data in data.items()]
        sorted_cost_id_pairs = sorted(cost_id_pairs)
        output_data = [{f"{cost:.2f}": [str(id_)]} for cost, id_ in sorted_cost_id_pairs]
        return output_data


#genrate markup
def generate_markup(page,data,server, service, name, buycommand):
    markup = InlineKeyboardMarkup()
    start = page * 5
    end = start + 5
    with open('countriesFlag.json', 'r') as file:
        countryFlags = json.load(file)

    if server in ['1','3','4']:
        for item in data[start:end]:
            for price, ids in item.items():
                for country_code in ids:
                    code = countryFlags['3'].get(country_code, "Unknown")
                    country_names = countryFlags['5'].get(code, 'Unknown').capitalize()
                    if code != 'Unknown':
                        markup.add(InlineKeyboardButton(f" {code} {country_names} ↝ 💎 {price}", callback_data=f"buy_{server} {buycommand} {country_code} {price}  {service} {name} {code}"))

    if server == '2':
        for item in data[start:end]:
            for price, ids in item.items():
                for country_code in ids:
                    virtual_id, country = ids[0].split('_')
                    code = countryFlags['2'].get(country, "Unknown")
                    country_code = country #countryFlags['6'].get(code, "Unknown")
                    if code != "Unknown":
                        price = f'{comissionPurchase * price:.2f}'
                        markup.add(InlineKeyboardButton(f" {code} {country.capitalize()} ↝ 💎 {price}", callback_data=f"buy_{server} {buycommand} {country_code} {price} {service} 1 {code} {virtual_id}"))
        


    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("« Pʀᴇᴠɪᴏᴜs", callback_data=f"prev_{page-1} {server} {service} {name} {buycommand}"))
    if end < len(data):
        nav_buttons.append(InlineKeyboardButton("Nᴇxᴛ »", callback_data=f"next_{page+1} {server} {service} {name} {buycommand}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("↻ Cʜᴀɴɢᴇ Tʜᴇ Sᴇʀᴠᴇʀ", callback_data=f"/Buy_{buycommand}"))
    return markup


def get_history(data, request_type):
    """
    Process order and deposit data based on the request type.
    """
    india_tz = pytz.timezone('Asia/Kolkata')
    current_date = datetime.now(india_tz)

    # Initialize aggregates
    week_total_order_amount = 0.0
    week_total_orders = 0
    week_total_deposit_amount = 0.0

    order_details = []
    deposit_details = []

    # Determine start of the week
    week_start = (current_date - timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    # Process orders
    for order_id, order in data['orders'].items():
        try:
            order_datetime = datetime.strptime(order['datetime'], '%Y-%m-%d %I:%M:%S %p')
            order_datetime = india_tz.localize(order_datetime) if order_datetime.tzinfo is None else order_datetime
            if order_datetime >= week_start:
                week_total_order_amount += float(order['amount'])
                week_total_orders += 1
                order_details.append({'order_id': order_id, 'datetime': order_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': order})
        except Exception as e:
            print(f"Error processing order {order_id}: {e}")

    # Process deposits
    for deposit_id, deposit in data['deposit'].items():
        try:
            if deposit['status'] == "WAITING":
                continue
            deposit_datetime = datetime.strptime(deposit['datetime'], '%Y-%m-%d %I:%M:%S %p')
            deposit_datetime = india_tz.localize(deposit_datetime) if deposit_datetime.tzinfo is None else deposit_datetime
            if deposit_datetime >= week_start:
                week_total_deposit_amount += float(deposit['amount'])
            deposit_details.append({'deposit_id': deposit_id, 'datetime': deposit_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': deposit})
        except Exception as e:
            print(f"Error processing deposit {deposit_id}: {e}")
            
    if request_type == 'OrderWeekDetails':
        return {
            'total_order_amount': week_total_order_amount,
            'total_orders': week_total_orders,
            'total_deposit_amount': week_total_deposit_amount
        }
    elif request_type == 'ORDER:DETAILS':
        return {'orders': order_details}
    elif request_type == 'DEPOSIT:DETAILS':
        return {'deposits': deposit_details}
    elif request_type == 'DEPOSIT:ORDER':
        return {'deposits': deposit_details, 'orders': order_details}
    else:
        raise ValueError("Invalid request type")


def Get_Ser_Price_AD(server, service):
    if server == "1":
        request = sort_data_ser1or3(f'https://flashsms.in/BotFile/serviceList.php?service={service}',"1")
    if server == "2":
        request = sort_data_ser1or3(f'https://api1.5sim.net/stubs/handler_api.php?api_key={fivesim}&action=getPrices&service={service}',"2")
    if server == "3":
        request = sort_data_ser1or3(f'https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=getPrices&service={service}',"3")
    if server == "4":
        request= sort_data_ser1or3(f'https://api.sms-activate.org/stubs/handler_api.php?api_key={smsactivate}&action=getPrices&service={service}',"4")
    return request
    

#format phone number
def format_phone_number(phone_number: str) -> str:
    try:
        parsed_number = phonenumbers.parse(phone_number)
        country_code = f"+{parsed_number.country_code}"
        national_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL).replace(" ", "")
        if national_number.startswith('0') and len(national_number) == 11:
            national_number = national_number[1:]
        return f"<code>{country_code}</code> <code>{national_number}</code>"
    except NumberParseException as e:
        return f"<code>{phone_number}</code>"


#buy number
def get_phone_number_id(server,service, country,price,message, message_id,buttonText,ServiceServer=None):
    user_id = message.chat.id
    if server in ["1","2","3","4"]:
        if server == "1":
            api_key = fastsms
            ser = 1
            url = f"https://fastsms.su/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={service}&country={country}" #&maxPrice={price}

        elif server == "2":
            api_key = fivesim
            ser = 2
            url = f"http://api1.5sim.net/stubs/handler_api.php?api_key={fivesim}&action=getNumber&service={service}&operator={ServiceServer}&country={country}" #&maxPrice={price}
        elif server == "3":
            api_key = smshub
            ser = 3
            url = f"https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=getNumber&service={service}&country={country}" #&maxPrice={price}
        elif server == "4":
            api_key = smsactivate
            ser = 4
            url = f"https://api.sms-activate.io/stubs/handler_api.php?api_key={smsactivate}&action=getNumber&service={service}&country={country}" #&maxPrice={price}

        try:
            response = requests.get(url)
            response_text = response.text
            if response_text.startswith('ACCESS_NUMBER'):
                match = re.match(r'ACCESS_NUMBER:(\d+):(\d+)', response_text)
                if match:
                    id_number = match.group(1)
                    phone_number = format_phone_number(f"+{match.group(2)}")
                    new_order = {"server_id": ser,"api_key":f"{api_key}","order_id":f"{id_number}", "user_id": f"{message.chat.id}","time":time.time()}
                    add_order(OrderFile, new_order)
                    data = manage_order(user_id, id_number, 'create',amount=price,server=server,sms='WATING',number=phone_number, message_id=message_id,buttonText=buttonText)
                    return {
                    'status': 'success',
                    'id': id_number,
                    'number': phone_number,
                    'data':data
                }
            elif response_text == 'WRONG_SERVICE':
                return {'status': 'error', 'message': 'Wrong service specified'}
            elif response_text == 'NO_NUMBERS':
                return {'status': 'error', 'message': 'No numbers available'}
            elif response_text == '':
                return {'status': 'error', 'message': 'Wrong API key'}
            elif response_text == 'NO_BALANCE':
                return {'status': 'error', 'message': 'Insufficient balance'}
            elif response_text == 'API_KEY_NOT_VALID':
                return {'status': 'error', 'message': 'Invalid API key'}
            else:
                return {'status': 'error', 'message': 'Unknown error: ' + response_text}

        except requests.RequestException as e:
            return {'status': 'error', 'message': str(e)}


def get_sms_text_by_code(order_id, sms):
    url = f"https://5sim.net/v1/user/check/{order_id}"
    headers = {
        "Authorization": f"Bearer {Fivesim}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        for code in data.get('sms'):
            if code.get('code') == sms:
                return code.get('text')
    return None

#format message
def format_message(original_text,message):
    modified_text = re.sub(
        r'📞 Nᴜᴍʙᴇʀ ❯ (\+\d+) ([\d\s\(\)\-]+)', 
        r'📞 <b>Nᴜᴍʙᴇʀ ❯</b> <code>\1</code> <code>\2</code>', 
        original_text
    )
    modified_text = re.sub(
        r'⏱ Nᴜᴍʙᴇʀ Is Vᴀʟɪᴅ Tɪʟʟ \d{2}:\d{2} [AP]ᴍ', 
        f'⏱ <b>Nᴜᴍʙᴇʀ Is {message} [</b>💰 <code>Rᴇғᴜɴᴅ</code><b> ]</b>', 
        modified_text
    )
    modified_text_lines = modified_text.splitlines()
    if modified_text_lines:
        modified_text_lines[0] = f"<blockquote><b>{modified_text_lines[0]} </b></blockquote>"
    formatted_text = '\n'.join(modified_text_lines)
    return formatted_text
    

#format message
def format_message(original_text,message):
    modified_text = re.sub(
        r'📞 Nᴜᴍʙᴇʀ ❯ (\+\d+) ([\d\s\(\)\-]+)', 
        r'📞 <b>Nᴜᴍʙᴇʀ ❯</b> <code>\1</code> <code>\2</code>', 
        original_text
    )
    modified_text = re.sub(
        r'⏱ Nᴜᴍʙᴇʀ Is Vᴀʟɪᴅ Tɪʟʟ \d{2}:\d{2} [AP]ᴍ', 
        f'⏱ <b>Nᴜᴍʙᴇʀ Is {message} [</b>💰 <code>Rᴇғᴜɴᴅ</code><b> ]</b>', 
        modified_text
    )
    modified_text_lines = modified_text.splitlines()
    if modified_text_lines:
        modified_text_lines[0] = f"<blockquote><b>{modified_text_lines[0]} </b></blockquote>"
    formatted_text = '\n'.join(modified_text_lines)
    return formatted_text
    

#Recieve Message
def recieveMessage(message):
    #print(f"${time.time()}\n{message}")
    checker = []
    if message == "No orders to process. Waiting for new orders.":
        return
    if message.get('status') == 'timeout':
        remove_order(OrderFile,message.get('order_id'))
        return
    else:
        checker = message.get('status','unknown')
        user_id = message.get('user_id','unknown')
        order_id = message.get('order_id','unknown')
        server = message.get('server','unknown')
        sms = message.get('sms','unknown')
        user = get_user(user_id)
        if order_id in user['orders']:
            order = user['orders'][order_id]
            status = order['status']
            SMS = order['sms']
            message_id = order['message_id']
            number = order['number']
            amount = order['amount']
            history = order['history']
            buttonText = order['buttonText']
        else:
            remove_order(OrderFile,message.get('order_id'))
            return


    # Your code here
    #{'status': status,'sms': extractor(text),'server': server_id,'order_id': order_id,'user_id': user_id}
    if checker == 'received':
        order = manage_order(user_id, order_id,'update',amount,server,sms)
        if order['status'] == 'success' and order['message'] == 'UPDATED':
            text = f'''<blockquote><b>🗨️ Nᴇᴡ Mᴇssᴀɢᴇ Rᴇᴄᴇɪᴠᴇᴅ [ {number} ]</b></blockquote>
<pre><code class="language-• Sᴍs ❯ ">{sms} 
</code></pre>'''
            if server == 2:
                sms_text = get_sms_text_by_code(order_id, sms)
                if sms_text:
                    text += f'\n<pre><code class="language-📨 Mᴇssᴀɢᴇ ❯ ">{sms_text}</code></pre>'
            
            bot.send_message(chat_id=user_id,text=text,parse_mode='HTML',reply_to_message_id=message_id)
            u = fetch_url(f"{server}",'NEXT',order_id)
            if u['status'] == 'error' and u['message'] == 'ORDER_FINISHED':
                remove_order(OrderFile,order_id)
            return
        elif order['status'] == 'error' and order['message'] == 'ORDER_NOT_FOUND':
            remove_order(OrderFile,order_id)
        elif order['status'] == 'error' and order['message'] == 'SMS_ALLREDY_RECEVIED':
            u = fetch_url(f"{server}",'NEXT',order_id)
            if u['status'] == 'error' and u['message'] == 'ORDER_FINISHED':
                remove_order(OrderFile,order_id)#TIMED_OUT
            

    if checker == 'canceled':
        remove_order(OrderFile,order_id)
        if not SMS.startswith('WATING,') and status not in ['FINISHED', 'CANCELED', 'REFUNDED', 'EXPIRED'] and 'SMS received' not in history:
            amount_refunded = float(amount)
            user['balance'] += amount_refunded
            user['total_spend'] -= amount_refunded 
            order['status'] = 'REFUNDED'
            order['sms'] = 'EXPIRED'
            history.append({'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'action': 'ORDER_EXPIRED:REFUNDED'})
            new_data = {'balance': user['balance'],'orders': user['orders'],'total_spend': user['total_spend']}
            update_user(user_id, new_data)
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("↻ Bᴜʏ Nᴇᴡ Nᴜᴍʙᴇʀ Aɢᴀɪɴ [ Bᴜʏ Sᴇʀᴠɪᴄᴇ ]",callback_data=buttonText))
            textU = '<blockquote><b>⌛ Tʜɪs Nᴜᴍʙᴇʀ Hᴀs Exᴘɪʀᴇᴅ, Aɴᴅ Tʜᴇ Rᴇғᴜɴᴅ Hᴀs Bᴇᴇɴ Cʀᴇᴅɪᴛᴇᴅ Tᴏ Yᴏᴜʀ Aᴄᴄᴏᴜɴᴛ!</b></blockquote>'
            texts = f'''<blockquote><b>🗑️ Tʜɪs Nᴜᴍʙᴇʀ Is Exᴘɪʀᴇᴅ! [💰 Rᴇғᴜɴᴅ]</b> </blockquote>

<b>📞 Nᴜᴍʙᴇʀ ❯</b> {number}

⏱<b> Nᴜᴍʙᴇʀ Is Exᴘɪʀᴇᴅ [</b> <code>💰 Rᴇғᴜɴᴅ</code> <b>]</b>'''
            bot.send_message(chat_id=user_id,text=textU,reply_to_message_id=message_id,parse_mode='HTML')
            bot.edit_message_text(chat_id=user_id,text=texts, message_id=message_id,parse_mode='HTML',reply_markup=keyboard)
            return


def recieveDeposit(message):
    #print(message)
    if message == "No orders to process. Waiting for new orders.":
        return

    remove_order(DepositFile,message.get('order_id'))
    user_id = message.get('user_id')
    order_id = message.get('order_id')
    if message.get('status') == 'timeout':
        
        update_balance(user_id, 'cancel', order_id,'UPI')
        return

    data = message.get('data')
    server = message.get('server')
    amount = data['TXNAMOUNT']
    paid_from = data['GATEWAYNAME']
    paid_type = data['PAYMENTMODE']
    date = data['TXNDATE']
    update_balance(user_id, 'deposit', amount, order_id)
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🛒 Bᴜʏ Sᴇʀᴠɪᴄᴇ Nᴏᴡ",switch_inline_query_current_chat=''))
    text = f"""<b>#Uᴘɪ_Cᴀʀᴅ_Dᴇᴘᴏsɪᴛ ❯</b>

<b>Tʀᴀɴsᴀᴄᴛɪᴏɴ Dᴇᴛᴀɪʟs</b>
<b>💰 Aᴍᴏᴜɴᴛ Cʀᴇᴅɪᴛᴇᴅ »</b> <code>{amount}</code> 💎  
<b>💳 Oʀᴅᴇʀ Iᴅ »</b> <code>{order_id}</code>
<b>👤 Pᴀɪᴅ Fʀᴏᴍ »</b> <code>{paid_from}</code>
<b>🕊 Pᴀʏᴍᴇɴᴛ Tʏᴘᴇ »</b> <code>{paid_type}</code>

<b>🏛️ Bᴀʟᴀɴᴄᴇ Uᴘᴅᴀᴛᴇ 》</b>
<i>Sᴜᴄᴄᴇssғᴜʟʟʏ Cʀᴇᴅɪᴛᴇᴅ</i> <code>{amount}</code> 💎 
<i>Tᴏ Yᴏᴜʀ Aᴄᴄᴏᴜɴᴛ.</i>"""
    bot.send_message(chat_id=user_id,text=text,parse_mode='HTML',reply_markup=keyboard)
























def update_progress(progress):
    bar_length = 10
    block = int(round(bar_length * progress))
    progress_bar = '[{}{}] {:.0f}%'.format('■' * block, '□' * (bar_length - block), progress * 100)
    return progress_bar

def handle_auto_check(call, user_id, server, code, country, price, msg, call_data, operate):
    bar = {
        "search": {1: "🔎", 2: "🔍", 3: "🔎", 4: "🔍", 5: "🔎", 6: "🔍", 7: "🔎", 8: "🔍", 9: "🔎", 10: "🔍"},
        "time": {1: "⏳", 2: "⌛", 3: "⏳", 4: "⌛", 5: "⏳", 6: "⌛", 7: "⏳", 8: "⌛", 9: "⏳", 10: "⌛"},
        "loading": {1: "↺", 2: "⟲", 3: "↻", 4: "⟳", 5: "↺", 6: "⟲", 7: "↻", 8: "⟳", 9: "↺", 10: "⟲"}
    }
    
    start_time = time.time()
    max_attempts = 10
    attempts = 0
    checker = False

    while attempts < max_attempts and (time.time() - start_time) < 10:
        result = get_phone_number_id(server, code, country, price, call.message, msg, call_data, operate)
        if result['status'] == 'success':
            checker = True
            break
        
        progress = attempts / max_attempts
        progress_bar = update_progress(progress)
        attempts += 1
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton(f"{bar.get('loading')[attempts]} Aᴜᴛᴏ Cʜᴇᴄᴋɪɴɢ [Aᴛᴛᴇᴍᴘᴛ ({attempts})]", callback_data=f'{call.data}'))

        try:
            bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"{bar.get('time')[attempts]} <b>Wᴇ Tʀʏɪɴɢ Tᴏ Gᴇᴛ Nᴜᴍʙᴇʀs!</b>\n\n<code>{progress_bar}</code>\n\n<b>{bar.get('search')[attempts]} Bᴜʏɪɴɢ Iɴ Pʀᴏɢʀᴇss</b>", parse_mode='html', reply_markup=keyboard)
        except Exception as e:
            print(e)
            pass

    if attempts == max_attempts:
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🐼 Eɴᴀʙʟᴇ Aᴜᴛᴏ Cʜᴇᴄᴋ Aɢᴀɪɴ [ Aᴛᴛᴇᴍᴘᴛ ]", callback_data=f'{call.data}'))
        bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"""👨🏻‍💻 <b>Wᴇ'ʀᴇ Sᴏʀʀʏ! Aᴛ Tʜɪs Mᴏᴍᴇɴᴛ!</b>

<i>✘ Tʜᴇʀᴇ Aʀᴇ Nᴏ Nᴇᴡ Nᴜᴍʙᴇʀs Aᴠᴀɪʟᴀʙʟᴇ. Pʟᴇᴀsᴇ Tʀʏ Aɢᴀɪɴ Lᴀᴛᴇʀ.</i>""", parse_mode='html', reply_markup=keyboard)

    if checker:
        print('done')

    return






#Open User History
@bot.callback_query_handler(func=lambda call: call.data.startswith('USER:SUPPORT'))
def callback_inline(call):
    parts = call.data.split()
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🛒 Oʀᴅᴇʀ Hɪsᴛᴏʀʏ", switch_inline_query_current_chat=''),
                 InlineKeyboardButton("💰 Dᴇᴘᴏsɪᴛ Hɪsᴛᴏʀʏ", switch_inline_query_current_chat=''))
    keyboard.row(InlineKeyboardButton("🔙 Bᴀᴄᴋ Tᴏ Pʀᴏғɪʟᴇ Pᴀɢᴇ [ Usᴇʀ-Pʀᴏғɪʟᴇ ] ", callback_data='MAIN:MENU'))
    purchase = 1
    caption = f"""<b>⁉️ Fʟᴀsʜ Hᴇʟᴘ Gᴜɪᴅᴇ</b> <b>[ </b><code>Hᴏᴡ ᴛᴏ Usᴇ</code><b> ]</b>

<b>𝟷.</b> <b>Sᴇʟᴇᴄᴛ Tʜᴇ Sᴇʀᴠɪᴄᴇ ❯</b>
<code>Cʜᴏᴏsᴇ Tʜᴇ Sᴇʀᴠɪᴄᴇ Yᴏᴜ Wɪsʜ Tᴏ Pᴜʀᴄʜᴀsᴇ.</code>
<b>𝟸.</b> <b>Cʜᴏᴏsᴇ Tʜᴇ Sᴇʀᴠᴇʀ ❯</b>
<code>Sᴇʟᴇᴄᴛ Tʜᴇ Sᴇʀᴠᴇʀ Fᴏʀ Tʜᴇ Cʜᴏsᴇɴ Sᴇʀᴠɪᴄᴇ.</code>
<b>𝟹.</b> <b>Pɪᴄᴋ Tʜᴇ Cᴏᴜɴᴛʀʏ ❯</b>
<code>Sᴘᴇᴄɪғʏ Tʜᴇ Cᴏᴜɴᴛʀʏ Fᴏʀ Tʜᴇ Sᴇʀᴠɪᴄᴇ.</code>
<b>𝟺.</b> <b>Cᴏɴғɪʀᴍ Yᴏᴜʀ Oʀᴅᴇʀ ❯</b>
<code>Rᴇᴠɪᴇᴡ Aɴᴅ Cᴏɴғɪʀᴍ Yᴏᴜʀ Oʀᴅᴇʀ Dᴇᴛᴀɪʟs.</code>
<b>𝟻.</b> <b>Rᴇᴄᴇɪᴠᴇ Yᴏᴜʀ Nᴜᴍʙᴇʀ ❯</b>
<code>Yᴏᴜ Wɪʟʟ Rᴇᴄᴇɪᴠᴇ A Nᴜᴍʙᴇʀ, Vᴀʟɪᴅ Fᴏʀ 20 Mɪɴᴜᴛᴇs.</code>

<b>📌 Nᴇᴇᴅ Assɪsᴛᴀɴᴄᴇ.!?</b>  
<i>Fᴇᴇʟ Fʀᴇᴇ Tᴏ Cᴏɴᴛᴀᴄᴛ Us Fᴏʀ Aɴʏ Hᴇʟᴘ Oʀ Sᴜᴘᴘᴏʀᴛ...</i>"""
    try:
        bot.edit_message_media(media=InputMediaPhoto(media='https://i.postimg.cc/9QH9VNky/20240628-203445.jpg', caption=caption, parse_mode='HTML'),chat_id=chat_id,message_id=message_id,reply_markup=keyboard)
    except Exception as e:
        return
    return
        

#Open User History
@bot.callback_query_handler(func=lambda call: call.data.startswith('USER:HISTORY'))
def callback_inline(call):
    parts = call.data.split()
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🛒 Oʀᴅᴇʀ Hɪsᴛᴏʀʏ", switch_inline_query_current_chat=''),
                 InlineKeyboardButton("💰 Dᴇᴘᴏsɪᴛ Hɪsᴛᴏʀʏ", switch_inline_query_current_chat=''))
    keyboard.row(InlineKeyboardButton("🔙 Bᴀᴄᴋ Tᴏ Pʀᴏғɪʟᴇ Pᴀɢᴇ [ Usᴇʀ-Pʀᴏғɪʟᴇ ] ", callback_data='USER:PROFILE'))

    user = get_user(chat_id)
    history = get_history(user, 'getData')
    number = history['total_orders']
    amount = history['total_order_amount']
    deposit = history['total_deposit_amount']
    caption = f"""🔥 <b>Fʟᴀsʜ Tʀᴀɴsᴀᴄᴛɪᴏɴ Hɪsᴛᴏʀʏ 》</b>

🔍 <b>Hᴇʀᴇ Yᴏᴜ Cᴀɴ Vɪᴇᴡ Aʟʟ Yᴏᴜʀ Pᴀsᴛ Tʀᴀɴsᴀᴄᴛɪᴏɴs.</b>

<b>📅 Tʜɪs Wᴇᴇᴋ ❯</b>
💰 <b>Pᴜʀᴄʜᴀsᴇs  »</b>  <code>{number}</code> <code>Nᴜᴍʙᴇʀ{'s' if number > 1 else ''}</code>
📊 <b>Sᴘᴇɴᴅ  »</b>  <code>{amount:.2f}</code> 💎  〚$ <code>0.00</code>〛
📈 <b>Dᴇᴘᴏsɪᴛs  »</b>  <code>{deposit:.2f}</code> 💎  〚$ <code>0.00</code>〛

🏛️ <b>Yᴏᴜ Cᴀɴ Sᴇᴀʀᴄʜ Yᴏᴜʀ Tʀᴀɴsᴀᴄᴛɪᴏɴs Bʏ Dᴀᴛᴇ Aɴᴅ Tʏᴘᴇ. Tʜɪs Wɪʟʟ Hᴇʟᴘ Yᴏᴜ Eᴀsɪʟʏ Aɴᴀʟʏᴢᴇ Yᴏᴜʀ Fᴜᴛᴜʀᴇ Fɪɴᴀɴᴄᴇs..</b>."""
    try:
        bot.edit_message_media(media=InputMediaPhoto(media='https://i.postimg.cc/HLWC80bf/20240628-092309.jpg', caption=caption, parse_mode='HTML'),chat_id=chat_id,message_id=message_id,reply_markup=keyboard)
    except Exception as e:
        return
    return


#Open User Profile
@bot.callback_query_handler(func=lambda call: call.data.startswith('USER:DEPOSIT:QR'))
def callback_inline(call):
    parts = call.data.split()
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ Cʜᴇᴄᴋ Pᴀʏᴍᴇɴᴛ", callback_data='USER:DEPO SIT'),
                 InlineKeyboardButton("ⓘ Hᴇʟᴘ & Sᴜᴘᴘᴏʀᴛ", callback_data="USER:HISTO RY"))
    keyboard.row(InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Dᴇᴘᴏsɪᴛ Pᴀɢᴇ [ Dᴇᴘᴏsɪᴛ-Mᴇɴᴜ ]", callback_data='USER:DEPOSIT'))
    
    caption = f"""<b>🔥 Yᴏᴜʀ Fʟᴀsʜ Qʀ-Cᴏᴅᴇ 》</b>

💰 <b>Mɪɴ Aᴍᴏᴜɴᴛ  »</b>  <code>₹⩇⩇</code>   <code>〚</code><code>⩇⩇💎</code><code>〛</code>
💳 <b>Oʀᴅᴇʀ Iᴅ  »</b>  [ <code>⩇⩇⩇⩇⩇⩇⩇⩇⩇⩇⩇⩇</code> ]
⏳ <b>Pᴀʏ Uɴᴅᴇʀ  »</b>  <code>⩇⩇:⩇⩇</code> <code>Mɪɴᴜᴛᴇs</code>

📌 <b>Sᴄᴀɴ Tʜɪs Qʀ Aɴᴅ Pᴀʏ Fʀᴏᴍ Aɴʏ Pᴀʏᴍᴇɴᴛ Aᴘᴘ.</b>.."""
    try:
        bot.edit_message_media(
        media=InputMediaVideo(media=f'https://t.me/imagesvideogif/10', caption=caption, parse_mode='HTML'),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )
    except Exception as e:
        return
    user = get_user(chat_id)
    current_deposit_address = user['current_deposit_address']['UPI']
    deposit = user['deposit']
    details = deposit.get(current_deposit_address,None)
    order_id = int(str(int(f"{str(str(time.time())[7:14]).replace('.', '')}{str(chat_id)[:5]}"))[::-1])
    if current_deposit_address == "NONE":
        details = {"order_id":f"{order_id}", "user_id": f"{chat_id}","server":"UPI","time":time.time()}
        add_deposit(DepositFile, details)
        update_balance(chat_id, 'create', order_id,'UPI')
    elif time.time() < details['time']+1800:
        order_id = current_deposit_address

    else:
        details = {"order_id":f"{order_id}", "user_id": f"{chat_id}","server":"UPI","time":time.time()}
        add_deposit(DepositFile, details)
        update_balance(chat_id, 'create', order_id,'UPI')
        
    caption = f"""<b>🔥 Yᴏᴜʀ Fʟᴀsʜ Qʀ-Cᴏᴅᴇ 》</b>

💰 <b>Mɪɴ Aᴍᴏᴜɴᴛ  »</b>  <code>₹1⩇</code>   <code>〚</code><code>1⩇💎</code><code>〛</code>
💳 <b>Oʀᴅᴇʀ Iᴅ  »</b>  [ <code>{order_id}</code> ]
⏳ <b>Pᴀʏ Uɴᴅᴇʀ  »</b>  <code>{convertTime(details['time']+1800)}</code>

📌 <b>Sᴄᴀɴ Tʜɪs Qʀ Aɴᴅ Pᴀʏ Fʀᴏᴍ Aɴʏ Pᴀʏᴍᴇɴᴛ Aᴘᴘ.</b>.."""
    image = qr_code('qr_code.jpg', order_id, 380, (1470, 550), 20)
    try:
        bot.edit_message_media(media=InputMediaPhoto(media=image, caption=caption, parse_mode='HTML'),chat_id=chat_id,message_id=message_id,reply_markup=keyboard)
    except Exception as e:
        return
    
    return




#Buy Checking List 2
def get_country_server_2(service: str,country_flags, data,comissionPurchase) -> Union[bool, tuple]:
    try:
        if data is None:
            return None, None #ValueError("Data is None, cannot proceed with get_country_server_2")
        
        if not data.get('status', True):
            return None, None
        
        countries = data.get(service, {})
        virtual_data = sorted(
            [(cn, vi['cost'], vi['count']) for cn, ci in countries.items() for vk, vi in ci.items() if 'virtual' in vk],
            key=lambda x: (x[1], -x[2])
        )
        
        top_3_country_names = [country[0] for country in virtual_data[:3]]
        more_countries = len(virtual_data) > 3
        displayed_countries = top_3_country_names if not more_countries else top_3_country_names + [" ..."]
        lowest_price = virtual_data[0][1] if virtual_data else None
        top_3_country_emojis = [country_flags.get(name, name) for name in displayed_countries]
        
        result_str = "[" + ",".join(top_3_country_emojis) + "]"
        return result_str, f"{lowest_price * comissionPurchase:.2f}"
    
    except (RequestException, ValueError, KeyError) as e:
        print(f"Error fetching data: {e}")
        return None, None

#Buy Checking List 3 or 1
def get_country_server_1or3(service,country_flags, service_data,comissionPurchase,serVer):
    if not service_data:
        return None, None
    if service_data == "null":
        return None, None
    prices = [(country_code, float(next(iter(services[service]))), int(next(iter(services[service].values())))) 
              for country_code, services in service_data.items() if service in services]
    if not prices:
        return None, None
    sorted_prices = sorted(prices, key=lambda x: (x[1], x[2]))
    top_3_country_codes = [price[0] for price in sorted_prices[:3]]
    top_1_lowest_price = sorted_prices[0][1] if sorted_prices else None
    top_3_country_flags = [country_flags.get(code, code) for code in top_3_country_codes]
    if len(top_3_country_flags) == 3:
        top_3_country_flags = top_3_country_flags + [' ...']

    if serVer == "3":
        top_1_lowest_price = top_1_lowest_price * 86.9565
    return "[" + ",".join(top_3_country_flags) + "]", f"{top_1_lowest_price * comissionPurchase:.2f}"

    
#Buy Checking List 4
def get_country_server_4(service, flags, data, comissionPurchase,top_n=3):
    return None, None
    if not data:
        return None, None
    costs = [(id, details[service]['cost']) for id, details in data.items()]
    if not costs:
        return None, None
    sorted_costs = sorted(costs, key=lambda x: x[1])
    top_n_lowest = sorted_costs[:top_n]
    lowest_cost = sorted_costs[0]
    top_n_lowest_with_flags = [flags[id] for id, cost in top_n_lowest]
    lowest_cost_value = lowest_cost[1]
    if len(sorted_costs) > top_n:
        top_n_lowest_with_flags.append('...')
    top_n_lowest_with_flags_str = ", ".join(top_n_lowest_with_flags)
    top_n_lowest_with_flags_str = f"[{top_n_lowest_with_flags_str}]"
    return top_n_lowest_with_flags_str, f"{lowest_cost_value * comissionPurchase:.2f}"

#edit menu
@bot.callback_query_handler(func=lambda call: call.data.startswith('MAIN:MENU'))
def edit_welcome(call):
    startHandle(call.message,'edit')
    return

#open menu
@bot.message_handler(commands=['start'])
def send_welcome(message):
    startHandle(message,'start')
    return 


#Open User Profile
@bot.callback_query_handler(func=lambda call: call.data.startswith('USER:PROFILE'))
def callback_inline(call):
    parts = call.data.split()
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("💰 Dᴇᴘᴏsɪᴛ", callback_data='USER:DEPOSIT'),
                 InlineKeyboardButton("📑 Hɪsᴛᴏʀʏ", callback_data="USER:HISTORY"))
    keyboard.row(InlineKeyboardButton("🔙 Bᴀᴄᴋ Tᴏ Hᴏᴍᴇ Pᴀɢᴇ [ Mᴀɪɴ-Mᴇɴᴜ ]", callback_data='MAIN:MENU'))
    
    caption = """<b>🔥 Yᴏᴜʀ Fʟᴀsʜ-Wᴀʟʟᴇᴛ 》</b>

💰 <b>Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ  »</b>  <code>0</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>
📊 <b>Tᴏᴛᴀʟ Sᴘᴇɴᴅ  »</b>  <code>0</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>
📈 <b>Tᴏᴛᴀʟ Dᴇᴘᴏsɪᴛ  »</b>  <code>0</code> 💎  <code>〚</code><b>$</b> <code>0.00</code><code>〛</code>

📌 <b>Yᴏᴜ Cᴀɴ Rᴇᴄʜᴀʀɢᴇ Yᴏᴜʀ Wᴀʟʟᴇᴛ Fʀᴏᴍ Hᴇʀᴇ.</b>.."""
    try:
        bot.edit_message_media(
        media=InputMediaVideo(media=f'https://t.me/imagesvideogif/10', caption=caption, parse_mode='HTML'),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )
    except Exception as e:
        return
    landscape_url = 'ProfileImage.png'
    text_position = (247, 430)
    text_size = 40
    text_font_path = 'NewtonHowardFont.ttf'
    user_image = get_telegram_profile_photo(BotToken, chat_id)
    create_and_send_image(call.message,landscape_url, user_image, text_position, text_size, text_font_path, BotToken, chat_id,message_id)
    return


#cancel order 
@bot.callback_query_handler(func=lambda call: call.data.startswith('CHANGE:STATUS'))
def change_order_status(call):
    if call.data.startswith("CHANGE:STATUS:CANCEL"):
        keyboard = InlineKeyboardMarkup()
        buttonText = call.message.reply_markup.keyboard[0][1].callback_data
        keyboard.row(InlineKeyboardButton("↻ Bᴜʏ Nᴇᴡ Nᴜᴍʙᴇʀ Aɢᴀɪɴ [ Bᴜʏ Sᴇʀᴠɪᴄᴇ ]",callback_data=buttonText))
        
        parts = call.data.split()
        user_id = parts[1] if len(parts) > 1 else None
        order_id = parts[2] if len(parts) > 2 else None
        if order_id and user_id:
            user = get_user(user_id)
            try:
                order_data = user['orders'][order_id]
                number = order_data.get('number')
                sms = order_data.get('sms')
                status = order_data.get('status')
                amount = order_data.get('amount')
                server = order_data.get('server')
            except KeyError as e:
                print(e)
                return
            if status == 'REFUNDED':
                try:
                    bot.answer_callback_query(call.id, f"🔎 Tʜᴇ Nᴜᴍʙᴇʀ Is Cᴀɴᴄᴇʟʟᴇᴅ Aʟʀᴇᴀᴅʏ Aɴᴅ Rᴇғᴜɴᴅ Wᴀs Sᴜᴄᴄᴇssғᴜʟʟʏ Iɴɪᴛɪᴀᴛᴇᴅ...",show_alert=True)
                except Exception as e:
                    pass
                return
            else:
                msg = bot.reply_to(call.message, text="⏳ <b>Cᴀɴᴄᴇʟʟᴀᴛɪᴏɴ Iɴ Pʀᴏɢʀᴇss..</b>.", parse_mode='html').message_id
            
            request = fetch_url(server,'CANCEL',order_id)

            
            if request['status'] == 'success' and request['message'] == 'ACTIVATION_CANCELED':
                bot.edit_message_text(chat_id=user_id, message_id=msg, text="🔎 <b>Rᴇǫᴜᴇsᴛɪɴɢ Sᴇʀᴠᴇʀ Fᴏʀ Oʀᴅᴇʀ..</b>.", parse_mode='html')
                
                checker = manage_order(user_id, order_id, 'cancel',amount)
                if checker['status'] == 'success' and checker['message'] == 'ORDER_CANCELED:REFUNDED':
                    bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"<blockquote><b>⚡Oʀᴅᴇʀ Hᴀs Bᴇᴇɴ Cᴀɴᴄᴇʟʟᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ, Aɴᴅ Tʜᴇ Rᴇғᴜɴᴅ Hᴀs Bᴇᴇɴ Cʀᴇᴅɪᴛᴇᴅ Tᴏ Yᴏᴜʀ Aᴄᴄᴏᴜɴᴛ!</b></blockquote>", parse_mode='html')
                    text = format_message(call.message.text,'Cᴀɴᴄᴇʟʟᴇᴅ')
                    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=text, parse_mode='html',reply_markup=keyboard)
                    remove_order(OrderFile,order_id)
                    return
            
            
            if request['message'] == 'ALLREDY_CANCELED':
                bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"🔎 <b>Tʜᴇ Nᴜᴍʙᴇʀ Is Cᴀɴᴄᴇʟʟᴇᴅ Aʟʀᴇᴀᴅʏ Aɴᴅ Rᴇғᴜɴᴅ Wᴀs Sᴜᴄᴄᴇssғᴜʟʟʏ Iɴɪᴛɪᴀᴛᴇᴅ..</b>.", parse_mode='html')
                return

            
            if request['message'] != 'ACTIVATION_CANCELED':
                bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"🔎 <b>{request['message']}..</b>.", parse_mode='html')
                
            return



#Open User Deposit 
@bot.callback_query_handler(func=lambda call: call.data.startswith('USER:DEPOSIT'))
def callback_inline(call):
    parts = call.data.split()
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    keyboard = InlineKeyboardMarkup()
    Trx = InlineKeyboardButton("🪙 Tʀx",callback_data=f"/Trx")
    Redeem = InlineKeyboardButton(
    "🏆 Rᴇᴅᴇᴇᴍ",callback_data=f"/Redeem")
    Inr = InlineKeyboardButton("💰 Iɴʀ",callback_data=f"USER:DEPOSIT:QR")
    keyboard.row(Trx, Redeem, Inr)
    keyboard.row(InlineKeyboardButton("🔙 Bᴀᴄᴋ Tᴏ Hᴏᴍᴇ Pᴀɢᴇ [ Mᴀɪɴ-Mᴇɴᴜ ]", callback_data='MAIN:MENU'))
    
    caption = """<b>🔥 Fʟᴀsʜ Dᴇᴘᴏsɪᴛ Pᴀɢᴇ 》</b>
<b>Hᴇʀᴇ Yᴏᴜ Cᴀɴ Aᴅᴅ Fᴜɴᴅs Tᴏ Yᴏᴜʀ Wᴀʟʟᴇᴛ!</b>

<code>❒</code> <code>1</code> <b>Iɴʀ</b>   <b>»</b> <code>1</code> 💎 <b>||</b> <code>1</code> Tʀx  <b>»</b> <code>10</code> 💎

➕ <b>Sᴇʟᴇᴄᴛ Dᴇᴘᴏsɪᴛ Mᴇᴛʜᴏᴅ, Aʟʟ Dᴇᴘᴏsɪᴛ Aᴍᴏᴜɴᴛ Wɪʟʟ Bᴇ Cᴏɴᴠᴇʀᴛᴇᴅ Tᴏ Pᴏɪɴᴛ</b><code>(</code><code>💎</code><code>)</code>"""
    try:
        bot.edit_message_media(
        media=InputMediaPhoto(media='https://i.postimg.cc/hGZ2G2v5/IMG-20240620-025944-733.jpg', caption=caption, parse_mode='HTML'),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )
    except Exception as e:
        print(e)
        return
    return



# Callback query handler
@bot.callback_query_handler(func=lambda call: call.data.startswith('next_') or call.data.startswith('prev_') or call.data.startswith('buy_'))
def callback_query(call):
    if call.data.startswith("next_") or call.data.startswith("prev_"):
        parts = call.data.split()
        server = parts[1] if len(parts) > 1 else None
        service = parts[2] if len(parts) > 2 else None
        name = parts[3] if len(parts) > 3 else service
        buycommand = parts[4] if len(parts) > 4 else None
        
        page = int(call.data.split('_')[1].split()[0])
        SerName = server.replace('1', '𝟷').replace('2', '𝟸').replace('3', '𝟹').replace('4', '𝟺')
        request = Get_Ser_Price_AD(server, service)
        text = f"<b>⦿ Sᴇʀᴠɪᴄᴇ ❯</b> {name} <b>〔{SerName}〕 \n\n↓ Cʜᴏᴏsᴇ Cᴏᴜɴᴛʀʏ Bᴇʟᴏᴡ</b>"
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=text, reply_markup=generate_markup(page, request,server, service, name,buycommand),parse_mode='html')
        except Exception as e:
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,text=text,reply_markup=generate_markup(page+1, request,server, service, name,buycommand),parse_mode='html')
            except Exception as e:
                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,text=text,reply_markup=generate_markup(page-1, request,server, service, name,buycommand),parse_mode='html')
                except Exception as e:
                    print(e)
                    return
    else:
        user_id = call.message.chat.id
        msg = bot.send_message(user_id,f"⏳ <b>Oʀᴅᴇʀɪɴɢ Iɴ Pʀᴏɢʀᴇss..</b>.", parse_mode='html'). message_id
        parts = call.data.split()
        server = call.data.split('_')[1].split()[0]
        SerName = server.replace('1', '𝟷').replace('2', '𝟸').replace('3', '𝟹').replace('4', '𝟺')
        buycommand = parts[1] if len(parts) > 1 else None
        country = parts[2] if len(parts) > 2 else None
        price = parts[3] if len(parts) > 3 else None
        code = parts[4] if len(parts) > 4 else None
        service = parts[5] if len(parts) > 5 else code
        flag = parts[6] if len(parts) > 6 else None
        operate = parts[7] if len(parts) > 7 else None
        if service == '1':
            service = str(f"{code}").capitalize()
        checking = update_balance(user_id, 'checking', float(price))
        bot.edit_message_text(chat_id=user_id, message_id=msg, text="🔎 <b>Rᴇǫᴜᴇsᴛɪɴɢ Sᴇʀᴠᴇʀ Fᴏʀ Oʀᴅᴇʀ..</b>.", parse_mode='html')
        if checking['status'] == 'success':
            checker = update_balance(user_id, 'purchase',price)

            if checker['status'] == 'error':
                if checker['message']:
                    try:
                        bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"⏳ <b>Yᴏᴜ Nᴇᴇᴅ Tᴏ Wᴀɪᴛ </b><code>{checker.get('message', '1')}</code><b> Sᴇᴄᴏɴᴅs Fᴏʀ Pʀᴏᴄᴇssɪɴɢ Yᴏᴜʀ Oʀᴅᴇʀ..</b>.", parse_mode='html')
                    except Exception as e:
                        print(e)
                        return
                    
                    return
        
            result = get_phone_number_id(server, code, country, price, call.message,msg,call.data,operate)
        elif checking['status'] == 'error':
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🔥 Dᴇᴘᴏsɪᴛ Nᴏᴡ Fᴏʀ Pᴜʀᴄʜᴀsᴇ", callback_data='USER:DEPOSIT'))
            bot.delete_message(user_id, msg)
            bot.send_photo(photo='https://i.postimg.cc/wM4r0m9V/IMG-20240623-223050-843.jpg',chat_id=user_id, caption=f"""<b>🏛️ Iɴsᴜғғɪᴄɪᴇɴᴛ Bᴀʟᴀɴᴄᴇ!</b>

💰 <b>Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ ❯</b> <code>{checking['balance']}</code> 💎
🫴🏻 <b>Rᴇǫᴜɪʀᴇᴅ Bᴀʟᴀɴᴄᴇ ❯</b> <code>{price}</code> 💎

⚡ <b>Rᴇᴄʜᴀʀɢᴇ Yᴏᴜʀ Wᴀʟʟᴇᴛ Tᴏ Cᴏɴᴛɪɴᴜᴇ Pᴜʀᴄʜᴀsᴇ..</b>.""", reply_markup=keyboard, parse_mode='html')
            return

        if result['status'] == 'error':
            try:
                keyboard = InlineKeyboardMarkup()
                keyboard.row(InlineKeyboardButton("🐼 Eɴᴀʙʟᴇ Aᴜᴛᴏ Cʜᴇᴄᴋ [ Aᴜᴛᴏ-Aᴛᴛᴇᴍᴘᴛ ]", callback_data=f'$ {call.data}'))
                bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"""<b>🌊 Nᴏ Nᴜᴍʙᴇʀs Aᴠᴀɪʟᴀʙʟᴇ</b>
<code>Dᴜᴇ Tᴏ Hɪɢʜ Dᴇᴍᴀɴᴅ, Tʜᴇ Sᴇʀᴠɪᴄᴇ Is Uɴᴀᴠᴀɪʟᴀʙʟᴇ.</code>

<b>🔎 Tʀʏ Aɢᴀɪɴ</b>
<code>Cʟɪᴄᴋ Aᴜᴛᴏ Cʜᴇᴄᴋ Tᴏ Rᴇᴛʀʏ Pᴜʀᴄʜᴀsᴇ.</code>""",parse_mode='html',reply_markup=keyboard)
                bot.answer_callback_query(call.id, f"✘ Nᴏ Nᴇᴡ Nᴜᴍʙᴇʀs Aᴠᴀɪʟᴀʙʟᴇ....")
            except Exception as e:
                print(e)
                return
        if result['status'] == 'success':
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("✘ Cᴀɴᴄᴇʟ Oʀᴅᴇʀ", callback_data=f"CHANGE:STATUS:CANCEL {user_id} {result['id']}"),InlineKeyboardButton("↻ Bᴜʏ Aɢᴀɪɴ", callback_data=call.data))
            text = f"""<blockquote><b>📦 {service} [</b> <code>{SerName}</code> <b>][</b> <code>{flag}</code> <b>][</b> 💎 <code>{price}</code> <b>]</b></blockquote>
            
<b>📞 Nᴜᴍʙᴇʀ ❯</b> {result['number']}
            
⏱<b> Nᴜᴍʙᴇʀ Is Vᴀʟɪᴅ Tɪʟʟ</b> {AfterMin(20)}"""
            bot.edit_message_text(chat_id=user_id, message_id=msg, text=text, parse_mode='html',reply_markup=keyboard)
            try:
                bot.answer_callback_query(call.id, f"🛍️ Nᴜᴍʙᴇʀ Bᴜʏᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ...")
            except Exception as e:
                return
            return


@bot.callback_query_handler(func=lambda call: call.data.startswith('$'))
def callback_inline(call):
    user_id = call.message.chat.id
    parts = call.data.split()
    server = call.data.split('_')[1].split()[0]
    SerName = server.replace('1', '𝟷').replace('2', '𝟸').replace('3', '𝟹').replace('4', '𝟺')
    msg = call.message.message_id
    call_data = call.data[10:]
    buycommand = parts[2] if len(parts) > 2 else None
    country = parts[3] if len(parts) > 3 else None
    price = parts[4] if len(parts) > 4 else None
    code = parts[5] if len(parts) > 5 else None
    service = parts[6] if len(parts) > 6 else code
    flag = parts[7] if len(parts) > 7 else None
    operate = parts[8] if len(parts) > 8 else None
    if service == '1':
        service = str(f"{code}").capitalize()

    thread = threading.Thread(target=handle_auto_check, args=(call, user_id, server, code, country, price, msg, call_data, operate))
    thread.start()



#inline query 
@bot.inline_handler(lambda query: not query.query.strip().startswith('#'))
def query_apps(inline_query):
    response = load_data('serviceCode.json','r')
    checker = load_data('CheckerList.json','r')

    app_list = {key: value.lower() if isinstance(value, str) else value[0].lower() for key, value in response.items()}
    
    RESULTS_PER_PAGE = 25
    
    try:
        query = inline_query.query.strip().lower()
        matches = []
        
        if query == '':
            matches = sorted(app_list.items())
        else:
            prefix_matches = [(key, value) for key, value in app_list.items() if key.lower().startswith(query)]
            other_matches = [(key, value) for key, value in app_list.items() if query in key.lower() or difflib.SequenceMatcher(None, query, key.lower()).ratio() > 0.7]
            
            # Combine and sort prefix matches first
            matches = sorted(prefix_matches) + sorted(other_matches)
        
        # Filter out duplicates based on 'value' before pagination
        seen_values = set()
        unique_matches = []
        for key, value in matches:
            if value not in seen_values:
                seen_values.add(value)
                unique_matches.append((key, value))
        
        num_pages = -(-len(unique_matches) // RESULTS_PER_PAGE)
        offset = int(inline_query.offset) if inline_query.offset else 0  # Ensure offset is not None
        current_matches = unique_matches[offset * RESULTS_PER_PAGE: (offset + 1) * RESULTS_PER_PAGE]
        
        results = []
        for idx, (key, value) in enumerate(current_matches, start=offset * RESULTS_PER_PAGE + 1):
            result = InlineQueryResultArticle(
                id=str(idx),
                title=key.title(),
                description=f'We Have “{value}” Numbers.',
                thumbnail_url=f"https://fastsms.su/img/service/{value}.png" if value in checker else f"https://smsactivate.s3.eu-central-1.amazonaws.com/assets/ico/{value}0.webp",
                input_message_content=InputTextMessageContent(f"/Buy_{value}")
            )
            results.append(result)
        
        next_offset = str(offset + 1) if offset + 1 < num_pages else ''
        if not results:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="📞 Cᴏɴᴛᴀᴄᴛ Cᴏᴜsᴛᴏᴍᴇʀ Exɪᴄᴜᴛɪᴠᴇ", url="FlashOtpOwner.t.me"))
            results.append(InlineQueryResultArticle(id=str(1),title=f'“{inline_query.query}” Is Nᴏᴛ Fᴏᴜɴᴅ Iɴ Sᴇʀᴠɪᴄᴇs',description="Yᴏᴜ Cᴀɴ Cᴏɴᴛᴀᴄᴛ Sᴜᴘᴘᴏʀᴛ Tᴏ Aᴅᴅ Tʜᴇsᴇ Sᴇʀᴠɪᴄᴇs Oʀ Tʀʏ “AɴʏOᴛʜᴇʀ” Nᴜᴍʙᴇʀs",input_message_content=InputTextMessageContent(message_text="*🔥 Fᴏʀ Aᴅᴅɪɴɢ Aɴʏ Uɴʟɪsᴛᴇᴅ Sᴇʀᴠɪᴄᴇ*\n\n*Cᴏɴᴛᴀᴄᴛ Cᴏᴜsᴛᴏᴍᴇʀ Exɪᴄᴜᴛɪᴠᴇ*\n\n*——————— Oʀ ———————*\n\n👉 *Tʀʏ “Oᴛʜᴇʀ(/Buy_ot)“, Iᴛ Mɪɢʜᴛ Bᴇ Wᴏʀᴋ.* ",parse_mode="Markdown"),reply_markup=keyboard,thumbnail_url="https://i.postimg.cc/1zd93SYp/1000011596.png"))
        bot.answer_inline_query(inline_query.id, results, next_offset=next_offset)
        return
    
    except Exception as e:
        #print(e)
        return

#orders
@bot.inline_handler(lambda query: query.query.strip().startswith('#OʀᴅᴇʀIᴅ'))
def query_smsList(inline_query):
    try:
        last = {1:'sᴛ',2:'ɴᴅ',3:'ʀᴅ',4:'ᴛʜ'}
        order_id = inline_query.query.split(":")[1]
        user_id = inline_query.from_user.id
        user = get_user(user_id)
        order_data = user['orders'].get(order_id)
        checker = load_data('CheckerList.json','r')
        id = 0
        if order_data:
            results = []
            for idx, item in enumerate(order_data['history'], start=1):
                action_details = item['action'].split(':')
                if 'SMS received' in action_details[0]:
                    sms_code = action_details[1].strip()
                    buttonText = order_data.get('buttonText')
                    code = re.search(r'\b\w+\b', buttonText.split()[1]).group()
                    price = order_data.get('amount')
                    price = price if idx == 2 else 'Fʀᴇᴇ'
                    name = re.search(r'\b\w+\b', buttonText.split()[5]).group()
                    id += 1
                    result = InlineQueryResultArticle(id=str(idx),title=f"{id}{last.get(id,'ᴛʜ')} Sᴍs Rᴇᴄɪᴇᴠᴇᴅ [{sms_code}]",description=f"💎 Pʀɪᴄᴇ ❯ {price}\n⏳ Rᴇᴄᴇɪᴠᴇᴅ Aᴛ {time_ago(item['datetime'])} Aɢᴏ...",thumbnail_url=f"https://fastsms.su/img/service/{code}.png" if code in checker else f"https://smsactivate.s3.eu-central-1.amazonaws.com/assets/ico/{code}0.webp",
input_message_content=InputTextMessageContent(f'/Buy_{code}'))
                    results.append(result)

            summary_result = InlineQueryResultArticle(id='summary',title=f'🛍️ Oʀᴅᴇʀ Sᴍs Hɪsᴛᴏʀʏ [{name}]',description=f"⚡ Oʀᴅᴇʀ Bᴜʏᴇᴅ Aᴛ [{order_data['datetime']}]\n💬 Tᴏᴛᴀʟ Sᴍs Rᴇᴄɪᴇᴠᴇᴅ ❯ {id} Sᴍs'{'s' if id > 1 else ''}",input_message_content=InputTextMessageContent(f'/Buy_{code}'),thumbnail_url='https://i.postimg.cc/SsGCcXsn/IMG-20240627-195746-954.jpg')
            results.insert(0, summary_result)
            bot.answer_inline_query(inline_query.id, results, cache_time=1)
    except Exception as e:
        print(f"Error handling inline query: {e}")
        return




def parse_datetime(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%d %I:%M:%S %p")


@bot.inline_handler(lambda query: query.query.strip().startswith('#history'))
def handle_inline_query(inline_query):
    try:
        query_type = 'all' #inline_query.query.split(":")[1]
        print(query_type)
        offset = int(inline_query.offset) if inline_query.offset else 1
        user_id = inline_query.from_user.id
        results, next_offset = get_inline_results(user_id,query_type, offset)
        bot.answer_inline_query(inline_query.id, results, next_offset=next_offset)
    except Exception as e:
        print(f"Error: {e}")



def get_inline_results(chat_id,query_type, page=1, items_per_page=25):
    if query_type in ['order', 'deposit', 'all']:
        user = get_user(chat_id)
        order_deposit = get_history(user, 'DEPOSIT:ORDER')
        bot.send_message(chat_id,f"{order_deposit}")
        data = order_deposit["orders"] + order_deposit["deposits"]
        if query_type == 'order':
            data = [d for d in data if 'order_id' in d]
        elif query_type == 'deposit':
            data = [d for d in data if 'deposit_id' in d]
        data.sort(key=lambda x: parse_datetime(x["datetime"]), reverse=True)

        # Pagination
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page
        paginated_results = data[start_index:end_index]
        next_offset = str(page + 1) if end_index < len(data) else ''

        return format_inline_query_results(paginated_results), next_offset
    else:
        return [], ''


def format_inline_query_results(results):
    inline_results = []
    for idx, result in enumerate(results, start=1):
        if "order_id" in result:
            description = f"Order ID: {result['order_id']}"
            thumbnail = 'https://i.postimg.cc/DzVnGBMr/1000014742-removebg-preview.png'
        else:
            description = f"Deposit ID: {result['deposit_id']}"
            thumbnail = 'https://i.postimg.cc/B6dpgP21/536113.png'

        inline_results.append(types.InlineQueryResultArticle(
            id=str(idx),
            title="Detail",
            description=description,
            thumbnail_url= thumbnail,
            input_message_content=types.InputTextMessageContent(message_text=description)
        ))

    return inline_results



#CallBack Data Inline Buttons For BUY
@bot.callback_query_handler(func=lambda call: call.data.startswith('BUY:NEW'))
def callback_inline(call):
    parts = call.data.split()
    server = parts[1] if len(parts) > 1 else None
    price = parts[2] if len(parts) > 2 else None
    service = parts[3] if len(parts) > 3 else None
    name = parts[4] if len(parts) > 4 else None
    buycommand = parts[5] if len(parts) > 5 else None
    if not server and not price and not service and not name:
        return
    bot.answer_callback_query(call.id, f"✅ Sᴇʀᴠᴇʀ Sᴇʟᴇᴄᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ...")
    
    request = Get_Ser_Price_AD(server, service)
    SerName = server.replace('1', '𝟷').replace('2', '𝟸').replace('3', '𝟹').replace('4', '𝟺')
    text = f"<b>⦿ Sᴇʀᴠɪᴄᴇ ❯</b> {name} <b>〔{SerName}〕 \n\n↓ Cʜᴏᴏsᴇ Cᴏᴜɴᴛʀʏ Bᴇʟᴏᴡ</b>"
    if server in ['1','2','3','4']:
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,text=text, reply_markup=generate_markup(0, request,server, service, name,buycommand),parse_mode='html')
        except Exception as e:
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,text=text, reply_markup=generate_markup(1, request,server, service, name,buycommand),parse_mode='html')
            except Exception as e:
                return
            return
    

#Chnage Server
@bot.callback_query_handler(func=lambda call: call.data.startswith('/Buy_'))
def change_ser(call):
    user_id = call.message.chat.id
    listService = load_data('serviceCode.json','r')
    checker = load_data('CheckerList.json','r')
    response = load_data('serviceForOne.json','r')
    countryFlags = load_data('countriesFlag.json','r')
    bot.answer_callback_query(call.id, f"🔥 Cʜᴀɴɢɪɴɢ Tʜᴇ Sᴇʀᴠᴇʀ...",show_alert=False)
        
    code = call.data[5:].replace(" ", "").lower()
    if code in response:
        keyboard = InlineKeyboardMarkup()
        msg = bot.edit_message_text(chat_id=call.message.chat.id,message_id=call.message.message_id,text=f"🔍 <b>Sᴇᴀʀᴄʜɪɴɢ Iɴ Pʀᴏɢʀᴇss..</b>.", parse_mode='html').message_id
        name = response[code].replace(" ", "").lower()
        Name = response[code].capitalize()
        command = "BUY:NEW"
        code2 = get_value(listService, name)
        services = fetch_service(name, code2,code)
        
        country1, PriceServer1 = get_country_server_1or3(code,countryFlags['1'], services['1'],comissionPurchase, '1') 
        if PriceServer1 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ1  ➨  {country1}  »»  💎 {PriceServer1}",callback_data=f'{command} 1 {PriceServer1} {code} {Name} {code}'))
            
        country2, PriceServer2 = get_country_server_2(name,countryFlags['2'],services['2'],comissionPurchase)
        if PriceServer2 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ2  ➨  {country2}  »»  💎 {PriceServer2}",callback_data=f'{command} 2 {PriceServer2} {name} {Name} {code}'))
        bot.edit_message_text(chat_id=call.message.chat.id,message_id=call.message.message_id,text="⏳ <b>Rᴇǫᴜᴇsᴛɪɴɢ Sᴇʀᴠᴇʀ Fᴏʀ Oʀᴅᴇʀ..</b>.", parse_mode='html')
            
        country3, PriceServer3 = get_country_server_1or3(code2,countryFlags['3'],services['3'],comissionPurchase, '3') 
        if PriceServer3 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ3  ➨  {country3}  »»  💎 {PriceServer3}",callback_data=f'{command} 3 {PriceServer3} {code2} {Name} {code}'))
            
        country4, PriceServer4 = get_country_server_4(code2,countryFlags['4'],services['4'],comissionPurchase) 
        if PriceServer4 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ4  ➨  {country4}  »»  💎 {PriceServer4}",callback_data=f'{command} 4 {PriceServer4} {code2} {Name} {code}'))
        try:
            bot.edit_message_text(chat_id=call.message.chat.id,message_id=call.message.message_id,text=f"<b>⊙ Sᴇʟᴇᴄᴛᴇᴅ Sᴇʀᴠɪᴄᴇ ❯</b> <code>{Name}</code><b>\n\n↓ Cʜᴏᴏsᴇ Sᴇʀᴠᴇʀ Bᴇʟᴏᴡ</b>",parse_mode="html", reply_markup=keyboard)
        except Exception as e:
            return
        return




# Check Servers
@bot.message_handler(func=lambda message: message.text.startswith('/Buy_'),content_types=['text'])
def handle_buy(message):
    user_id = message.chat.id
    listService = load_data('serviceCode.json','r')
    checker = load_data('CheckerList.json','r')
    response = load_data('serviceForOne.json','r')
    countryFlags = load_data('countriesFlag.json','r')
        
    code = message.text[5:].replace(" ", "").lower()
    if code in response:
        keyboard = InlineKeyboardMarkup()
        msg = bot.send_message(user_id,f"🔍 <b>Sᴇᴀʀᴄʜɪɴɢ Iɴ Pʀᴏɢʀᴇss..</b>.", parse_mode='html',reply_to_message_id=message.message_id). message_id
        name = response[code].replace(" ", "").lower()
        Name = response[code].capitalize()
        command = "BUY:NEW"
        code2 = get_value(listService, name)
        services = fetch_service(name, code2,code)
        
        country1, PriceServer1 = get_country_server_1or3(code,countryFlags['1'], services['1'],comissionPurchase,'1') 
        if PriceServer1 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ1  ➨  {country1}  »»  💎 {PriceServer1}",callback_data=f'{command} 1 {PriceServer1} {code} {Name} {code}'))
            
        country2, PriceServer2 = get_country_server_2(name,countryFlags['2'],services['2'],comissionPurchase)
        if PriceServer2 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ2  ➨  {country2}  »»  💎 {PriceServer2}",callback_data=f'{command} 2 {PriceServer2} {name} {Name} {code}'))

        bot.edit_message_text(chat_id=user_id, message_id=msg, text="⏳ <b>Rᴇǫᴜᴇsᴛɪɴɢ Sᴇʀᴠᴇʀ Fᴏʀ Oʀᴅᴇʀ..</b>.", parse_mode='html')
            
        country3, PriceServer3 = get_country_server_1or3(code2,countryFlags['3'],services['3'],comissionPurchase,'3') 
        if PriceServer3 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ3  ➨  {country3}  »»  💎 {PriceServer3}",callback_data=f'{command} 3 {PriceServer3} {code2} {Name} {code}'))
            
        country4, PriceServer4 = get_country_server_4(code2,countryFlags['4'],services['4'],comissionPurchase) 
        if PriceServer4 is not None:
            keyboard.row(InlineKeyboardButton(f"Sᴇʀᴠᴇʀ4  ➨  {country4}  »»  💎 {PriceServer4}",callback_data=f'{command} 4 {PriceServer4} {code2} {Name} {code}'))
        bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"<b>⊙ Sᴇʟᴇᴄᴛᴇᴅ Sᴇʀᴠɪᴄᴇ ❯</b> <code>{Name}</code><b>\n\n↓ Cʜᴏᴏsᴇ Sᴇʀᴠᴇʀ Bᴇʟᴏᴡ</b>",parse_mode="html", reply_markup=keyboard)
        return




def start_bot():
    while True:
        try:
            print("Bot is running")
            bot.polling(non_stop=True)
        except Exception as e:
            error_message = f"Bot polling failed: {e}\n{traceback.format_exc()}"
            print(error_message)
            try:
                bot.send_message(AdminId, error_message)
            except Exception as send_error:
                print(f"Failed to send error message to admin: {send_error}")
            time.sleep(10)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    order_thread = threading.Thread(target=mainForOrders, args=(OrderFile,))
    deposit_thread = threading.Thread(target=mainForDeposit, args=(DepositFile,))

    order_thread.start()
    deposit_thread.start()

    order_thread.join()
    deposit_thread.join()
