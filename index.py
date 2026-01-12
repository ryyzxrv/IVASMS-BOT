import requests
import re
import json
import time
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
import asyncio
import urllib.parse
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
import socket

HAS_CURL_CFFI = False
HAS_TLS_CLIENT = False
HAS_CLOUDSCRAPER = False

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
    logging.info("curl_cffi available - best Cloudflare bypass")
except ImportError:
    pass

if not HAS_CURL_CFFI:
    try:
        import tls_client
        HAS_TLS_CLIENT = True
        logging.info("tls_client available - good Cloudflare bypass")
    except ImportError:
        pass

if not HAS_CURL_CFFI and not HAS_TLS_CLIENT:
    try:
        import cloudscraper
        HAS_CLOUDSCRAPER = True
        logging.info("cloudscraper available")
    except ImportError:
        pass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ADMIN_IDS = [7500869913, 6524840104]

bot_users = set()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = b'''<!DOCTYPE html>
<html><head><title>IVASMS Bot</title></head>
<body><h1>IVASMS Bot is running!</h1><p>Status: OK</p></body></html>'''
        self.wfile.write(response)
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_health_server():
    """Run a simple HTTP server for health checks."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health server listening on 0.0.0.0:{port}")
    server.serve_forever()

BANNER_URL = "https://files.catbox.moe/koc535.jpg"

def get_inline_keyboard():
    """Return inline keyboard with channel/group buttons - vertical layout."""
    keyboard = [
        [InlineKeyboardButton("𝐍ᴜᴍʙᴇʀ 𝐂ʜᴀɴɴᴇʟ", url="https://t.me/mrafrixtech")],
        [InlineKeyboardButton("𝐎ᴛᴘ 𝐆𝐫𝐨𝐮𝐩", url="https://t.me/afrixotpgc")],
        [InlineKeyboardButton("𝐑ᴇɴᴛ sᴄʀɪᴘᴛ", url="https://t.me/jaden_afrix")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_powered_by_caption():
    """Return the powered by caption with auto-updated year."""
    current_year = datetime.now().year
    return f"©ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐀ᴜʀᴏʀᴀ𝐈ɪɴᴄ {current_year}"

def is_admin(user_id):
    return user_id in ADMIN_IDS

BASE_HEADERS = {
    "Host": "www.ivasms.com",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_headers():
    """Get headers with a random user agent."""
    headers = BASE_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    return headers


class UnifiedSession:
    """Wrapper class to provide unified interface for different HTTP libraries."""
    
    def __init__(self):
        self.session_type = None
        self.session = None
        self.cookies = {}
        self._init_session()
    
    def _init_session(self):
        """Initialize the best available session type."""
        if HAS_CURL_CFFI:
            try:
                self.session = curl_requests.Session(impersonate="chrome120")
                self.session_type = "curl_cffi"
                logger.info("Using curl_cffi session (best Cloudflare bypass)")
                return
            except Exception as e:
                logger.warning(f"Failed to create curl_cffi session: {e}")
        
        if HAS_TLS_CLIENT:
            try:
                self.session = tls_client.Session(
                    client_identifier="chrome_120",
                    random_tls_extension_order=True
                )
                self.session_type = "tls_client"
                logger.info("Using tls_client session (good Cloudflare bypass)")
                return
            except Exception as e:
                logger.warning(f"Failed to create tls_client session: {e}")
        
        if HAS_CLOUDSCRAPER:
            try:
                self.session = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'desktop': True,
                    }
                )
                self.session_type = "cloudscraper"
                logger.info("Using cloudscraper session")
                return
            except Exception as e:
                logger.warning(f"Failed to create cloudscraper session: {e}")
        
        # Fallback to requests
        self.session = requests.Session()
        self.session.headers.update(get_random_headers())
        self.session_type = "requests"
        logger.info("Using standard requests session (may face Cloudflare blocks)")
    
    def get(self, url, **kwargs):
        """Perform GET request."""
        headers = kwargs.pop('headers', get_random_headers())
        timeout = kwargs.pop('timeout', 60)
        
        if self.session_type == "curl_cffi":
            return self.session.get(url, headers=headers, timeout=timeout, **kwargs)
        elif self.session_type == "tls_client":
            resp = self.session.get(url, headers=headers, timeout_seconds=timeout, **kwargs)
            return self._wrap_tls_response(resp)
        else:
            return self.session.get(url, headers=headers, timeout=timeout, **kwargs)
    
    def post(self, url, **kwargs):
        """Perform POST request."""
        headers = kwargs.pop('headers', get_random_headers())
        timeout = kwargs.pop('timeout', 60)
        
        if self.session_type == "curl_cffi":
            return self.session.post(url, headers=headers, timeout=timeout, **kwargs)
        elif self.session_type == "tls_client":
            resp = self.session.post(url, headers=headers, timeout_seconds=timeout, **kwargs)
            return self._wrap_tls_response(resp)
        else:
            return self.session.post(url, headers=headers, timeout=timeout, **kwargs)
    
    def _wrap_tls_response(self, resp):
        """Wrap tls_client response to match requests.Response interface."""
        class ResponseWrapper:
            def __init__(self, r):
                self.status_code = r.status_code
                self.text = r.text
                self.content = r.content
                self.url = r.url
                self.headers = r.headers
            
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(f"{self.status_code} Error")
            
            def json(self):
                return json.loads(self.text)
        
        return ResponseWrapper(resp)


def create_session():
    """Create a unified session with best available Cloudflare bypass."""
    return UnifiedSession()


async def send_to_telegram(sms):
    """Send SMS details to Telegram group with banner, buttons, and powered by caption."""
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("BOT_TOKEN or CHAT_ID not set")
        return
    
    bot = Bot(token=bot_token)
    
    message = (
        f"📨 *New SMS Received*\n\n"
        f"📞 *Number*: `+{sms['number']}`\n\n"
        f"💬 *Message*: {sms['message']}\n\n"
        f"🕒 *Time*: {sms['timestamp']}\n\n"
        f"_{get_powered_by_caption()}_"
    )

    try:
        await bot.send_photo(
            chat_id=chat_id,
            photo=BANNER_URL,
            caption=message,
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Sent SMS to Telegram: {sms['message'][:50]}...")
    except Exception as e:
        logger.error(f"Failed to send photo to Telegram: {str(e)}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
        except Exception as e2:
            logger.error(f"Fallback text message also failed: {str(e2)}")


def payload_1(session, max_retries=5):
    """Send GET request to /login to retrieve initial tokens with enhanced retry logic."""
    url = "https://www.ivasms.com/login"
    
    for attempt in range(max_retries):
        try:
            # Random delay to appear more human-like
            time.sleep(random.uniform(3, 7))
            
            headers = get_random_headers()
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            })
            
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Fetching login page...")
            response = session.get(url, headers=headers)
            
            # Check for Cloudflare challenge
            if response.status_code == 403:
                logger.warning(f"Attempt {attempt + 1}: Got 403 Forbidden (Cloudflare block)")
                if "cloudflare" in response.text.lower() or "cf-" in str(response.headers).lower():
                    logger.warning("Detected Cloudflare protection")
                wait_time = random.uniform(30, 60) * (attempt + 1)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                continue
            
            if response.status_code == 503:
                logger.warning(f"Attempt {attempt + 1}: Got 503 Service Unavailable")
                time.sleep(random.uniform(20, 40))
                continue
            
            response.raise_for_status()
            
            # Try multiple patterns to find the token
            token_patterns = [
                r'<input type="hidden" name="_token" value="([^"]+)"',
                r'name="_token"\s+value="([^"]+)"',
                r'value="([^"]+)"\s+name="_token"',
                r'_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            ]
            
            token = None
            for pattern in token_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    token = match.group(1)
                    break
            
            if not token:
                logger.warning(f"Attempt {attempt + 1}: Could not find _token in response")
                # Check if we got a challenge page
                if "challenge" in response.text.lower() or "captcha" in response.text.lower():
                    logger.warning("Detected challenge/captcha page")
                if "just a moment" in response.text.lower():
                    logger.warning("Detected Cloudflare 'Just a moment' page")
                
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(15, 30))
                    continue
                raise ValueError("Could not find _token after all retries")
            
            logger.info(f"Successfully retrieved login token on attempt {attempt + 1}")
            return {"_token": token}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Attempt {attempt + 1} - HTTP Error: {e}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(20, 60) * (attempt + 1)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} - Error: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(15, 40) * (attempt + 1)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            else:
                raise
    
    raise ValueError("Failed to get login token after all retries")


def payload_2(session, _token, max_retries=3):
    """Send POST request to /login with credentials."""
    url = "https://www.ivasms.com/login"
    
    email = os.getenv("IVASMS_EMAIL")
    password = os.getenv("IVASMS_PASSWORD")
    
    if not email or not password:
        raise ValueError("IVASMS_EMAIL or IVASMS_PASSWORD not set in environment variables")
    
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(2, 5))
            
            headers = get_random_headers()
            headers.update({
                "Content-Type": "application/x-www-form-urlencoded",
                "Sec-Fetch-Site": "same-origin",
                "Referer": "https://www.ivasms.com/login",
                "Origin": "https://www.ivasms.com"
            })
            
            data = {
                "_token": _token,
                "email": email,
                "password": password,
                "remember": "on",
            }
            
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Submitting login...")
            response = session.post(url, headers=headers, data=data, allow_redirects=True)
            response.raise_for_status()
            
            # Check if login was successful
            if "/login" in response.url and "portal" not in response.url:
                if "invalid" in response.text.lower() or "incorrect" in response.text.lower():
                    raise ValueError("Invalid email or password")
                if "credentials" in response.text.lower():
                    raise ValueError("Invalid credentials")
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}: Login redirected back, retrying...")
                    time.sleep(random.uniform(5, 10))
                    continue
                raise ValueError("Login failed, redirected back to /login")
            
            logger.info(f"Successfully logged in on attempt {attempt + 1}! URL: {response.url}")
            return response
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} - Payload 2 failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(5, 15))
            else:
                raise


def payload_3(session):
    """Send GET request to /sms/received to get statistics page."""
    url = "https://www.ivasms.com/portal/sms/received"
    
    time.sleep(random.uniform(1, 3))
    
    headers = get_random_headers()
    headers.update({
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://www.ivasms.com/portal"
    })
    
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
        if not token_match:
            # Try alternative pattern
            token_match = re.search(r'name="_token" value="([^"]+)"', response.text)
        if not token_match:
            logger.warning("No CSRF token found in /sms/received response")
            return response, ""
        return response, token_match.group(1)
    except Exception as e:
        logger.error(f"Payload 3 failed: {str(e)}")
        raise


def payload_4(session, csrf_token, from_date, to_date):
    """Send POST request to /sms/received/getsms to fetch SMS statistics."""
    url = "https://www.ivasms.com/portal/sms/received/getsms"
    
    time.sleep(random.uniform(0.5, 1.5))
    
    headers = get_random_headers()
    headers.update({
        "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryhkp0qMozYkZV6Ham",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.ivasms.com/portal/sms/received",
        "Origin": "https://www.ivasms.com"
    })
    
    data = (
        "------WebKitFormBoundaryhkp0qMozYkZV6Ham\r\n"
        "Content-Disposition: form-data; name=\"from\"\r\n"
        "\r\n"
        f"{from_date}\r\n"
        f"------WebKitFormBoundaryhkp0qMozYkZV6Ham\r\n"
        "Content-Disposition: form-data; name=\"to\"\r\n"
        "\r\n"
        f"{to_date}\r\n"
        f"------WebKitFormBoundaryhkp0qMozYkZV6Ham\r\n"
        "Content-Disposition: form-data; name=\"_token\"\r\n"
        "\r\n"
        f"{csrf_token}\r\n"
        "------WebKitFormBoundaryhkp0qMozYkZV6Ham--\r\n"
    )
    
    try:
        response = session.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Payload 4 failed: {str(e)}")
        raise


def parse_statistics(response_text):
    """Parse SMS statistics from response and return range data."""
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        ranges = []
        
        no_sms = soup.find('p', id='messageFlash')
        if no_sms and "You do not have any SMS" in no_sms.text:
            logger.info("No SMS data found in response")
            return ranges
        
        range_cards = soup.find_all('div', class_='card card-body mb-1 pointer')
        for card in range_cards:
            cols = card.find_all('div', class_=re.compile(r'col-sm-\d+|col-\d+'))
            if len(cols) >= 5:
                range_name = cols[0].text.strip()
                count_text = cols[1].find('p').text.strip() if cols[1].find('p') else "0"
                paid_text = cols[2].find('p').text.strip() if cols[2].find('p') else "0"
                unpaid_text = cols[3].find('p').text.strip() if cols[3].find('p') else "0"
                revenue_span = cols[4].find('span', class_='currency_cdr')
                revenue_text = revenue_span.text.strip() if revenue_span else "0.0"
                
                try:
                    count = int(count_text) if count_text else 0
                    paid = int(paid_text) if paid_text else 0
                    unpaid = int(unpaid_text) if unpaid_text else 0
                    revenue = float(revenue_text) if revenue_text else 0.0
                except ValueError as e:
                    logger.warning(f"Error parsing values for {range_name}: {str(e)}")
                    count, paid, unpaid, revenue = 0, 0, 0, 0.0
                
                onclick = card.get('onclick', '')
                range_id_match = re.search(r"getDetials$$'([^']+)'$$", onclick)
                range_id = range_id_match.group(1) if range_id_match else range_name
                
                ranges.append({
                    "range_name": range_name,
                    "range_id": range_id,
                    "count": count,
                    "paid": paid,
                    "unpaid": unpaid,
                    "revenue": revenue
                })
        return ranges
    except Exception as e:
        logger.error(f"Parse statistics failed: {str(e)}")
        return []


def save_to_json(data, filename="sms_statistics.json"):
    """Save range data to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.debug("Data saved to JSON")
    except Exception as e:
        logger.error(f"Failed to save to JSON: {str(e)}")


def load_from_json(filename="sms_statistics.json"):
    """Load range data from JSON file."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to load from JSON: {str(e)}")
        return []


def payload_5(session, csrf_token, to_date, range_name):
    """Send POST request to /sms/received/getsms/number to get numbers for a range."""
    url = "https://www.ivasms.com/portal/sms/received/getsms/number"
    
    time.sleep(random.uniform(0.5, 1))
    
    headers = get_random_headers()
    headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.ivasms.com/portal/sms/received",
        "Origin": "https://www.ivasms.com"
    })
    
    data = {
        "_token": csrf_token,
        "start": "",
        "end": to_date,
        "range": range_name
    }
    
    try:
        response = session.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Payload 5 failed: {str(e)}")
        raise


def parse_numbers(response_text):
    """Parse numbers from the range response."""
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        numbers = []
        
        number_divs = soup.find_all('div', class_='card card-body border-bottom bg-100 p-2 rounded-0')
        for div in number_divs:
            col_div = div.find('div', class_=re.compile(r'col-sm-\d+|col-\d+'))
            if col_div:
                onclick = col_div.get('onclick', '')
                match = re.search(r"'([^']+)','([^']+)'", onclick)
                if match:
                    number, number_id = match.groups()
                    numbers.append({"number": number, "number_id": number_id})
                else:
                    logger.warning(f"Failed to parse onclick: {onclick}")
        return numbers
    except Exception as e:
        logger.error(f"Parse numbers failed: {str(e)}")
        return []


def payload_6(session, csrf_token, to_date, number, range_name):
    """Send POST request to /sms/received/getsms/number/sms to get message details."""
    url = "https://www.ivasms.com/portal/sms/received/getsms/number/sms"
    
    time.sleep(random.uniform(0.3, 0.8))
    
    headers = get_random_headers()
    headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.ivasms.com/portal/sms/received",
        "Origin": "https://www.ivasms.com"
    })
    
    data = {
        "_token": csrf_token,
        "start": "",
        "end": to_date,
        "Number": number,
        "Range": range_name
    }
    
    try:
        response = session.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Payload 6 failed: {str(e)}")
        raise


def parse_message(response_text):
    """Parse message details from response."""
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        message_div = soup.find('div', class_='col-9 col-sm-6 text-center text-sm-start')
        revenue_div = soup.find('div', class_='col-3 col-sm-2 text-center text-sm-start')
        
        message = "No message found"
        if message_div:
            p_tag = message_div.find('p')
            if p_tag:
                message = p_tag.text.strip()
        
        revenue = "0.0"
        if revenue_div:
            span = revenue_div.find('span', class_='currency_cdr')
            if span:
                revenue = span.text.strip()
        
        return {"message": message, "revenue": revenue}
    except Exception as e:
        logger.error(f"Parse message failed: {str(e)}")
        return {"message": "Error parsing message", "revenue": "0.0"}


async def start_command(update, context):
    """Handle /start command in Telegram."""
    try:
        user_id = update.effective_user.id
        bot_users.add(user_id)
        
        welcome_message = (
            "🚀 *IVASMS Bot Started!*\n\n"
            "Monitoring SMS statistics...\n\n"
            f"_{get_powered_by_caption()}_"
        )
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=welcome_message,
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Processed /start command from user {user_id}")
    except Exception as e:
        logger.error(f"Start command failed: {str(e)}")


async def stats_command(update, context):
    """Handle /stats command - Admin only."""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_photo(
                photo=BANNER_URL,
                caption=f"❌ *Access Denied*\n\nThis command is for admins only.\n\n_{get_powered_by_caption()}_",
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
            return
        
        stats_data = load_from_json()
        total_sms = sum(r.get("count", 0) for r in stats_data)
        total_revenue = sum(r.get("revenue", 0) for r in stats_data)
        total_ranges = len(stats_data)
        
        stats_message = (
            "📊 *Bot Statistics*\n\n"
            f"📱 *Total Ranges*: {total_ranges}\n"
            f"📨 *Total SMS*: {total_sms}\n"
            f"💰 *Total Revenue*: ${total_revenue:.2f}\n"
            f"👥 *Bot Users*: {len(bot_users)}\n\n"
            f"_{get_powered_by_caption()}_"
        )
        
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=stats_message,
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Admin {user_id} requested stats")
    except Exception as e:
        logger.error(f"Stats command failed: {str(e)}")


async def broadcast_command(update, context):
    """Handle /broadcast command - Admin only."""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_photo(
                photo=BANNER_URL,
                caption=f"❌ *Access Denied*\n\nThis command is for admins only.\n\n_{get_powered_by_caption()}_",
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
            return
        
        if not context.args:
            await update.message.reply_photo(
                photo=BANNER_URL,
                caption=f"⚠️ *Usage*: /broadcast <message>\n\nExample: `/broadcast Hello everyone!`\n\n_{get_powered_by_caption()}_",
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
            return
        
        broadcast_text = " ".join(context.args)
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        
        success_count = 0
        fail_count = 0
        
        for uid in bot_users:
            try:
                await bot.send_photo(
                    chat_id=uid,
                    photo=BANNER_URL,
                    caption=f"📢 *Broadcast Message*\n\n{broadcast_text}\n\n_{get_powered_by_caption()}_",
                    parse_mode="Markdown",
                    reply_markup=get_inline_keyboard()
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {uid}: {e}")
                fail_count += 1
        
        # Also send to main chat
        try:
            chat_id = os.getenv("CHAT_ID")
            if chat_id:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=BANNER_URL,
                    caption=f"📢 *Broadcast Message*\n\n{broadcast_text}\n\n_{get_powered_by_caption()}_",
                    parse_mode="Markdown",
                    reply_markup=get_inline_keyboard()
                )
        except Exception as e:
            logger.error(f"Failed to send broadcast to main chat: {e}")
        
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=f"✅ *Broadcast Complete*\n\n📤 Sent: {success_count}\n❌ Failed: {fail_count}\n\n_{get_powered_by_caption()}_",
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Admin {user_id} sent broadcast to {success_count} users")
    except Exception as e:
        logger.error(f"Broadcast command failed: {str(e)}")


async def restart_command(update, context):
    """Handle /restart command - Admin only."""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_photo(
                photo=BANNER_URL,
                caption=f"❌ *Access Denied*\n\nThis command is for admins only.\n\n_{get_powered_by_caption()}_",
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
            return
        
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=f"🔄 *Restarting Monitoring...*\n\nThe bot will reconnect to IVASMS.\n\n_{get_powered_by_caption()}_",
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Admin {user_id} requested restart")
    except Exception as e:
        logger.error(f"Restart command failed: {str(e)}")


async def status_command(update, context):
    """Handle /status command - Admin only."""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_photo(
                photo=BANNER_URL,
                caption=f"❌ *Access Denied*\n\nThis command is for admins only.\n\n_{get_powered_by_caption()}_",
                parse_mode="Markdown",
                reply_markup=get_inline_keyboard()
            )
            return
        
        # Determine which session type is active
        session_type = "Unknown"
        if HAS_CURL_CFFI:
            session_type = "curl_cffi (Best)"
        elif HAS_TLS_CLIENT:
            session_type = "tls_client (Good)"
        elif HAS_CLOUDSCRAPER:
            session_type = "cloudscraper"
        else:
            session_type = "requests (Basic)"
        
        status_message = (
            "🤖 *Bot Status*\n\n"
            f"✅ *Status*: Running\n"
            f"🔌 *Session Type*: {session_type}\n"
            f"📅 *Date*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 *Users Tracked*: {len(bot_users)}\n"
            f"🔐 *Admin IDs*: {', '.join(map(str, ADMIN_IDS))}\n\n"
            f"_{get_powered_by_caption()}_"
        )
        
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=status_message,
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"Admin {user_id} checked status")
    except Exception as e:
        logger.error(f"Status command failed: {str(e)}")


async def help_command(update, context):
    """Handle /help command."""
    try:
        user_id = update.effective_user.id
        bot_users.add(user_id)
        
        if is_admin(user_id):
            help_message = (
                "🔧 *Admin Commands*\n\n"
                "📊 /stats - View bot statistics\n"
                "📢 /broadcast <msg> - Send message to all users\n"
                "🔄 /restart - Restart monitoring\n"
                "📡 /status - Check bot status\n"
                "❓ /help - Show this help\n\n"
                f"_{get_powered_by_caption()}_"
            )
        else:
            help_message = (
                "📖 *Available Commands*\n\n"
                "🚀 /start - Start the bot\n"
                "❓ /help - Show this help\n\n"
                f"_{get_powered_by_caption()}_"
            )
        
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=help_message,
            parse_mode="Markdown",
            reply_markup=get_inline_keyboard()
        )
        logger.info(f"User {user_id} requested help")
    except Exception as e:
        logger.error(f"Help command failed: {str(e)}")


async def main():
    """Main function to execute automation and monitor SMS statistics."""
    try:
        # Start health check server first
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        logger.info("Health check server started")
        
        # Give the server a moment to start
        await asyncio.sleep(2)
        
        # Check required environment variables
        bot_token = os.getenv("BOT_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        ivasms_email = os.getenv("IVASMS_EMAIL")
        ivasms_password = os.getenv("IVASMS_PASSWORD")
        
        if not bot_token:
            logger.error("BOT_TOKEN environment variable is not set!")
            raise ValueError("BOT_TOKEN is required")
        
        if not chat_id:
            logger.error("CHAT_ID environment variable is not set!")
            raise ValueError("CHAT_ID is required")
        
        if not ivasms_email or not ivasms_password:
            logger.warning("IVASMS credentials not set - SMS monitoring will not work")
        
        # Set up Telegram bot with polling
        application = Application.builder().token(bot_token).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("restart", restart_command))
        application.add_handler(CommandHandler("status", status_command))
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started successfully")
        
        # If no IVASMS credentials, just keep the bot running
        if not ivasms_email or not ivasms_password:
            logger.info("Running in Telegram-only mode (no IVASMS monitoring)")
            while True:
                await asyncio.sleep(60)
        
        # Calculate date range
        today = datetime.now()
        from_date = today.strftime("%m/%d/%Y")
        to_date = (today + timedelta(days=1)).strftime("%m/%d/%Y")
        
        # Initialize storage
        JSON_FILE = "sms_statistics.json"
        existing_ranges = load_from_json(JSON_FILE)
        existing_ranges_dict = {r["range_name"]: r for r in existing_ranges}
        logger.info("Initialized storage")
        
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        while True:
            try:
                session = create_session()
                logger.info(f"Created new session using {session.session_type}")
                
                session_start = time.time()
                
                # Step 1: Login
                logger.info("Executing Payload 1: GET /login")
                tokens = payload_1(session)
                
                logger.info("Executing Payload 2: POST /login")
                response = payload_2(session, tokens["_token"])
                logger.info(f"Login successful! Redirected to: {response.url}")
                
                consecutive_failures = 0
                
                logger.info("Executing Payload 3: GET /sms/received")
                response, csrf_token = payload_3(session)
                
                # Step 2: Fetch initial statistics
                logger.info(f"Executing Payload 4: POST /sms/received/getsms")
                response = payload_4(session, csrf_token, from_date, to_date)
                ranges = parse_statistics(response.text)
                
                if not existing_ranges:
                    existing_ranges = ranges
                    existing_ranges_dict = {r["range_name"]: r for r in ranges}
                    save_to_json(existing_ranges, JSON_FILE)
                
                # Step 3: Continuous monitoring
                while True:
                    try:
                        # Session validation
                        test_response = session.get("https://www.ivasms.com/portal", headers=get_random_headers())
                        if test_response.status_code == 401 or "/login" in test_response.url:
                            logger.info("Session expired. Re-authenticating...")
                            break
                    except Exception as e:
                        logger.warning(f"Session validation failed: {str(e)}")
                        break
                    
                    # Session age check
                    elapsed_time = time.time() - session_start
                    if elapsed_time > 7200:  # 2 hours
                        logger.info("Session age limit reached. Refreshing...")
                        break
                    
                    # Fetch new statistics
                    response = payload_4(session, csrf_token, from_date, to_date)
                    new_ranges = parse_statistics(response.text)
                    new_ranges_dict = {r["range_name"]: r for r in new_ranges}
                    
                    for range_data in new_ranges:
                        range_name = range_data["range_name"]
                        current_count = range_data["count"]
                        existing_range = existing_ranges_dict.get(range_name)
                        
                        if not existing_range:
                            logger.info(f"New range detected: {range_name}")
                            response = payload_5(session, csrf_token, to_date, range_name)
                            numbers = parse_numbers(response.text)
                            if numbers:
                                for number_data in numbers[::-1]:
                                    logger.info(f"Fetching message for: {number_data['number']}")
                                    response = payload_6(session, csrf_token, to_date, number_data["number"], range_name)
                                    message_data = parse_message(response.text)
                                    
                                    sms = {
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "number": number_data["number"],
                                        "message": message_data["message"],
                                        "range": range_name,
                                        "revenue": message_data["revenue"]
                                    }
                                    await send_to_telegram(sms)
                                
                                existing_ranges.append(range_data)
                                existing_ranges_dict[range_name] = range_data
                        
                        elif current_count > existing_range["count"]:
                            count_diff = current_count - existing_range["count"]
                            logger.info(f"Count increased for {range_name}: +{count_diff}")
                            response = payload_5(session, csrf_token, to_date, range_name)
                            numbers = parse_numbers(response.text)
                            if numbers:
                                for number_data in numbers[-count_diff:][::-1]:
                                    logger.info(f"Fetching message for: {number_data['number']}")
                                    response = payload_6(session, csrf_token, to_date, number_data["number"], range_name)
                                    message_data = parse_message(response.text)
                                    
                                    sms = {
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "number": number_data["number"],
                                        "message": message_data["message"],
                                        "range": range_name,
                                        "revenue": message_data["revenue"]
                                    }
                                    await send_to_telegram(sms)
                                
                                for r in existing_ranges:
                                    if r["range_name"] == range_name:
                                        r["count"] = current_count
                                        r["paid"] = range_data["paid"]
                                        r["unpaid"] = range_data["unpaid"]
                                        r["revenue"] = range_data["revenue"]
                                        break
                                existing_ranges_dict[range_name] = range_data
                    
                    existing_ranges = new_ranges
                    existing_ranges_dict = new_ranges_dict
                    save_to_json(existing_ranges, JSON_FILE)
                    
                    await asyncio.sleep(3 + random.random() * 2)
                    
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error (failure {consecutive_failures}/{max_consecutive_failures}): {str(e)}")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Too many failures. Waiting 5 minutes...")
                    await asyncio.sleep(300)
                    consecutive_failures = 0
                else:
                    retry_delay = min(30 * (2 ** consecutive_failures) + random.uniform(0, 30), 300)
                    logger.info(f"Retrying in {retry_delay:.1f} seconds...")
                    await asyncio.sleep(retry_delay)
    
    except Exception as e:
        logger.error(f"Main loop failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
