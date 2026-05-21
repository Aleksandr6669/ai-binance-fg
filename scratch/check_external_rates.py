import requests

url = "https://open.er-api.com/v6/latest/USD"
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    rates = data.get("rates", {})
    print("External exchange rates:")
    print("  UAH:", rates.get("UAH"))
    print("  EUR:", rates.get("EUR"))
    print("  RUB:", rates.get("RUB"))
except Exception as e:
    print("Error:", e)
