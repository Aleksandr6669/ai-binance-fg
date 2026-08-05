from fastmcp import FastMCP, Context
from binance_client import BinanceClient
from typing import Optional
import os
import database

import contextvars

current_client_id = contextvars.ContextVar("current_client_id")
global_session_map = {}

def get_client_id_from_ctx(ctx):
    print(f"[AUTH DEBUG] get_client_id_from_ctx called. ctx={ctx}", flush=True)
    if ctx and hasattr(ctx, 'session_id') and ctx.session_id:
        sid = str(ctx.session_id).replace('-', '')
        cid = global_session_map.get(sid)
        print(f"[AUTH DEBUG] session_id={ctx.session_id}, sid={sid}, client_id={cid}, map_keys={list(global_session_map.keys())}", flush=True)
        return cid
    print("[AUTH DEBUG] ctx has no session_id!", flush=True)
    return None

import mcp.types

mcp = FastMCP(
    "Binance Trading Server",
    instructions="""Это сервер для торговли на бирже Binance. 
Если пользователь просит узнать баланс, выставить ордер или отменить его — используй соответствующие инструменты (tools) этого сервера. 
Ключи Binance хранятся в базе данных сервера персонально для каждого пользователя (привязка по Client ID). 
Если при вызове инструмента сервер возвращает ошибку об отсутствии ключей, вежливо попроси пользователя предоставить его Binance API Key и API Secret в чате, а затем используй инструмент save_binance_credentials, чтобы сохранить их.
Никогда не запрашивай Client ID и Client Secret — они используются только на этапе подключения (OAuth).""",
    icons=[
        mcp.types.Icon(src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgdmlld0JveD0iMCAwIDI1NiAyNTYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjI1NiIgaGVpZ2h0PSIyNTYiIHJ4PSI1MCIgZmlsbD0iI0ZDRDUzNSIvPjxwYXRoIGQ9Ik0xMjggNTAgTDE2OCA5MCBMMTI4IDEzMCBMODggOTAgWiIgZmlsbD0iIzBCMEUxMSIvPjxwYXRoIGQ9Ik0xMjggMjA2IEwxNjggMTY2IEwxMjggMTI2IEw4OCAxNjYgWiIgZmlsbD0iIzBCMEUxMSIvPjxwYXRoIGQ9Ik01MCAxMjggTDkwIDg4IEwxMzAgMTI4IEw5MCAxNjggWiIgZmlsbD0iIzBCMEUxMSIvPjxwYXRoIGQ9Ik0yMDYgMTI4IEwxNjYgODggTDEyNiAxMjggTDE2NiAxNjggWiIgZmlsbD0iIzBCMEUxMSIvPjxwYXRoIGQ9Ik0xMjggMTAwIEwxNTYgMTI4IEwxMjggMTU2IEwxMDAgMTI4IFoiIGZpbGw9IiMwQjBFMTEiLz48L3N2Zz4K", mimeType="image/svg+xml")
    ]
)

def get_user_client(ctx: Context = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None):
    # Если нейросеть передает ключи напрямую
    if api_key and api_secret:
        return BinanceClient(api_key=api_key, api_secret=api_secret, proxy=proxy)
        
    # Иначе берем ключи из базы данных
    client_id = None
    client_id = get_client_id_from_ctx(ctx)
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            raise Exception("Authentication context lost. Please reconnect the application.")
        
    db_api_key, db_api_secret, db_proxy = database.get_settings(client_id)
    
    # Если ключей нет в БД, пробуем переменные окружения
    env_api_key = os.environ.get("BINANCE_API_KEY")
    env_api_secret = os.environ.get("BINANCE_API_SECRET")
    env_proxy = os.environ.get("BINANCE_PROXY")
    
    final_api_key = db_api_key if db_api_key else env_api_key
    final_api_secret = db_api_secret if db_api_secret else env_api_secret
    
    final_proxy = proxy if proxy else (db_proxy if db_proxy else env_proxy)
    
    if not final_api_key or not final_api_secret:
        raise Exception("Binance API keys not provided in tool arguments, database, or environment variables. Please use 'save_binance_credentials' to save them.")
        
    return BinanceClient(api_key=final_api_key, api_secret=final_api_secret, proxy=final_proxy)

def log_action(action: str, details: str = ""):
    print(f"[Operation Log] Action: {action} | Details: {details}")

@mcp.tool()
def save_binance_credentials(ctx: Context, api_key: str, api_secret: str, proxy: Optional[str] = None) -> str:
    """Save Binance API credentials to the application database.
    Gemini should use this tool when the user provides their Binance keys in the chat.
    The keys will be securely stored and used for all future operations.
    """
    client_id = get_client_id_from_ctx(ctx)
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            return "ERROR: Authentication context lost. Please reconnect."
        
    database.save_settings(client_id, api_key, api_secret, proxy)
    log_action("Saved Credentials", "Binance API credentials were saved to the database.")
    return "Successfully saved Binance API credentials to the database."

@mcp.tool()
def delete_binance_credentials(ctx: Context) -> str:
    """Delete the saved Binance API credentials from the application database."""
    client_id = get_client_id_from_ctx(ctx)
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            return "ERROR: Authentication context lost. Please reconnect."
        
    database.delete_settings(client_id)
    log_action("Deleted Credentials", "Binance API credentials were deleted.")
    return "Successfully deleted Binance API credentials."

@mcp.tool()
def check_binance_credentials_status(ctx: Context) -> str:
    """Check if Binance API credentials are currently saved in the application database."""
    client_id = get_client_id_from_ctx(ctx)
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            return "ERROR: Authentication context lost. Please reconnect."
        
    api_key, _, proxy = database.get_settings(client_id)
    if api_key:
        return f"Credentials ARE saved. Proxy is {'set' if proxy else 'NOT set'}."
    else:
        return "Credentials are NOT saved. Please use save_binance_credentials to set them."

@mcp.tool()
def get_binance_balance(ctx: Context, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch the full Binance portfolio balance in USD and various assets."""
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        log_action("Checked Balance", "Requested full portfolio balance")
        return client.get_full_portfolio()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_open_orders(ctx: Context, symbol: Optional[str] = None, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch open orders for a specific symbol or all symbols.
    - market_type: 'SPOT' or 'FUTURES'
    """
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        orders = client.get_open_orders(symbol=symbol, market_type=market_type)
        log_action("Checked Open Orders", f"Symbol: {symbol or 'ALL'}, Market: {market_type}")
        return {"orders": orders}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_order_history(ctx: Context, symbol: str, market_type: str = "SPOT", limit: int = 500, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch all historical orders (open, canceled, filled) for a specific symbol.
    - market_type: 'SPOT' or 'FUTURES'
    """
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        orders = client.get_all_orders(symbol=symbol, market_type=market_type, limit=limit)
        log_action("Checked Order History", f"Symbol: {symbol}, Market: {market_type}")
        return {"orders": orders}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_positions(ctx: Context, symbol: Optional[str] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch current active positions and their unRealizedProfit on Binance Futures."""
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        positions = client.get_positions(symbol=symbol)
        log_action("Checked Positions", f"Symbol: {symbol or 'ALL'}")
        return {"positions": positions}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def place_binance_order(ctx: Context, symbol: str, side: str, order_type: str, market_type: str = "SPOT", quantity: Optional[float] = None, usdt_amount: Optional[float] = None, wallet_percentage: Optional[float] = None, leverage: Optional[int] = None, price: Optional[float] = None, stop_price: Optional[float] = None, trailing_delta: Optional[int] = None, reduce_only: bool = False, close_position: bool = False, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Place a new order on Binance Spot or Futures.
    - side: 'BUY' or 'SELL'
    - order_type: 'MARKET', 'LIMIT', 'STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT', 'STOP_MARKET', 'TAKE_PROFIT_MARKET', 'TRAILING_STOP_MARKET'
    - market_type: 'SPOT' or 'FUTURES'
    - quantity: Exact amount of crypto to buy/sell (e.g. 0.01)
    - usdt_amount: Buy/sell using exactly this amount of USDT (calculates quantity automatically)
    - wallet_percentage: Buy/sell using this % of your USDT wallet balance (calculates quantity automatically)
    - leverage: Leverage to use (only for FUTURES)
    - price: Required if order_type is 'LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'
    - stop_price: Required for STOP_LOSS or TAKE_PROFIT orders
    - trailing_delta: Trailing stop delta (e.g., 100 for 1%)
    - reduce_only: Ensures the order only reduces an existing position (only for FUTURES)
    - close_position: Closes the entire position for the given symbol and side (only for FUTURES)
    """
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        order_res = client.create_order(
            symbol=symbol, side=side, order_type=order_type, market_type=market_type,
            quantity=quantity, usdt_amount=usdt_amount, wallet_percentage=wallet_percentage,
            leverage=leverage, price=price, stopPrice=stop_price, trailingDelta=trailing_delta,
            reduceOnly=reduce_only, closePosition=close_position
        )
        log_action("Placed Order", f"{side} {order_type} on {symbol} ({market_type})")
        return {"success": True, "order": order_res}
    except Exception as e:
        log_action("Failed to Place Order", f"{side} {order_type} on {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def cancel_binance_order(ctx: Context, symbol: str, order_id: int, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Cancel a specific active order on Binance Spot or Futures."""
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        res = client.cancel_order(symbol=symbol, order_id=order_id, market_type=market_type)
        log_action("Canceled Order", f"Order {order_id} on {symbol} ({market_type})")
        return {"success": True, "result": res}
    except Exception as e:
        log_action("Failed to Cancel Order", f"Order {order_id} on {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def cancel_all_binance_orders(ctx: Context, symbol: str, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Cancel all active orders for a specific symbol on Binance Spot or Futures."""
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        res = client.cancel_all_orders(symbol=symbol, market_type=market_type)
        log_action("Canceled All Orders", f"Symbol {symbol} ({market_type})")
        return {"success": True, "result": res}
    except Exception as e:
        log_action("Failed to Cancel All Orders", f"Symbol {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def place_binance_oco_order(ctx: Context, symbol: str, side: str, quantity: float, price: float, stop_price: float, stop_limit_price: Optional[float] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Place an OCO (One Cancels the Other) order on Binance Spot.
    This allows you to set both a Take Profit (limit) and Stop Loss (stop-limit) simultaneously.
    - side: 'BUY' or 'SELL'
    - quantity: Exact amount of crypto to trade
    - price: The Take Profit limit price
    - stop_price: The Stop Loss trigger price
    - stop_limit_price: The Stop Loss limit price (defaults to stop_price if not provided)
    """
    try:
        client = get_user_client(ctx, api_key, api_secret, proxy)
        res = client.create_oco_order(
            symbol=symbol, side=side, quantity=quantity, 
            price=price, stopPrice=stop_price, stopLimitPrice=stop_limit_price
        )
        log_action("Placed OCO Order", f"{side} on {symbol}, Qty: {quantity}")
        return {"success": True, "order": res}
    except Exception as e:
        log_action("Failed to Place OCO Order", f"{side} on {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_binance_klines(ctx: Context, symbol: str, interval: str, limit: int = 1000, start_time: Optional[int] = None, end_time: Optional[int] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch historical klines (candlesticks).
    interval options: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    If you need maximum history, you must paginate using start_time and end_time.
    """
    try:
        # Пытаемся получить ключи для работы с API
        try:
            client = get_user_client(ctx, api_key, api_secret, proxy)
        except Exception:
            # Если нет авторизации, можно выполнить публичный запрос без ключей
            client = BinanceClient(api_key="", api_secret="", proxy=proxy)
            
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit, start_time=start_time, end_time=end_time)
        return {"klines": klines, "count": len(klines)}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_current_ip(ctx: Context, proxy: Optional[str] = None) -> dict:
    """Get the current external IP address that Binance will see. 
    Useful for whitelisting the IP in Binance API settings.
    """
    import requests
    session = requests.Session()
    try:
        env_proxy = os.environ.get("BINANCE_PROXY")
        final_proxy = proxy if proxy else env_proxy
        
        if final_proxy:
            session.proxies.update({"http": final_proxy, "https": final_proxy})
            
        res = session.get("https://api.ipify.org?format=json", timeout=10)
        res.raise_for_status()
        return {"ip": res.json().get("ip")}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    print("Starting Web Portal and MCP Server...")
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from urllib.parse import parse_qs

    async def authorize(request):
        redirect_uri = request.query_params.get("redirect_uri", "")
        state = request.query_params.get("state", "")
        
        if redirect_uri:
            # We don't need a UI anymore. We just instantly redirect back with a dummy code.
            # Gemini will then call /token with the client_id (Binance API Key) and client_secret.
            url = f"{redirect_uri}?code=dummy_auth_code&state={state}"
            return RedirectResponse(url, status_code=303)
            
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Binance Trading Server</title>
            <meta name="description" content="AI Assistant for Binance">
            <link rel="icon" href="https://cryptologos.cc/logos/bnb-bnb-logo.png" type="image/png">
            <meta property="og:title" content="Binance Trading Server">
            <meta property="og:description" content="AI Assistant for Binance">
            <meta property="og:image" content="https://cryptologos.cc/logos/bnb-bnb-logo.png">
        </head>
        <body>
            <h1>Binance Trading MCP Server</h1>
            <p>This server provides tools to trade on Binance via AI.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    async def favicon(request):
        return RedirectResponse("https://cryptologos.cc/logos/bnb-bnb-logo.png")

    async def token(request):
        body_bytes = await request.body()
        form = parse_qs(body_bytes.decode('utf-8'))
        
        client_id = form.get("client_id", [None])[0]
        client_secret = form.get("client_secret", [None])[0]
        
        if not client_id or not client_secret:
             return JSONResponse({"error": "invalid_client", "details": "Client ID and Secret cannot be empty"}, status_code=401)
             
        # Authenticate or register client via DB
        token_str = database.register_or_verify_client(client_id, client_secret)
        if not token_str:
             return JSONResponse({"error": "invalid_client", "details": "Incorrect Client ID or Secret"}, status_code=401)
        
        return JSONResponse({
            "access_token": token_str,
            "token_type": "bearer",
            "expires_in": 31536000
        })

    class ASGIAuthMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] not in ("http", "websocket"):
                return await self.app(scope, receive, send)

            path = scope.get("path", "")
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                # Do not block /sse probes with 401. Let them pass to FastMCP (which returns 405/406 for probes).
                public_paths = ["/", "/favicon.ico", "/authorize", "/token", "/sse"]
                if path in public_paths or path.startswith("/static/") or path.startswith("/.well-known/"):
                    return await self.app(scope, receive, send)
                else:
                    await self.send_401(send)
                    return

            token = auth_header.split(" ")[1]
            client_id = database.get_client_id_by_token(token)
            if not client_id:
                await self.send_401(send)
                return

            query_string = scope.get("query_string", b"").decode("utf-8")
            print(f"ASGI Request to {scope.get('path', '')} with query_string: {query_string}", flush=True)
            if "session_id=" in query_string:
                import urllib.parse
                parsed_query = urllib.parse.parse_qs(query_string)
                if "session_id" in parsed_query:
                    session_id = parsed_query["session_id"][0]
                    global_session_map[session_id] = client_id

            token_ctx = current_client_id.set(client_id)
            try:
                await self.app(scope, receive, send)
            finally:
                current_client_id.reset(token_ctx)

        async def send_401(self, send):
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b"Bearer")
                ]
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Unauthorized"}'
            })

    class LoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            return response

    # MCP endpoints will be at /sse and /messages
    mcp_app = mcp.http_app(transport="http", path="/sse") 
    
    app = Starlette(routes=[
        Route("/", authorize, methods=["GET"]),
        Route("/favicon.ico", favicon, methods=["GET"]),
        Route("/authorize", authorize, methods=["GET"]),
        Route("/token", token, methods=["POST"]),
        Mount("/", app=mcp_app)
    ], lifespan=mcp_app.lifespan)

    app.add_middleware(ASGIAuthMiddleware)
    app.add_middleware(LoggingMiddleware)
    cors_app = CORSMiddleware(
        app=app,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Web Portal and MCP Server on http://0.0.0.0:{port}")
    uvicorn.run(cors_app, host="0.0.0.0", port=port)
