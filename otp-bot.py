# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
import logging
from urllib.parse import urljoin
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

YOUR_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

ADMIN_CHAT_IDS = ["6524840104"]

env_initial_ids = os.environ.get("INITIAL_CHAT_IDS", "")
INITIAL_CHAT_IDS = [x.strip() for x in env_initial_ids.split(",") if x.strip()] if env_initial_ids else []

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = os.environ.get("IVASMS_USERNAME", "")
PASSWORD = os.environ.get("IVASMS_PASSWORD", "")

POLLING_INTERVAL_SECONDS = 5
STATE_FILE = "processed_sms_ids.json"
CHAT_IDS_FILE = "chat_ids.json"

SIGNATURE = "𝐌ʀ 𝐀ғʀɪx 𝐓ᴇᴄʜ"

NUMBER_CHANNEL_URL = "https://t.me/mrafrix"
OTP_GROUP_URL = "https://t.me/+_76TZqOFTeBkMWFk"
OWNER_URL = "https://t.me/jadenafrix"

COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Andorra": "🇦🇩", "Angola": "🇦🇴",
    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿",
    "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩", "Belarus": "🇧🇾", "Belgium": "🇧🇪", "Benin": "🇧🇯",
    "Bhutan": "🇧🇹", "Bolivia": "🇧🇴", "Brazil": "🇧🇷", "Bulgaria": "🇧🇬", "Burkina Faso": "🇧🇫",
    "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chad": "🇹🇩", "Chile": "🇨🇱",
    "China": "🇨🇳", "Colombia": "🇨🇴", "Congo": "🇨🇬", "Croatia": "🇭🇷", "Cuba": "🇨🇺",
    "Cyprus": "🇨🇾", "Czech Republic": "🇨🇿", "Denmark": "🇩🇰", "Egypt": "🇪🇬", "Estonia": "🇪🇪",
    "Ethiopia": "🇪🇹", "Finland": "🇫🇮", "France": "🇫🇷", "Gabon": "🇬🇦", "Gambia": "🇬🇲",
    "Georgia": "🇬🇪", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Greece": "🇬🇷", "Guatemala": "🇬🇹",
    "Guinea": "🇬🇳", "Haiti": "🇭🇹", "Honduras": "🇭🇳", "Hong Kong": "🇭🇰", "Hungary": "🇭🇺",
    "Iceland": "🇮🇸", "India": "🇮🇳", "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶",
    "Ireland": "🇮🇪", "Israel": "🇮🇱", "Italy": "🇮🇹", "IVORY COAST": "🇨🇮", "Ivory Coast": "🇨🇮", "Jamaica": "🇯🇲",
    "Japan": "🇯🇵", "Jordan": "🇯🇴", "Kazakhstan": "🇰🇿", "Kenya": "🇰🇪", "Kuwait": "🇰🇼",
    "Kyrgyzstan": "🇰🇬", "Laos": "🇱🇦", "Latvia": "🇱🇻", "Lebanon": "🇱🇧", "Liberia": "🇱🇷",
    "Libya": "🇱🇾", "Lithuania": "🇱🇹", "Luxembourg": "🇱🇺", "Madagascar": "🇲🇬", "Malaysia": "🇲🇾",
    "Mali": "🇲🇱", "Malta": "🇲🇹", "Mexico": "🇲🇽", "Moldova": "🇲🇩", "Monaco": "🇲🇨",
    "Mongolia": "🇲🇳", "Montenegro": "🇲🇪", "Morocco": "🇲🇦", "Mozambique": "🇲🇿", "Myanmar": "🇲🇲",
    "Namibia": "🇳🇦", "Nepal": "🇳🇵", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿", "Nicaragua": "🇳🇮",
    "Niger": "🇳🇪", "Nigeria": "🇳🇬", "North Korea": "🇰🇵", "North Macedonia": "🇲🇰", "Norway": "🇳🇴",
    "Oman": "🇴🇲", "Pakistan": "🇵🇰", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Peru": "🇵🇪",
    "Philippines": "🇵🇭", "Poland": "🇵🇱", "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Romania": "🇷🇴",
    "Russia": "🇷🇺", "Rwanda": "🇷🇼", "Saudi Arabia": "🇸🇦", "Senegal": "🇸🇳", "Serbia": "🇷🇸",
    "Sierra Leone": "🇸🇱", "Singapore": "🇸🇬", "Slovakia": "🇸🇰", "Slovenia": "🇸🇮", "Somalia": "🇸🇴",
    "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰", "Sudan": "🇸🇩",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Syria": "🇸🇾", "Taiwan": "🇹🇼", "Tajikistan": "🇹🇯",
    "Tanzania": "🇹🇿", "Thailand": "🇹🇭", "TOGO": "🇹🇬", "Tunisia": "🇹🇳", "Turkey": "🇹🇷",
    "Turkmenistan": "🇹🇲", "Uganda": "🇺🇬", "Ukraine": "🇺🇦", "United Arab Emirates": "🇦🇪", "United Kingdom": "🇬🇧",
    "United States": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿", "Venezuela": "🇻🇪", "Vietnam": "🇻🇳",
    "Yemen": "🇾🇪", "Zambia": "🇿🇲", "Zimbabwe": "🇿🇼", "Unknown Country": "🏴‍☠️"
}

SERVICE_KEYWORDS = {
    "Facebook": ["facebook"],
    "Google": ["google", "gmail"],
    "WhatsApp": ["whatsapp"],
    "Telegram": ["telegram"],
    "Instagram": ["instagram"],
    "Amazon": ["amazon"],
    "Netflix": ["netflix"],
    "LinkedIn": ["linkedin"],
    "Microsoft": ["microsoft", "outlook", "live.com"],
    "Apple": ["apple", "icloud"],
    "Twitter": ["twitter"],
    "Snapchat": ["snapchat"],
    "TikTok": ["tiktok"],
    "Discord": ["discord"],
    "Signal": ["signal"],
    "Viber": ["viber"],
    "IMO": ["imo"],
    "PayPal": ["paypal"],
    "Binance": ["binance"],
    "Uber": ["uber"],
    "Bolt": ["bolt"],
    "Airbnb": ["airbnb"],
    "Yahoo": ["yahoo"],
    "Steam": ["steam"],
    "Blizzard": ["blizzard"],
    "Foodpanda": ["foodpanda"],
    "Pathao": ["pathao"],
    "Messenger": ["messenger", "meta"],
    "Gmail": ["gmail", "google"],
    "YouTube": ["youtube", "google"],
    "X": ["x", "twitter"],
    "eBay": ["ebay"],
    "AliExpress": ["aliexpress"],
    "Alibaba": ["alibaba"],
    "Flipkart": ["flipkart"],
    "Outlook": ["outlook", "microsoft"],
    "Skype": ["skype", "microsoft"],
    "Spotify": ["spotify"],
    "iCloud": ["icloud", "apple"],
    "Stripe": ["stripe"],
    "Cash App": ["cash app", "square cash"],
    "Venmo": ["venmo"],
    "Zelle": ["zelle"],
    "Wise": ["wise", "transferwise"],
    "Coinbase": ["coinbase"],
    "KuCoin": ["kucoin"],
    "Bybit": ["bybit"],
    "OKX": ["okx"],
    "Huobi": ["huobi"],
    "Kraken": ["kraken"],
    "MetaMask": ["metamask"],
    "Epic Games": ["epic games", "epicgames"],
    "PlayStation": ["playstation", "psn"],
    "Xbox": ["xbox", "microsoft"],
    "Twitch": ["twitch"],
    "Reddit": ["reddit"],
    "ProtonMail": ["protonmail", "proton"],
    "Zoho": ["zoho"],
    "Quora": ["quora"],
    "StackOverflow": ["stackoverflow"],
    "Indeed": ["indeed"],
    "Upwork": ["upwork"],
    "Fiverr": ["fiverr"],
    "Glassdoor": ["glassdoor"],
    "Booking.com": ["booking.com", "booking"],
    "Careem": ["careem"],
    "Swiggy": ["swiggy"],
    "Zomato": ["zomato"],
    "McDonald's": ["mcdonalds", "mcdonald's"],
    "KFC": ["kfc"],
    "Nike": ["nike"],
    "Adidas": ["adidas"],
    "Shein": ["shein"],
    "OnlyFans": ["onlyfans"],
    "Tinder": ["tinder"],
    "Bumble": ["bumble"],
    "Grindr": ["grindr"],
    "Line": ["line"],
    "WeChat": ["wechat"],
    "VK": ["vk", "vkontakte"],
    "Unknown": ["unknown"]
}

SERVICE_EMOJIS = {
    "Telegram": "📩", "WhatsApp": "🟢", "Facebook": "📘", "Instagram": "📸", "Messenger": "💬",
    "Google": "🔍", "Gmail": "✉️", "YouTube": "▶️", "Twitter": "🐦", "X": "❌",
    "TikTok": "🎵", "Snapchat": "👻", "Amazon": "🛒", "eBay": "📦", "AliExpress": "📦",
    "Alibaba": "🏭", "Flipkart": "📦", "Microsoft": "🪟", "Outlook": "📧", "Skype": "📞",
    "Netflix": "🎬", "Spotify": "🎶", "Apple": "🍏", "iCloud": "☁️", "PayPal": "💰",
    "Stripe": "💳", "Cash App": "💵", "Venmo": "💸", "Zelle": "🏦", "Wise": "🌐",
    "Binance": "🪙", "Coinbase": "🪙", "KuCoin": "🪙", "Bybit": "📈", "OKX": "🟠",
    "Huobi": "🔥", "Kraken": "🐙", "MetaMask": "🦊", "Discord": "🗨️", "Steam": "🎮",
    "Epic Games": "🕹️", "PlayStation": "🎮", "Xbox": "🎮", "Twitch": "📺", "Reddit": "👽",
    "Yahoo": "🟣", "ProtonMail": "🔐", "Zoho": "📬", "Quora": "❓", "StackOverflow": "🧑‍💻",
    "LinkedIn": "💼", "Indeed": "📋", "Upwork": "🧑‍💻", "Fiverr": "💻", "Glassdoor": "🔎",
    "Airbnb": "🏠", "Booking.com": "🛏️", "Uber": "🚗", "Lyft": "🚕", "Bolt": "🚖",
    "Careem": "🚗", "Swiggy": "🍔", "Zomato": "🍽️", "Foodpanda": "🍱",
    "McDonald's": "🍟", "KFC": "🍗", "Nike": "👟", "Adidas": "👟", "Shein": "👗",
    "OnlyFans": "🔞", "Tinder": "🔥", "Bumble": "🐝", "Grindr": "😈", "Signal": "🔐",
    "Viber": "📞", "Line": "💬", "WeChat": "💬", "VK": "🌐", "Unknown": "❓"
}

def get_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📱 NUMBER CHANNEL", url=NUMBER_CHANNEL_URL),
            InlineKeyboardButton("🔑 OTP GROUP", url=OTP_GROUP_URL),
        ],
        [
            InlineKeyboardButton("👤 OWNER", url=OWNER_URL),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def load_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE):
        try:
            with open(CHAT_IDS_FILE, 'w') as f:
                json.dump(INITIAL_CHAT_IDS, f)
        except Exception as e:
            logger.error(f"Error creating chat IDs file: {e}")
        return INITIAL_CHAT_IDS
    try:
        with open(CHAT_IDS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading chat IDs: {e}")
        return INITIAL_CHAT_IDS

def save_chat_ids(chat_ids):
    try:
        with open(CHAT_IDS_FILE, 'w') as f:
            json.dump(chat_ids, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving chat IDs: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) in ADMIN_CHAT_IDS:
        welcome_msg = (
            f"🚀 Welcome Admin!\n\n"
            f"You can use the following commands:\n"
            f"/add_chat <chat_id> - Add a new chat ID\n"
            f"/remove_chat <chat_id> - Remove a chat ID\n"
            f"/list_chats - List all chat IDs\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ {SIGNATURE}"
        )
        await update.message.reply_text(welcome_msg, reply_markup=get_inline_keyboard())
    else:
        await update.message.reply_text(
            f"❌ Sorry, you are not authorized to use this bot.\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )

async def add_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_CHAT_IDS:
        await update.message.reply_text(
            f"❌ Sorry, only admins can use this command.\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )
        return
    try:
        new_chat_id = context.args[0]
        chat_ids = load_chat_ids()
        if new_chat_id not in chat_ids:
            chat_ids.append(new_chat_id)
            save_chat_ids(chat_ids)
            await update.message.reply_text(
                f"✅ Chat ID {new_chat_id} successfully added.\n\n✨ {SIGNATURE}",
                reply_markup=get_inline_keyboard()
            )
        else:
            await update.message.reply_text(
                f"⚠️ This chat ID ({new_chat_id}) is already in the list.\n\n✨ {SIGNATURE}",
                reply_markup=get_inline_keyboard()
            )
    except (IndexError, ValueError):
        await update.message.reply_text(
            f"❌ Invalid format. Use: /add_chat <chat_id>\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )

async def remove_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_CHAT_IDS:
        await update.message.reply_text(
            f"❌ Sorry, only admins can use this command.\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )
        return
    try:
        chat_id_to_remove = context.args[0]
        chat_ids = load_chat_ids()
        if chat_id_to_remove in chat_ids:
            chat_ids.remove(chat_id_to_remove)
            save_chat_ids(chat_ids)
            await update.message.reply_text(
                f"✅ Chat ID {chat_id_to_remove} successfully removed.\n\n✨ {SIGNATURE}",
                reply_markup=get_inline_keyboard()
            )
        else:
            await update.message.reply_text(
                f"🤔 This chat ID ({chat_id_to_remove}) was not found in the list.\n\n✨ {SIGNATURE}",
                reply_markup=get_inline_keyboard()
            )
    except (IndexError, ValueError):
        await update.message.reply_text(
            f"❌ Invalid format. Use: /remove_chat <chat_id>\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )

async def list_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_CHAT_IDS:
        await update.message.reply_text(
            f"❌ Sorry, only admins can use this command.\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )
        return
    
    chat_ids = load_chat_ids()
    if chat_ids:
        message = "📜 Currently registered chat IDs:\n\n"
        for cid in chat_ids:
            message += f"• {cid}\n"
        message += f"\n✨ {SIGNATURE}"
        await update.message.reply_text(message, reply_markup=get_inline_keyboard())
    else:
        await update.message.reply_text(
            f"📭 No chat IDs registered.\n\n✨ {SIGNATURE}",
            reply_markup=get_inline_keyboard()
        )

def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def load_processed_ids():
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def save_processed_id(sms_id):
    try:
        processed_ids = load_processed_ids()
        processed_ids.add(sms_id)
        with open(STATE_FILE, 'w') as f:
            json.dump(list(processed_ids), f)
    except Exception as e:
        logger.error(f"Error saving processed ID: {e}")

async def fetch_sms_from_api(client: httpx.AsyncClient, headers: dict, csrf_token: str):
    all_messages = []
    try:
        today = datetime.utcnow()
        start_date = today - timedelta(days=1)
        from_date_str, to_date_str = start_date.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y')
        first_payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        summary_response = await client.post(SMS_API_ENDPOINT, headers=headers, data=first_payload)
        summary_response.raise_for_status()
        summary_soup = BeautifulSoup(summary_response.text, 'html.parser')
        group_divs = summary_soup.find_all('div', {'class': 'pointer'})
        if not group_divs:
            return []
        
        group_ids = [re.search(r"getDetials\('(.+?)'\)", div.get('onclick', '')).group(1) for div in group_divs if re.search(r"getDetials\('(.+?)'\)", div.get('onclick', ''))]
        numbers_url = urljoin(BASE_URL, "portal/sms/received/getsms/number")
        sms_url = urljoin(BASE_URL, "portal/sms/received/getsms/number/sms")

        for group_id in group_ids:
            numbers_payload = {'start': from_date_str, 'end': to_date_str, 'range': group_id, '_token': csrf_token}
            numbers_response = await client.post(numbers_url, headers=headers, data=numbers_payload)
            numbers_soup = BeautifulSoup(numbers_response.text, 'html.parser')
            number_divs = numbers_soup.select("div[onclick*='getDetialsNumber']")
            if not number_divs:
                continue
            phone_numbers = [div.text.strip() for div in number_divs]
            
            for phone_number in phone_numbers:
                sms_payload = {'start': from_date_str, 'end': to_date_str, 'Number': phone_number, 'Range': group_id, '_token': csrf_token}
                sms_response = await client.post(sms_url, headers=headers, data=sms_payload)
                sms_soup = BeautifulSoup(sms_response.text, 'html.parser')
                final_sms_cards = sms_soup.find_all('div', class_='card-body')
                
                for card in final_sms_cards:
                    sms_text_p = card.find('p', class_='mb-0')
                    if sms_text_p:
                        sms_text = sms_text_p.get_text(separator='\n').strip()
                        date_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                        
                        country_name_match = re.match(r'([a-zA-Z\s]+)', group_id)
                        if country_name_match:
                            country_name = country_name_match.group(1).strip()
                        else:
                            country_name = group_id.strip()
                        
                        service = "Unknown"
                        lower_sms_text = sms_text.lower()
                        for service_name, keywords in SERVICE_KEYWORDS.items():
                            if any(keyword in lower_sms_text for keyword in keywords):
                                service = service_name
                                break
                        code_match = re.search(r'(\d{3}-\d{3})', sms_text) or re.search(r'\b(\d{4,8})\b', sms_text)
                        code = code_match.group(1) if code_match else "N/A"
                        unique_id = f"{phone_number}-{sms_text}"
                        flag = COUNTRY_FLAGS.get(country_name, "🏴‍☠️")
                        
                        all_messages.append({
                            "id": unique_id,
                            "time": date_str,
                            "number": phone_number,
                            "country": country_name,
                            "flag": flag,
                            "service": service,
                            "code": code,
                            "full_sms": sms_text
                        })
        return all_messages
    except httpx.RequestError as e:
        logger.error(f"Network issue (httpx): {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching or processing API data: {e}")
        traceback.print_exc()
        return []

async def send_telegram_message(context: ContextTypes.DEFAULT_TYPE, chat_id: str, message_data: dict):
    try:
        time_str = message_data.get("time", "N/A")
        number_str = message_data.get("number", "N/A")
        country_name = message_data.get("country", "N/A")
        flag_emoji = message_data.get("flag", "🏴‍☠️")
        service_name = message_data.get("service", "N/A")
        code_str = message_data.get("code", "N/A")
        full_sms_text = message_data.get("full_sms", "N/A")
        
        service_emoji = SERVICE_EMOJIS.get(service_name, "❓")

        full_message = (
            f"🔔 *You have successfully received OTP*\n\n"
            f"📞 *Number:* `{escape_markdown(number_str)}`\n"
            f"🔑 *Code:* `{escape_markdown(code_str)}`\n"
            f"🏆 *Service:* {service_emoji} {escape_markdown(service_name)}\n"
            f"🌎 *Country:* {escape_markdown(country_name)} {flag_emoji}\n"
            f"⏳ *Time:* `{escape_markdown(time_str)}`\n\n"
            f"💬 *Message:*\n"
            f"```\n{full_sms_text}\n```\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *{escape_markdown(SIGNATURE)}*"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=full_message,
            parse_mode='MarkdownV2',
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Message sent to chat ID: {chat_id}")
    except Exception as e:
        logger.error(f"Error sending message to chat ID {chat_id}: {e}")

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Checking for new messages at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        try:
            logger.info("Attempting to log in to ivasms.com...")
            login_page_res = await client.get(LOGIN_URL, headers=headers)
            
            if login_page_res.status_code == 403:
                logger.warning("Access blocked by ivasms.com (403 Forbidden). Website may be blocking cloud servers.")
                return
            
            if login_page_res.status_code != 200:
                logger.error(f"Failed to load login page. Status: {login_page_res.status_code}")
                return
                
            soup = BeautifulSoup(login_page_res.text, 'html.parser')
            token_input = soup.find('input', {'name': '_token'})
            login_data = {'email': USERNAME, 'password': PASSWORD}
            if token_input:
                login_data['_token'] = token_input['value']
            
            headers['Referer'] = LOGIN_URL
            headers['Origin'] = BASE_URL.rstrip('/')
            
            login_res = await client.post(LOGIN_URL, data=login_data, headers=headers)
            
            if login_res.status_code == 403:
                logger.warning("Login blocked by ivasms.com (403 Forbidden).")
                return
            
            if "login" in str(login_res.url):
                logger.error("Login failed. Check username/password.")
                return

            logger.info("Login successful!")
            dashboard_soup = BeautifulSoup(login_res.text, 'html.parser')
            csrf_token_meta = dashboard_soup.find('meta', {'name': 'csrf-token'})
            if not csrf_token_meta:
                logger.error("New CSRF token not found.")
                return
            csrf_token = csrf_token_meta.get('content')

            headers['Referer'] = str(login_res.url)
            messages = await fetch_sms_from_api(client, headers, csrf_token)
            if not messages:
                logger.info("No new messages found.")
                return

            processed_ids = load_processed_ids()
            chat_ids_to_send = load_chat_ids()
            new_messages_found = 0
            
            for msg in reversed(messages):
                if msg["id"] not in processed_ids:
                    new_messages_found += 1
                    logger.info(f"New message found from: {msg['number']}")
                    for chat_id in chat_ids_to_send:
                        await send_telegram_message(context, chat_id, msg)
                    save_processed_id(msg["id"])
            
            if new_messages_found > 0:
                logger.info(f"Total {new_messages_found} new messages sent to Telegram.")

        except httpx.RequestError as e:
            logger.error(f"Network or login issue (httpx): {e}")
        except Exception as e:
            logger.error(f"A problem occurred in the main process: {e}")
            traceback.print_exc()

def main():
    logger.info("🚀 iVasms to Telegram Bot is starting...")
    logger.info(f"Bot by {SIGNATURE}")

    if not YOUR_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set.")
        return
    
    if not USERNAME or not PASSWORD:
        logger.error("IVASMS_USERNAME or IVASMS_PASSWORD environment variable is not set.")
        return

    if not ADMIN_CHAT_IDS:
        logger.error("ADMIN_CHAT_IDS is not configured.")
        return

    logger.info(f"Admin IDs: {ADMIN_CHAT_IDS}")
    logger.info(f"Initial Chat IDs: {INITIAL_CHAT_IDS}")

    application = Application.builder().token(YOUR_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add_chat", add_chat_command))
    application.add_handler(CommandHandler("remove_chat", remove_chat_command))
    application.add_handler(CommandHandler("list_chats", list_chats_command))

    job_queue = application.job_queue
    job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=5)

    logger.info(f"Checking for new messages every {POLLING_INTERVAL_SECONDS} seconds.")
    logger.info("Bot is now online. Ready to listen for commands.")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
