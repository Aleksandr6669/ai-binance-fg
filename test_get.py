import requests
import json

url = "https://ai-binance-fg-ii.onrender.com/sse"
headers = {"Accept": "text/event-stream"}
resp = requests.get(url, headers=headers, stream=True)
print(resp.status_code)
for line in resp.iter_lines():
    if line:
        print(line.decode('utf-8'))
        break
