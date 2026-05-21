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
    
    # 1. Get raw balance
    print("\n--- Raw dapi/v1/balance ---")
    try:
        timestamp = int(time.time() * 1000) + offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"https://dapi.binance.com/dapi/v1/balance?{query_string}&signature={signature}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            non_zero = [b for b in data if float(b.get("balance", 0.0)) > 0]
            print(json.dumps(non_zero, indent=2))
        else:
            print("Status:", res.status_code, "Body:", res.text)
    except Exception as e:
        print("Exception:", e)

    # 2. Get raw account
    print("\n--- Raw dapi/v1/account ---")
    try:
        timestamp = int(time.time() * 1000) + offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"https://dapi.binance.com/dapi/v1/account?{query_string}&signature={signature}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            assets = data.get("assets", [])
            non_zero_assets = [a for a in assets if float(a.get("walletBalance", 0.0)) > 0]
            print("Non-zero Assets:")
            print(json.dumps(non_zero_assets, indent=2))
            
            positions = data.get("positions", [])
            active_positions = [p for p in positions if float(p.get("positionAmt", 0.0)) != 0]
            print("Active Positions:")
            print(json.dumps(active_positions, indent=2))
        else:
            print("Status:", res.status_code, "Body:", res.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    main()
