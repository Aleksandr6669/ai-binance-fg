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
    
    if not api_key:
        print("API keys not set.")
        return
        
    client = BinanceClient(api_key, api_secret)
    offset = client._get_server_time_offset()
    
    print("Time offset:", offset)

    # 1. Test Portfolio Margin Classic (GET /sapi/v1/portfolio/account)
    print("\n--- Testing Portfolio Margin Classic (GET /sapi/v1/portfolio/account) ---")
    try:
        timestamp = int(time.time() * 1000) + offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        url = f"https://api.binance.com/sapi/v1/portfolio/account?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        res = requests.get(url, headers=headers, timeout=10)
        print("Portfolio Margin Status:", res.status_code)
        if res.status_code == 200:
            print("Response:", res.json())
        else:
            print("Portfolio Margin Error:", res.text)
    except Exception as e:
        print("Portfolio Margin Exception:", e)

    # 2. Test Portfolio Margin PAPI (GET /papi/v1/account)
    print("\n--- Testing Portfolio Margin PAPI (GET /papi/v1/account) ---")
    try:
        timestamp = int(time.time() * 1000) + offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        url = f"https://papi.binance.com/papi/v1/account?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        res = requests.get(url, headers=headers, timeout=10)
        print("PAPI Status:", res.status_code)
        if res.status_code == 200:
            print("Response:", res.json())
        else:
            print("PAPI Error:", res.text)
    except Exception as e:
        print("PAPI Exception:", e)

if __name__ == "__main__":
    main()
