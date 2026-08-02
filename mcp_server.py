from mcp.server.fastmcp import FastMCP
from binance_client import BinanceClient

# Create an MCP server
mcp = FastMCP("Binance")

@mcp.tool()
def get_binance_balance(api_key: str, api_secret: str, proxy: str = None) -> dict:
    """Fetch the full Binance portfolio balance in USD and various assets.
    The proxy should be in the format 'http://user:pass@ip:port' or 'http://ip:port'.
    """
    client = BinanceClient(api_key=api_key, api_secret=api_secret, proxy=proxy)
    try:
        return client.get_full_portfolio()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_open_orders(api_key: str, api_secret: str, symbol: str = None, proxy: str = None) -> dict:
    """Fetch open orders for a specific symbol or all symbols.
    """
    client = BinanceClient(api_key=api_key, api_secret=api_secret, proxy=proxy)
    try:
        orders = client.get_open_orders(symbol)
        return {"orders": orders}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def place_binance_order(api_key: str, api_secret: str, symbol: str, side: str, order_type: str, market_type: str = "SPOT", quantity: float = None, usdt_amount: float = None, wallet_percentage: float = None, leverage: int = None, price: float = None, stop_price: float = None, trailing_delta: int = None, proxy: str = None) -> dict:
    """Place a new order on Binance Spot or Futures.
    - side: 'BUY' or 'SELL'
    - order_type: 'MARKET', 'LIMIT', 'STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'
    - market_type: 'SPOT' or 'FUTURES'
    - quantity: Exact amount of crypto to buy/sell (e.g. 0.01)
    - usdt_amount: Buy/sell using exactly this amount of USDT (calculates quantity automatically)
    - wallet_percentage: Buy/sell using this % of your USDT wallet balance (calculates quantity automatically)
    - leverage: Leverage to use (only for FUTURES)
    - price: Required if order_type is 'LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'
    - stop_price: Required for STOP_LOSS or TAKE_PROFIT orders (if trailing_delta is not used)
    - trailing_delta: Trailing stop delta (e.g., 100 for 1%)
    """
    client = BinanceClient(api_key=api_key, api_secret=api_secret, proxy=proxy)
    try:
        order_res = client.create_order(
            symbol=symbol, side=side, order_type=order_type, market_type=market_type,
            quantity=quantity, usdt_amount=usdt_amount, wallet_percentage=wallet_percentage,
            leverage=leverage, price=price, stopPrice=stop_price, trailingDelta=trailing_delta
        )
        return {"success": True, "order": order_res}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_binance_klines(symbol: str, interval: str, limit: int = 1000, start_time: int = None, end_time: int = None, proxy: str = None) -> dict:
    """Fetch historical klines (candlesticks).
    interval options: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    If you need maximum history, you must paginate using start_time and end_time.
    """
    client = BinanceClient(api_key="", api_secret="", proxy=proxy)
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit, start_time=start_time, end_time=end_time)
        return {"klines": klines, "count": len(klines)}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_current_ip(proxy: str = None) -> dict:
    """Get the current external IP address that Binance will see. 
    Useful for whitelisting the IP in Binance API settings.
    If proxy is provided, it returns the IP of the proxy.
    """
    import requests
    session = requests.Session()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    try:
        res = session.get("https://api.ipify.org?format=json", timeout=10)
        res.raise_for_status()
        return {"ip": res.json().get("ip")}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    # Если скрипт запущен на Hugging Face Spaces, запускаем SSE-сервер на порту 7860
    if os.environ.get("SPACE_ID"):
        print("Starting on Hugging Face Spaces (SSE on port 7860)...")
        mcp.run(transport='sse', host='0.0.0.0', port=7860)
    else:
        # Иначе запускаем стандартный stdio сервер
        mcp.run()
