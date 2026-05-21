import sys
sys.path.append("/Users/aleksandrryzenkov/Desktop/ai_binanc_fg")

import os
import json
import time
import hmac
import hashlib
import requests
from binance_client import BinanceClient

CONFIG_PATH = os.path.expanduser("~/.binance_tracker_config.json")

def main():
    if not os.path.exists(CONFIG_PATH):
        print("Config not found.")
        return
        
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except Exception as e:
        print("Error reading config:", e)
        return
        
    api_key = config.get("api_key", "")
    api_secret = config.get("api_secret", "")
    
    client = BinanceClient(api_key, api_secret)
    offset = client._get_server_time_offset()
    
    headers = {"X-MBX-APIKEY": api_key}
    
    print("\n--- Checking API Key Restrictions (GET /sapi/v1/account/apiRestrictions) ---")
    try:
        timestamp = int(time.time() * 1000) + offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/sapi/v1/account/apiRestrictions?{query_string}&signature={signature}"
        res = requests.get(url, headers=headers, timeout=10)
        print("Restrictions Status:", res.status_code)
        if res.status_code == 200:
            print(json.dumps(res.json(), indent=2))
        else:
            print("Error:", res.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    main()
