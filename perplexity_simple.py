import requests
import random
import string
import time
import json

# Configuration
NUM_CODES_TO_TEST = 10  # Number of random codes to test

# Proxy Configuration (Rotating residential proxy)
PROXY_HOST = "p.webshare.io"
PROXY_PORT = "80"
PROXY_USERNAME = "tzddwtgp-rotate"
PROXY_PASSWORD = "7ueyopt3s288"

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7642033573:AAHV4jyqAa_LMCRVs1NVXHZ5Gr-yMg-ocxU"
TELEGRAM_CHAT_ID = None  # Will be set to the first person who messages the bot

def send_telegram_message(message):
    """Send a message to Telegram"""
    global TELEGRAM_CHAT_ID
    
    if not TELEGRAM_CHAT_ID:
        # Get the chat ID from recent messages
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            response = requests.get(url)
            data = response.json()
            
            if data['ok'] and data['result']:
                TELEGRAM_CHAT_ID = data['result'][-1]['message']['chat']['id']
                print(f"Using Telegram chat ID: {TELEGRAM_CHAT_ID}", flush=True)
            else:
                print("No Telegram messages found. Send a message to the bot first.", flush=True)
                return False
        except Exception as e:
            print(f"Error getting Telegram chat ID: {e}", flush=True)
            return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data)
        return response.json()['ok']
    except Exception as e:
        print(f"Error sending Telegram message: {e}", flush=True)
        return False

def generate_random_code():
    """Generate a random MEO code with 9 additional characters (A-Z, 0-9)"""
    characters = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(characters, k=9))
    return f"MEO{random_part}"

def check_code_requests(code):
    """Check code using requests instead of selenium"""
    try:
        # Set up proxy
        proxies = {
            "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}",
            "https": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"
        }
        
        # Headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # First, get the page to see if we can access it
        response = requests.get(
            "https://www.perplexity.ai/join/p/priority?code", 
            proxies=proxies, 
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            # Check if we can access the page
            if "perplexity" in response.text.lower():
                return code, f"Page accessible via proxy (Status: {response.status_code})"
            else:
                return code, f"Unexpected response content (Status: {response.status_code})"
        else:
            return code, f"HTTP Error: {response.status_code}"
            
    except requests.exceptions.ProxyError:
        return code, "Proxy connection failed"
    except requests.exceptions.Timeout:
        return code, "Request timeout"
    except Exception as e:
        return code, f"Error: {str(e)}"

def main():
    print(f"Starting simplified Perplexity code testing...")
    print(f"Will test MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes")
    print(f"Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}")
    print("=" * 50)
    
    # Send start message to Telegram
    start_msg = f"🚀 <b>Perplexity Code Test Started (Simplified)</b>\n\n"
    start_msg += f"📊 Testing MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes\n"
    start_msg += f"🌍 Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}\n"
    start_msg += f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(start_msg)
    
    # Start with specific test code, then generate random codes
    codes = ["MEO3KPQ7ZR5Q"]  # Test this specific code first
    codes.extend([generate_random_code() for _ in range(NUM_CODES_TO_TEST - 1)])  # Then add random codes
    
    # Test codes and send live results
    working_codes = []
    
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{NUM_CODES_TO_TEST}] Testing code: {code}", flush=True)
        code_value, status = check_code_requests(code)
        
        # Format result for display and Telegram
        send_to_telegram = True  # Send all results for simplified version
        
        if "accessible" in status.lower():
            display_msg = f"✅ Code {code}: {status}"
            telegram_msg = f"✅ <code>{code}</code>\n📡 {status}"
        elif "error" in status.lower():
            display_msg = f"❌ Code {code}: {status}"
            telegram_msg = f"❌ <code>{code}</code>\n🚫 {status}"
        else:
            display_msg = f"❓ Code {code}: {status}"
            telegram_msg = f"❓ <code>{code}</code>\n⚠️ {status}"
        
        print(f"[{i}/{NUM_CODES_TO_TEST}] {display_msg}", flush=True)
        
        # Send individual result to Telegram
        if send_to_telegram:
            progress_msg = f"[{i}/{NUM_CODES_TO_TEST}] {telegram_msg}"
            send_telegram_message(progress_msg)
        
        # Small delay between requests
        time.sleep(2)
    
    # Send final summary to Telegram
    summary_msg = f"📋 <b>Simplified Test Completed!</b>\n\n"
    summary_msg += f"📊 Tested: {NUM_CODES_TO_TEST} codes\n"
    summary_msg += f"✅ Working: {len(working_codes)} codes\n"
    summary_msg += f"⏰ Finished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    summary_msg += f"ℹ️ This was a simplified test to check proxy connectivity"
    
    send_telegram_message(summary_msg)
    
    print(f"\n" + "=" * 50)
    print(f"Simplified testing completed!")
    print(f"Results sent to Telegram!")

if __name__ == "__main__":
    main()