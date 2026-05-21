import json
import traceback
import os
from binance_client import BinanceClient

try:
    with open(os.path.expanduser("~/.binance_tracker_config.json")) as f:
        config = json.load(f)
    client = BinanceClient(api_key=config.get("api_key"), api_secret=config.get("api_secret"))
    data = client.get_full_portfolio(fiat_currency="UAH")
    print("Success, keys:", data.keys())
except Exception as e:
    traceback.print_exc()
