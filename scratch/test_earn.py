import json
import os
import requests
import time
import hmac
import hashlib

CONFIG_PATH = os.path.expanduser("~/.binance_tracker_config.json")

def sign_query(query_string, secret):
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def main():
    if not os.path.exists(CONFIG_PATH):
        print("Config not found at", CONFIG_PATH)
        return
        
    with open(CONFIG_PATH) as f:
        config = json.load(f)
        
    api_key = config.get("api_key")
    api_secret = config.get("api_secret")
    
    if not api_key or not api_secret:
        print("Missing keys in config")
        return
        
    print("Testing Binance Earn endpoints...")
    
    # Get server time
    try:
        res = requests.get("https://api.binance.com/api/v3/time")
        server_time = res.json()["serverTime"]
    except Exception as e:
        print("Failed to get server time:", e)
        server_time = int(time.time() * 1000)
        
    timestamp = server_time
    query_string = f"timestamp={timestamp}&recvWindow=60000"
    signature = sign_query(query_string, api_secret)
    headers = {"X-MBX-APIKEY": api_key}
    
    # Flexible positions
    try:
        url = f"https://api.binance.com/sapi/v1/simple-earn/flexible/position?{query_string}&signature={signature}"
        res = requests.get(url, headers=headers)
        print("Flexible earn status:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            print("Flexible rows:")
            for row in data.get("rows", []):
                print(f"  Asset: {row.get('asset')}, Total Amount: {row.get('totalAmount')}")
        else:
            print("Response:", res.text)
    except Exception as e:
        print("Error fetching flexible positions:", e)
        
    # Locked positions
    try:
        url = f"https://api.binance.com/sapi/v1/simple-earn/locked/position?{query_string}&signature={signature}"
        res = requests.get(url, headers=headers)
        print("Locked earn status:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            print("Locked rows:")
            for row in data.get("rows", []):
                print(f"  Asset: {row.get('asset')}, Amount: {row.get('amount')}")
        else:
            print("Response:", res.text)
    except Exception as e:
        print("Error fetching locked positions:", e)

if __name__ == "__main__":
    main()
