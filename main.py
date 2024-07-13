import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, InputTextMessageContent, InlineQueryResultArticle, WebAppInfo
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
from flask import Flask, request, jsonify
app = Flask(__name__)





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
UserUpdateChannel = response["UserUpdateChannel"]
ApiFile = response["ApiFile"]

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


def get_user(user_id,user_name=None):
    """Retrieve user data or initialize it if the user doesn't exist."""
    data = load_user_data()
    user_id = str(user_id)
    if user_id not in data['users']:
        data['users'][user_id] = {
            'username': f'{user_name}',
            'balance': 0,
            'total_numbers_purchased': 0,
            'total_spend': 0,
            'total_deposit_amount': 0,
            'user_forum_id': "NONE",
            'user_currency': {'Iɴʀ [₹]': True},
            'current_deposit_address':{"UPI":"NONE","TRX":"NONE"},
            'deposit': {},
            'orders': {},
            'last_purchase_time': currentTime()
        }
        save_user_data(data)

    return data['users'][user_id]



def create_forum_topic(chat_id, topic_name):
    random_colors = [
    0x6FB9F0,   # RGB: 111, 185, 240
    0xFFD67E,   # RGB: 255, 214, 126
    0xCB86DB,   # RGB: 203, 134, 219
    0x8EEE98,   # RGB: 142, 238, 152
    0xFF93B2,   # RGB: 255, 147, 178
    0xFB6F5F    # RGB: 251, 111, 95
    ]
    icon_color = random.choice(random_colors)
    url = f'https://api.telegram.org/bot{BotToken}/createForumTopic'
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        'chat_id': UserUpdateChannel,
        'name': topic_name,
        'icon_color': icon_color
    }
    json_payload = json.dumps(payload)
    response = requests.post(url, headers=headers, data=json_payload)
    if response.status_code == 200:
        result = response.json()
        if result['ok']:
            return result['result']

    return None




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
        is_single_id = len(user['deposit']) == 1
        order_id = method_or_card
        amount = float(amount)
        user['balance'] += amount
        user['total_deposit_amount'] += amount 
        details = user['deposit'][order_id]
        details['status'] = 'CONFIRMED'
        user['current_deposit_address']['UPI'] = "NONE"
        details['amount'] = amount
        details['datetime'] = currentTime()
        details['history'].append({'datetime': currentTime(),'action':'ORDER_CONFIRMED:ADDED'})
        del details['time']
        new_data = {'balance': user['balance'],'total_deposit_amount':user['total_deposit_amount'],'deposit':user['deposit'],'current_deposit_address':user['current_deposit_address']}
        update_user(user_id, new_data)
        if is_single_id == True:
            return {'status': 'success','orderId':order_id,'is_new':True}
        return {'status': 'success','orderId':order_id,'is_new':False}


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
    keyboard.row(InlineKeyboardButton("⁉️ Hᴇʟᴘ",callback_data=f"USER:SUPPORT"),InlineKeyboardButton("⚙️ Sᴇᴛᴛɪɴɢs",callback_data=f"USER:SETTINGS:CURRENCY"))
    link = 'https://i.postimg.cc/9fyK1yCK/IMG-20240607-023137-160.jpg'
    chat_id = message.chat.id
    first_name = message.chat.first_name
    message_id = message.message_id

    user = get_user(chat_id,first_name)
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

user_selected_buttons = {}
def create_inline_markup(user_id):
    markup = InlineKeyboardMarkup()
    button_labels = [
        ['Iɴʀ [₹]', 'Usᴅ [$]'],
        ['Eᴜʀ [€]', 'Gʙᴘ [£]'],
        ['Jᴘʏ [¥]', 'Aᴜᴅ [$]'],
        ['Cɴʏ [¥]', 'Cʜғ [Fʀ.]'],
        ['Cᴀᴅ [$]', 'Kʀᴡ [₩]'],
        ['Rᴜʙ [₽]', 'Mxɴ [$]'],
        ['Bʀʟ [R$]', 'Pʜᴘ [₱]'],
        ['Sɢᴅ [$]', 'Hᴋᴅ [$]']
    ]
    flag_emojis = {
        'Iɴʀ [₹]': '🇮🇳', 'Usᴅ [$]': '🇺🇸', 'Eᴜʀ [€]': '🇪🇺', 'Gʙᴘ [£]': '🇬🇧',
        'Jᴘʏ [¥]': '🇯🇵', 'Aᴜᴅ [$]': '🇦🇺', 'Cɴʏ [¥]': '🇨🇳', 'Cʜғ [Fʀ.]': '🇨🇭',
        'Cᴀᴅ [$]': '🇨🇦', 'Kʀᴡ [₩]': '🇰🇷', 'Rᴜʙ [₽]': '🇷🇺', 'Mxɴ [$]': '🇲🇽',
        'Bʀʟ [R$]': '🇧🇷', 'Pʜᴘ [₱]': '🇵🇭', 'Sɢᴅ [$]': '🇸🇬', 'Hᴋᴅ [$]': '🇭🇰'
    }
    user = get_user(user_id)
    selected_buttons = user['user_currency']
    for row in button_labels:
        button_row = []
        for label in row:
            button_text = f"{flag_emojis[label]} {label}"
            if label in selected_buttons:
                button_text = f"🔘 {button_text}"
            button_row.append(InlineKeyboardButton(text=button_text, callback_data=f"USER:SETTINGS:CURRENCY{label}"))
        markup.row(*button_row)
    return markup


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
        f'https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=getPrices&service={service}'
    ]
    responses = [fetch_data(url) for url in urls if fetch_data(url)]
    result = {}
    for i, response in enumerate(responses):
        try:
            result[str(i + 1)] = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for response {i+1}: {e}")
            result[str(i + 1)] = None
    json_result = json.dumps(result, indent=4)
    parsed_result = json.loads(json_result)
    return parsed_result


#sort list 1 and 2
def sort_data_ser1or3(url, server,country=None):
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
    week_total_deposit = 0

    order_details = []
    deposit_details = []

    # Determine start of the week
    week_start = (current_date - timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if request_type == 'OrderWeekDetails':
        # Process orders
        for order_id, order in data['orders'].items():
            try:
                order_datetime = datetime.strptime(order['datetime'], '%Y-%m-%d %I:%M:%S %p')
                order_datetime = india_tz.localize(order_datetime) if order_datetime.tzinfo is None else order_datetime
                if order_datetime >= week_start:
                    week_total_order_amount += float(order['amount'])
                    week_total_orders += 1
            except Exception as e:
                print(f"Error processing deposit {order_id}: {e}")

        # Process deposits
        for deposit_id, deposit in data['deposit'].items():
            try:
                if deposit['status'] == "WAITING":
                    continue
                deposit_datetime = datetime.strptime(deposit['datetime'], '%Y-%m-%d %I:%M:%S %p')
                deposit_datetime = india_tz.localize(deposit_datetime) if deposit_datetime.tzinfo is None else deposit_datetime
                if deposit_datetime >= week_start:
                    week_total_deposit_amount += float(deposit['amount'])
                    week_total_deposit += 1
            except Exception as e:
                print(f"Error processing deposit {deposit_id}: {e}")
            
        return {
            'total_order_amount': week_total_order_amount,
            'total_orders': week_total_orders,
            'total_deposit_amount': week_total_deposit_amount,
            'total_deposit': week_total_deposit
        }

    # Process orders
    if request_type == 'ORDER:DETAILS':
        for order_id, order in data['orders'].items():
            try:
                order_datetime = datetime.strptime(order['datetime'], '%Y-%m-%d %I:%M:%S %p')
                order_datetime = india_tz.localize(order_datetime) if order_datetime.tzinfo is None else order_datetime
                order_details.append({'order_id': order_id, 'datetime': order_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': order})
                week_total_order_amount += float(order['amount'])
                week_total_orders += 1
            except Exception as e:
                print(f"Error processing order1 {order_id}: {e}")
            
        return {
            'orders': order_details,
            'total_order_amount': week_total_order_amount, 
            'total_orders': week_total_orders
        }



    if request_type == 'DEPOSIT:DETAILS':
        for deposit_id, deposit in data['deposit'].items():
            try:
                if deposit['status'] == "WAITING":
                    continue
                deposit_datetime = datetime.strptime(deposit['datetime'], '%Y-%m-%d %I:%M:%S %p')
                deposit_datetime = india_tz.localize(deposit_datetime) if deposit_datetime.tzinfo is None else deposit_datetime
                deposit_details.append({'deposit_id': deposit_id, 'datetime': deposit_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': deposit})
                week_total_deposit_amount += float(deposit['amount'])
                week_total_deposit += 1
            except Exception as e:
                print(f"Error processing deposit2 {deposit_id}: {e}")       
        return {
            'deposits': deposit_details,
            'total_deposit_amount': week_total_deposit_amount,
            'total_deposit': week_total_deposit}

    if request_type == 'DEPOSIT:ORDER':
        for order_id, order in data['orders'].items():
            try:
                order_datetime = datetime.strptime(order['datetime'], '%Y-%m-%d %I:%M:%S %p')
                order_datetime = india_tz.localize(order_datetime) if order_datetime.tzinfo is None else order_datetime
                order_details.append({'order_id': order_id, 'datetime': order_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': order})
                week_total_order_amount += float(order['amount'])
                week_total_orders += 1
            except Exception as e:
                print(f"Error processing order1 {order_id}: {e}")
        
        for deposit_id, deposit in data['deposit'].items():
            try:
                if deposit['status'] == "WAITING":
                    continue
                deposit_datetime = datetime.strptime(deposit['datetime'], '%Y-%m-%d %I:%M:%S %p')
                deposit_datetime = india_tz.localize(deposit_datetime) if deposit_datetime.tzinfo is None else deposit_datetime
                deposit_details.append({'deposit_id': deposit_id, 'datetime': deposit_datetime.strftime('%Y-%m-%d %I:%M:%S %p'), 'details': deposit})
                week_total_deposit_amount += float(deposit['amount'])
                week_total_deposit += 1
            except Exception as e:
                print(f"Error processing deposit2 {deposit_id}: {e}")
    
        return {
            'deposits': deposit_details, 
            'orders': order_details,
            'details': {
                'total_order_amount': week_total_order_amount,
                'total_orders': week_total_orders,
                'total_deposit_amount': week_total_deposit_amount,
                'total_deposit': week_total_deposit
            }
        }
    else:
        raise ValueError("Invalid request type")



def Get_Ser_Price_AD(server, service,type=None,country=None):
    if server == "1":
        request = sort_data_ser1or3(f'https://flashsms.in/BotFile/serviceList.php?service={service}',"1",country)
    if server == "2":
        request = sort_data_ser1or3(f'https://api1.5sim.net/stubs/handler_api.php?api_key={fivesim}&action=getPrices&service={service}',"2",country)
    if server == "3":
        request = sort_data_ser1or3(f'https://smshub.org/stubs/handler_api.php?api_key={smshub}&action=getPrices&service={service}',"3",country)
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
    if server in ["1","2","3"]:
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
                    new_order = {"server_id": ser,"api_key":f"{api_key}","order_id":f"{id_number}", "user_id": f"{message.chat.id}","time":time.time(),"status":"pending","number":f"{phone_number}","type":"user"}
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
                return {'status': 'error', 'message': 'Something went wrong'}
            elif response_text == 'NO_BALANCE':
                return {'status': 'error', 'message': 'adding new numbers'}
            elif response_text == 'API_KEY_NOT_VALID':
                return {'status': 'error', 'message': 'Invalid key'}
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
    print(f"${time.time()}\n{message}")
    checker = []
    if message == "No orders to process. Waiting for new orders.":
        return
    if str(message.get('status')) == str('timeout'):
        data = remove_order(OrderFile,message.get('order_id'))
        print(data)
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
            del user['orders'][order_id]
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
    user = get_user(user_id)
    update = update_balance(user_id, 'deposit', amount, order_id)
    if update['status'] == 'success' and update['is_new'] == True:
        forum = create_forum_topic(user_id, f"❯ {user['username']} [{user_id}]")
        user['user_forum_id'] = forum['message_thread_id']
        new_data = {'user_forum_id': user['user_forum_id']}
        update_user(user_id, new_data)
        
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
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔗 Usᴇʀ",url=f'tg://openmessage?user_id={user_id}'),InlineKeyboardButton("🔍 Dᴇᴛᴀɪʟs",callback_data=f'[DETAILS] {user_id}'))
    message_text = f"""<b>#Uᴘɪ_Cᴀʀᴅ_Dᴇᴘᴏsɪᴛ ❯</b>

<b>Tʀᴀɴsᴀᴄᴛɪᴏɴ Dᴇᴛᴀɪʟs</b>
<b>💰 Aᴍᴏᴜɴᴛ Cʀᴇᴅɪᴛᴇᴅ »</b> <code>{amount}</code> 💎  
<b>💳 Oʀᴅᴇʀ Iᴅ »</b> <code>{order_id}</code>
<b>👤 Pᴀɪᴅ Fʀᴏᴍ »</b> <code>{paid_from}</code>
<b>🕊 Pᴀʏᴍᴇɴᴛ Tʏᴘᴇ »</b> <code>{paid_type}</code>
<b>💎 Usᴇʀ Bᴀʟᴀɴᴄᴇ »</b> <code>{user['balance']:.2f}</code>"""
    msg = bot.send_message(chat_id=UserUpdateChannel, text=message_text, message_thread_id=user['user_forum_id'],reply_markup=keyboard,parse_mode='HTML')
    message_id = msg.message_id
    chat_id = msg.chat.id
    if str(chat_id).startswith('-100'):
        chat_id = 'c/' + str(chat_id)[4:]

    forum = user['user_forum_id']
    link = f'https://t.me/{chat_id}/{forum}/{message_id}'
    text = f'<b>💎 Nᴇᴡ Dᴇᴘᴏsɪᴛ</b>\n[<code>{paid_type}</code>][<code>{amount}</code>][<code>{user_id}</code>]'
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔗 Usᴇʀ",url=f'tg://openmessage?user_id={user_id}'),InlineKeyboardButton("🔍 Dᴇᴛᴀɪʟs",url=link))
    bot.send_message(chat_id=UserUpdateChannel, text=text,reply_markup=keyboard,parse_mode='HTML')
    return























#api keys

def validate_api_key(api_key):
    api_data = load_data(ApiFile,'r')
    if api_key not in api_data:
        return {'status':'error','message':'Invalid or missing API key','short_code':'BAD_KEY'}
    return None

def get_api_number(user_id, service, country, server, buycommand, name, code, server_data):
    countryFlags = load_data('countriesFlag.json', 'r')
    url = {}
    if str(server) == str('1'):
        api_key = fastsms
        for item in server_data:
            for price, numbers in item.items():
                if country in numbers:
                    amount = price
                    flag = countryFlags['3'].get(country, "🏴‍☠️")
                    url = f"https://fastsms.su/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={code}&country={country}"
                    buttonText = f'buy_{server} {buycommand} {country} {amount} {service} {name} {flag}'
                    break
    elif str(server) == '2':
        api_key = fivesim
        for item in server_data:
            for price, countries in item.items():
                for entry in countries:
                    operator, country_name = entry.split('_')
                    if country_name.lower() == country.lower():
                        amount = price
                        flag = countryFlags['2'].get(country,"🏴‍☠️")
                        url = f"http://api1.5sim.net/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={code}&operator={operator}&country={country}" 
                        buttonText = f'buy_{server} {buycommand} {country} {amount} {service} {name} {flag} {operator}'
                        break
    elif str(server) == str('3'):
        api_key = smshub
        for item in server_data:
            for price, numbers in item.items():
                if country in numbers:
                    amount = price
                    flag = countryFlags['3'].get(country, "🏴‍☠️")
                    url = f"https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={code}&country={country}"
                    buttonText = f'buy_{server} {buycommand} {country} {amount} {service} {name} {flag}'
                    break
    if not url:
        return {'status': 'error', 'message': 'Missing required parameter: country','short_code': 'BAD_COUNTRY'}, 400

    checker = update_balance(user_id, 'checking', amount)
    if checker.get('status') == 'error' and checker.get('status') != 'success':
        return {'status': 'error', 'message': 'No balance remains to buy this service','short_code': 'NO_BALANCE'}, 400
    
    if server in ["1", "2", "3"]:
        try:
            response = requests.get(url)
            response_text = response.text
            if response_text.startswith('ACCESS_NUMBER'):
                match = re.match(r'ACCESS_NUMBER:(\d+):(\d+)', response_text)
                if match:
                    id_number = match.group(1)
                    phone_number = f"+{match.group(2)}"
                    new_order = {
                        "server_id": server,
                        "api_key": api_key,
                        "order_id": id_number,
                        "user_id": user_id,
                        "time": time.time(),
                        "amount": amount,
                        "status": "pending",
                        "number": phone_number,
                        "type": "api"
                    }
                    add_order('OrderFile', new_order)
                    data = manage_order(user_id, id_number, 'create', amount=price, server=server, sms='WAITING', number=phone_number, message_id='api', buttonText=buttonText)
                    return {
                        'status': "success",
                        'order_id': f'{id_number}',
                        "number": f'{phone_number}',
                        'url': f'{url}'
                    }, 200
            elif response_text.startswith('NO_BALANCE'):
                return {'status': 'error', 'message': 'No balance remains to buy this service','short_code': 'NO_BALANCE'}, 400
            elif response_text.startswith('NO_NUMBERS'):
                return {'status': 'error', 'message': 'Currently no number in stock','short_code': 'NO_NUMBERS'}, 400
            elif response_text.startswith('BAD_ACTION'):
                return {'status': 'error', 'message': 'This function can not approve currently','short_code': 'BAD_ACTION'}, 400
            else:
                return {'status': 'error', 'message': f'Unknown error: {response_text}','short_code': 'BAD_ACTION'}, 400

        except requests.RequestException as e:
            return {'status': 'error', 'message': str(e),'short_code': 'BAD_ACTION'}, 400

def apply_tax(price, server):
    multiplier = 86.9565 if server == '3' else 1
    adjusted_price = float(price) * multiplier
    commission_purchase = comissionPurchase
    final_price = adjusted_price * (commission_purchase)
    return round(final_price, 2)

def normalize_data(server_data, server):
    normalized = {}
    for country, services in server_data.items():
        normalized[country] = {}
        for service, details in services.items():
            if isinstance(details, dict):
                if "cost" in details and "count" in details:
                    cost_with_tax = apply_tax(details["cost"], server)
                    normalized[country][service] = {str(cost_with_tax): str(details["count"])}
                else:
                    for cost, count in details.items():
                        cost_with_tax = apply_tax(float(cost), server)
                        normalized[country][service] = {str(cost_with_tax): str(count)}
    return normalized

def get_api_prices(SERVER, COUNTRY=None, SERVICE=None):
    if not SERVER:
        return {"status": "error", "message": "Server Not Found", "short_code": "SERVER_NOT_FOUND"}

    if not COUNTRY and not SERVICE:
        details = ''
    elif not COUNTRY:
        details = f'&service={SERVICE}'
    elif not SERVICE:
        details = f'&country={COUNTRY}'
    else:
        details = f'&service={SERVICE}&country={COUNTRY}'

    countryFlags = load_data('countriesFlag.json', 'r')
    service_codes = countryFlags.get('service', {})
    country_flags = countryFlags.get('2', {})
    country_codes = countryFlags.get('6', {})
    output = {}

    try:
        if SERVER == '1':
            server_data = requests.get(f'https://flashsms.in/BotFile/serviceList.php?action=getPrices{details}')
            if server_data.status_code != 200:
                return {"status": "error", "message": "Failed to retrieve data from server", "short_code": "SERVER_REQUEST_ERROR"}
            server_data = server_data.json()
            if not isinstance(server_data, dict):
                if not COUNTRY and SERVICE:
                    COUNTRY = None
                    data = requests.get(f'https://flashsms.in/BotFile/serviceList.php?action=getPrices& service={SERVICE}').json()
                if not SERVICE and COUNTRY:
                    SERVICE = None
                    data = requests.get(f'https://flashsms.in/BotFile/serviceList.php?action=getPrices&country={COUNTRY}').json()
                else:
                    SERVICE = None
                    COUNTRY = None
                    data = requests.get(f'https://flashsms.in/BotFile/serviceList.php?action=getPrices').json()
                server_data = data

        elif SERVER == '2':
            api_key = fivesim
            data = requests.get(f'http://api1.5sim.net/stubs/handler_api.php?api_key={api_key}&action=getPrices{details}').json()
            if data.get('status','Not Found') != 'Not Found':
                msg = str(data.get('msg'))
                if COUNTRY and str('country is incorrect') not in msg:
                    COUNTRY = None
                    data = requests.get(f'http://api1.5sim.net/stubs/handler_api.php?api_key={api_key}&action=getPrices&country={COUNTRY}').json()
                elif SERVICE and str('service is incorrect') not in msg:
                    SERVICE = None
                    data = requests.get(f'http://api1.5sim.net/stubs/handler_api.php?api_key={api_key}&action=getPrices&service={SERVICE}').json()
                else:
                    COUNTRY = None
                    SERVICE = None
                    data = requests.get(f'http://api1.5sim.net/stubs/handler_api.php?api_key={api_key}&action=getPrices').json()
            if not isinstance(data, dict):
                return {"status": "error", "message": 'wrong parameters', "short_code": "SERVER_WRONG_PARAMETERS"}
            for country, services in data.items():
                if SERVICE and not COUNTRY:
                    service_code = service_codes.get(country.lower(), country)
                else:
                    country_flag = country_flags.get(country,country)
                    country_code = country_codes.get(country_flag,country)
                for service, products in services.items():
                    if SERVICE and not COUNTRY:
                        country_flag = country_flags.get(service,service)
                        country_code = country_codes.get(country_flag,service)
                    else:
                        service_code = service_codes.get(service.lower(), service)
                    
                    lowest_cost = float('inf')
                    lowest_cost_virtual = None
                    for virtual_id, info in products.items():
                        cost = info.get('cost')
                        count = info.get('count') or info.get('quantity')
                        if cost < lowest_cost:
                            lowest_cost = cost
                            lowest_cost_virtual = count
                    if lowest_cost_virtual is not None:
                        if country_code not in output:
                            output[country_code] = {}
                        if service_code not in output[country_code]:
                            output[country_code][service_code] = {}
                        output[country_code][service_code][str(lowest_cost)] = str(lowest_cost_virtual)
            server_data = output

        elif SERVER == '3':
            api_key = smshub
            server3 = requests.get(f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getPrices&currency=643{details}').json()
            if not isinstance(server3, dict):
                if not COUNTRY and SERVICE:
                    COUNTRY = None
                    data = requests.get(f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getPrices& service={SERVICE}').json()
                if not SERVICE and COUNTRY:
                    SERVICE = None
                    data = requests.get(f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getPrices&country={COUNTRY}').json()
                else:
                    SERVICE = None
                    COUNTRY = None
                    data = requests.get(f'https://smshub.org/stubs/handler_api.php?api_key={api_key}&action=getPrices').json()
                server_data = data
            server3 = {key: value for key, value in server3.items() if value}
            server_data = server3

    except (requests.RequestException, ValueError) as e:
        return {"status": "error", "message": str(e), "short_code": "SERVER_RESPONSE_ERROR"}

    normalized_data = normalize_data(server_data, SERVER)
    return normalized_data



    
    



@app.route('/handler_api', methods=['GET', 'POST'])
def handler_api():
    listService = load_data('serviceCode.json', 'r')
    checker = load_data('CheckerList.json', 'r')
    responses = load_data('serviceForOne.json', 'r')
    countryFlags = load_data('countriesFlag.json', 'r')

    api_key = request.args.get('api_key') or request.form.get('api_key')
    validate = validate_api_key(api_key)

    user_id = '5716978793'
    
    if validate:
        return jsonify(validate), 400

    action = request.args.get('action') or request.form.get('action')
    
    if action == 'getSms':
        sms = request.args.get('sms') or request.form.get('sms')
        
        if sms:
            response = requests.get(f"https://fastsms.su/stubs/handler_api.php?api_key={fastsms}&action=getOtp&sms={sms}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    service_data = response_data[0].split(':') if ':' in response_data[0] else [response_data[0]]
                    
                    result = jsonify({
                        'status': 'success',
                        'service': service_data,
                        'sms': response_data[1]
                    }), 200
                except Exception as e:
                    result = jsonify({
                'status': 'error',
                'message': 'Service not found for this format'
            }), 400
            else:
                result = jsonify({
                'status': 'error',
                'message': 'Service not found for this format'
            }), 400
        else:
            result = jsonify({
                'status': 'error',
                'message': 'Missing required parameter: sms'
            }), 400
        
        return result
    
    elif action == 'getNumber':
        service = request.args.get('service') or request.form.get('service') or None
        country = request.args.get('country') or request.form.get('country') or None
        server = request.args.get('server') or request.form.get('server') 
        
        if server in ['1','2','3']:
            name = responses.get(service.replace(" ", "").lower(), service.replace(" ", "").lower())
            if str(server) == str('1'):
                code = service
            elif str(server) == str('2'):
                flag = countryFlags["3"].get(country,country)
                country = countryFlags["5"].get(flag,country)
                code = name
            elif str(server) == str('3'):
                if service:
                    code = get_value(listService, code)
                else:
                    service = None
            else:
                return jsonify({'status': 'error', 'message': 'Missing required parameter: server'}), 400
            response_data = Get_Ser_Price_AD(server, code, type='api', country=country)
            result, status = get_api_number(user_id, service, country, server, f'{service}', name.capitalize(),code, response_data)
            return jsonify(result), status
        else:
            return jsonify({'status': 'error', 'message': 'Missing required parameter: service',"short_code": "BAD_SERVICE"}), 400

    elif action == 'getBalance':
        user = get_user(user_id)
        current_balance = user['balance']
        return jsonify({'status': 'success', 'message': 'Your balance fetched','short_code':'ACCESS_BALANCE','balance': f'{current_balance}'}), 200

    elif action == 'getServices':
        return jsonify(responses), 200

    elif action == 'getPrices':
        service = request.args.get('service') or request.form.get('service') or None
        country = request.args.get('country') or request.form.get('country') or None
        server = request.args.get('server') or request.form.get('server')
        if server in ['1','2','3']:
            if service:
                name = responses.get(service.replace(" ", "").lower(),service.replace(" ", "").lower())
            if str(server) == str('1'):
                code = service
            elif str(server) == str('2'):
                if country:
                    flag = countryFlags["3"].get(country,"🏴‍☠️")
                    country = countryFlags["5"].get(flag,"None")
                else: 
                    country = None
                if service:
                    code = name
                else:
                    code = None
            elif str(server) == str('3'):
                if service:
                    code = get_value(listService, name)
                else:
                    code = None
            else:
                return jsonify({'status': 'error', 'message': 'Missing required parameter: server'}), 400
            responses = get_api_prices(server,COUNTRY=country,SERVICE=code)
            return jsonify(responses), 200
        else:
            return jsonify({'status': 'error', 'message': 'Missing required parameter: server',"short_code": "BAD_SERVER"}), 400
    
    
    else:
        return jsonify({'status': 'error', 'message': 'Unsupported action'}), 400
















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

        
        bot.edit_message_text(chat_id=user_id, message_id=msg, text=f"<b>⊙ Sᴇʟᴇᴄᴛᴇᴅ Sᴇʀᴠɪᴄᴇ ❯</b> <code>{Name}</code><b>\n\n↓ Cʜᴏᴏsᴇ Sᴇʀᴠᴇʀ Bᴇʟᴏᴡ</b>",parse_mode="html", reply_markup=keyboard)
        return




@app.route('/')
def index():
    return "Web server is running!"

def start_bot():
    print("Bot is running")
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            pass
        time.sleep(10)

if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Run the Flask web server
    app.run(host='0.0.0.0', port=5001)
