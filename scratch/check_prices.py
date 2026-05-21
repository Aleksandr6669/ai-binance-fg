import requests

url = "https://api.binance.com/api/v3/ticker/price"
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    prices = {item["symbol"]: float(item["price"]) for item in data}
    
    print("Matching symbols for UAH:")
    for sym, val in prices.items():
        if "UAH" in sym:
            print(f"  {sym}: {val}")
            
    print("\nMatching symbols for EUR:")
    for sym, val in prices.items():
        if "EUR" in sym:
            print(f"  {sym}: {val}")
            
    print("\nMatching symbols for RUB:")
    for sym, val in prices.items():
        if "RUB" in sym:
            print(f"  {sym}: {val}")

except Exception as e:
    print("Error:", e)
