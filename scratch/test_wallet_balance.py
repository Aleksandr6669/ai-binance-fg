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
        print("Config file not found.")
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
        print("API key is empty in config.")
        return
        
    client = BinanceClient(api_key, api_secret)
    offset = client._get_server_time_offset()
    
    try:
        balances = client.get_wallet_balances(offset)
        print("Wallet Balances Response:")
        print(json.dumps(balances, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error fetching wallet balances:", e)

if __name__ == "__main__":
    main()
