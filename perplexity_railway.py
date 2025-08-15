import concurrent.futures
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import string
import time
import os
import zipfile
import tempfile
import requests

# Configuration
NUM_CODES_TO_TEST = 10  # Number of random codes to test
MAX_WORKERS = 1  # Number of parallel browsers (reduced to avoid file conflicts)

# Proxy Configuration (Rotating residential proxy)
PROXY_HOST = "p.webshare.io"
PROXY_PORT = "80"
PROXY_USERNAME = "tzddwtgp-rotate"
PROXY_PASSWORD = "7ueyopt3s288"
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7642033573:AAHV4jyqAa_LMCRVs1NVXHZ5Gr-yMg-ocxU"
TELEGRAM_CHAT_ID = None  # Will be set to the first person who messages the bot

# URL to visit
url = "https://www.perplexity.ai/join/p/priority?code"

def create_proxy_extension(host, port, username, password):
    """Create a Chrome extension for proxy authentication"""
    import zipfile
    import tempfile
    
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """
    
    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{host}",
                port: parseInt({port})
              }},
              bypassList: ["localhost"]
            }}
          }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{username}",
                password: "{password}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """
    
    # Create temporary directory and files
    temp_dir = tempfile.mkdtemp()
    manifest_path = os.path.join(temp_dir, "manifest.json")
    background_path = os.path.join(temp_dir, "background.js")
    
    with open(manifest_path, "w") as f:
        f.write(manifest_json)
    with open(background_path, "w") as f:
        f.write(background_js)
    
    # Create zip file
    extension_path = os.path.join(temp_dir, "proxy_auth_extension.zip")
    with zipfile.ZipFile(extension_path, 'w') as zip_file:
        zip_file.write(manifest_path, "manifest.json")
        zip_file.write(background_path, "background.js")
    
    return extension_path

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

# Function to check if a code works
def check_code(code):
    try:
        # Set up undetected Chrome with incognito mode and proxy
        options = uc.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument("--headless")  # Enable headless for Railway
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        
        # Add proxy with authentication using Chrome extension method
        proxy_extension = create_proxy_extension(PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD)
        options.add_extension(proxy_extension)
        
        driver = uc.Chrome(options=options, version_main=None)
    except Exception as e:
        return code, f"Driver creation error: {str(e)}"
    try:
        driver.get(url)
        
        # Wait for the input field to be present
        wait = WebDriverWait(driver, 10)
        code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Promo Code"]')))
        
        # Enter the code
        code_input.clear()
        code_input.send_keys(code)
        
        # Find and click the submit button
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        
        # Wait for response message to appear
        import time
        time.sleep(2)  # Give page time to fully load
        
        try:
            error_message_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.text-caution')))
            error_message = error_message_element.text
            print(f"DEBUG: Found error message: '{error_message}'", flush=True)
            
            if "already been redeemed" in error_message.lower():
                return code, f"Already redeemed: {error_message}"
            elif "not eligible in your region" in error_message.lower():
                return code, f"Region restricted: {error_message}"
            elif "invalid" in error_message.lower() or "not valid" in error_message.lower():
                return code, f"Invalid code: {error_message}"
            else:
                return code, f"Error: {error_message}"
        except TimeoutException:
            print("DEBUG: No error message found, checking page content...", flush=True)
            # If no error message, check for success
            page_text = driver.page_source.lower()
            print(f"DEBUG: Page contains 'success': {'success' in page_text}", flush=True)
            print(f"DEBUG: Page contains 'welcome': {'welcome' in page_text}", flush=True)
            if "success" in page_text or "welcome" in page_text or "applied" in page_text:
                return code, "Success"
            else:
                return code, "Unknown response"
    except (NoSuchElementException, TimeoutException) as e:
        return code, f"Error: {str(e)}"
    finally:
        try:
            driver.quit()
        except:
            pass  # Ignore quit errors

def main():
    print(f"Starting random code generation and testing...")
    print(f"Will test MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes")
    print(f"Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}")
    print("=" * 50)
    
    # Send start message to Telegram
    start_msg = f"🚀 <b>Perplexity Code Test Started</b>\n\n"
    start_msg += f"📊 Testing MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes\n"
    start_msg += f"🌍 Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}\n"
    start_msg += f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(start_msg)
    
    # Start with specific test code, then generate random codes
    codes = ["MEO3KPQ7ZR5Q"]  # Test this specific code first
    codes.extend([generate_random_code() for _ in range(NUM_CODES_TO_TEST - 1)])  # Then add random codes
    
    # Test codes and send live results
    working_codes = []
    
    # Use ThreadPoolExecutor for parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_code, code) for code in codes]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            print(f"[{i}/{NUM_CODES_TO_TEST}] Processing result...", flush=True)
            code, status = future.result()
            
            # Format result for display and Telegram
            send_to_telegram = False
            
            if status == "Success":
                display_msg = f"✅ Code {code}: SUCCESS!"
                telegram_msg = f"🎉 <b>SUCCESS!</b>\n<code>{code}</code>\n✅ Working code found!"
                working_codes.append(code)
                send_to_telegram = True
            elif "Already redeemed" in str(status):
                display_msg = f"❌ Code {code}: Already redeemed"
                telegram_msg = f"❌ <code>{code}</code>\n🔄 Already redeemed"
                send_to_telegram = True
            elif "Region restricted" in str(status):
                display_msg = f"🌍 Code {code}: Region restricted"
                telegram_msg = f"🌍 <code>{code}</code>\n🚫 Region restricted"
                send_to_telegram = True
            elif "Invalid" in str(status):
                display_msg = f"🚫 Code {code}: Invalid"
                # Don't send invalid codes to Telegram
                send_to_telegram = False
            else:
                display_msg = f"❓ Code {code}: {status}"
                # Don't send unknown status to Telegram
                send_to_telegram = False
            
            print(f"[{i}/{NUM_CODES_TO_TEST}] {display_msg}", flush=True)
            
            # Send individual result to Telegram only for specific statuses
            if send_to_telegram:
                progress_msg = f"[{i}/{NUM_CODES_TO_TEST}] {telegram_msg}"
                send_telegram_message(progress_msg)
    
    # Send final summary to Telegram
    summary_msg = f"📋 <b>Test Completed!</b>\n\n"
    summary_msg += f"📊 Tested: {NUM_CODES_TO_TEST} codes\n"
    summary_msg += f"✅ Working: {len(working_codes)} codes\n"
    summary_msg += f"⏰ Finished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if working_codes:
        summary_msg += f"🎉 <b>WORKING CODES:</b>\n"
        for code in working_codes:
            summary_msg += f"<code>{code}</code>\n"
    else:
        summary_msg += f"😔 No working codes found this time"
    
    send_telegram_message(summary_msg)
    
    print(f"\n" + "=" * 50)
    print(f"Testing completed!")
    print(f"Working codes found: {len(working_codes)}")
    if working_codes:
        print("🎉 WORKING CODES:")
        for code in working_codes:
            print(f"   {code}")
    print(f"Results sent to Telegram!")

if __name__ == "__main__":
    main()