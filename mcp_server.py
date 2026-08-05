from fastmcp import FastMCP
from binance_client import BinanceClient
from typing import Optional
import contextvars
import database

    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "my-client-id")
    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "my-client-secret")
import mcp.types

current_user_id = contextvars.ContextVar("current_user_id", default=None)

# Create an MCP server
mcp = FastMCP("Binance Trading Server", icons=[
    mcp.types.Icon(src="https://cryptologos.cc/logos/binance-coin-bnb-logo.png", mimeType="image/png")
])

def get_user_client(api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None):
    # Если нейросеть передает ключи напрямую
    if api_key and api_secret:
        return BinanceClient(api_key=api_key, api_secret=api_secret, proxy=proxy)
        
    # Иначе берем ключи из базы данных
    user_id = current_user_id.get()
    if not user_id:
        raise Exception("User not authenticated or context missing")
        
    db_api_key, db_api_secret, db_proxy = database.get_user_settings(user_id)
    
    # Приоритет отдаем переданному прокси, если его нет - берем из БД
    final_proxy = proxy if proxy else db_proxy
    
    if not db_api_key or not db_api_secret:
        raise Exception("Binance API keys not configured. Please set them in your dashboard or provide them in the request.")
        
    return BinanceClient(api_key=db_api_key, api_secret=db_api_secret, proxy=final_proxy)

def log_action(action: str, details: str = ""):
    user_id = current_user_id.get()
    if user_id:
        database.log_operation(user_id, action, details)

@mcp.tool()
def get_binance_balance(api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch the full Binance portfolio balance in USD and various assets."""
    try:
        client = get_user_client(api_key, api_secret, proxy)
        log_action("Checked Balance", "Requested full portfolio balance")
        return client.get_full_portfolio()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_open_orders(symbol: Optional[str] = None, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch open orders for a specific symbol or all symbols.
    - market_type: 'SPOT' or 'FUTURES'
    """
    try:
        client = get_user_client(api_key, api_secret, proxy)
        orders = client.get_open_orders(symbol=symbol, market_type=market_type)
        log_action("Checked Open Orders", f"Symbol: {symbol or 'ALL'}, Market: {market_type}")
        return {"orders": orders}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_order_history(symbol: str, market_type: str = "SPOT", limit: int = 500, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch all historical orders (open, canceled, filled) for a specific symbol.
    - market_type: 'SPOT' or 'FUTURES'
    """
    try:
        client = get_user_client(api_key, api_secret, proxy)
        orders = client.get_all_orders(symbol=symbol, market_type=market_type, limit=limit)
        log_action("Checked Order History", f"Symbol: {symbol}, Market: {market_type}")
        return {"orders": orders}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_binance_positions(symbol: Optional[str] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch current active positions and their unRealizedProfit on Binance Futures."""
    try:
        client = get_user_client(api_key, api_secret, proxy)
        positions = client.get_positions(symbol=symbol)
        log_action("Checked Positions", f"Symbol: {symbol or 'ALL'}")
        return {"positions": positions}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def place_binance_order(symbol: str, side: str, order_type: str, market_type: str = "SPOT", quantity: Optional[float] = None, usdt_amount: Optional[float] = None, wallet_percentage: Optional[float] = None, leverage: Optional[int] = None, price: Optional[float] = None, stop_price: Optional[float] = None, trailing_delta: Optional[int] = None, reduce_only: bool = False, close_position: bool = False, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
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
        client = get_user_client(api_key, api_secret, proxy)
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
def cancel_binance_order(symbol: str, order_id: int, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Cancel a specific active order on Binance Spot or Futures."""
    try:
        client = get_user_client(api_key, api_secret, proxy)
        res = client.cancel_order(symbol=symbol, order_id=order_id, market_type=market_type)
        log_action("Canceled Order", f"Order {order_id} on {symbol} ({market_type})")
        return {"success": True, "result": res}
    except Exception as e:
        log_action("Failed to Cancel Order", f"Order {order_id} on {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def cancel_all_binance_orders(symbol: str, market_type: str = "SPOT", api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Cancel all active orders for a specific symbol on Binance Spot or Futures."""
    try:
        client = get_user_client(api_key, api_secret, proxy)
        res = client.cancel_all_orders(symbol=symbol, market_type=market_type)
        log_action("Canceled All Orders", f"Symbol {symbol} ({market_type})")
        return {"success": True, "result": res}
    except Exception as e:
        log_action("Failed to Cancel All Orders", f"Symbol {symbol} - Error: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def place_binance_oco_order(symbol: str, side: str, quantity: float, price: float, stop_price: float, stop_limit_price: Optional[float] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Place an OCO (One Cancels the Other) order on Binance Spot.
    This allows you to set both a Take Profit (limit) and Stop Loss (stop-limit) simultaneously.
    - side: 'BUY' or 'SELL'
    - quantity: Exact amount of crypto to trade
    - price: The Take Profit limit price
    - stop_price: The Stop Loss trigger price
    - stop_limit_price: The Stop Loss limit price (defaults to stop_price if not provided)
    """
    try:
        client = get_user_client(api_key, api_secret, proxy)
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
def get_binance_klines(symbol: str, interval: str, limit: int = 1000, start_time: Optional[int] = None, end_time: Optional[int] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None) -> dict:
    """Fetch historical klines (candlesticks).
    interval options: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    If you need maximum history, you must paginate using start_time and end_time.
    """
    try:
        # Пытаемся получить ключи для работы с API
        try:
            client = get_user_client(api_key, api_secret, proxy)
        except Exception:
            # Если нет авторизации, можно выполнить публичный запрос без ключей
            client = BinanceClient(api_key="", api_secret="", proxy=proxy)
            
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit, start_time=start_time, end_time=end_time)
        return {"klines": klines, "count": len(klines)}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_current_ip(proxy: Optional[str] = None) -> dict:
    """Get the current external IP address that Binance will see. 
    Useful for whitelisting the IP in Binance API settings.
    """
    import requests
    session = requests.Session()
    try:
        user_id = current_user_id.get()
        db_proxy = None
        if user_id:
            _, _, db_proxy = database.get_user_settings(user_id)
        
        final_proxy = proxy if proxy else db_proxy
        
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
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.staticfiles import StaticFiles
    from urllib.parse import parse_qs
    import database

    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "my-client-id")
    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "my-client-secret")

    def render_template(filename: str, context: dict = None):
        if context is None:
            context = {}
        with open(os.path.join("templates", filename), "r", encoding="utf-8") as f:
            content = f.read()
        for k, v in context.items():
            content = content.replace(f"{{{k}}}", str(v))
        return HTMLResponse(content)

    async def authorize(request):
        client_id = request.query_params.get("client_id", "")
        redirect_uri = request.query_params.get("redirect_uri", "")
        state = request.query_params.get("state", "")
        
        if request.session.get("user_id"):
            if redirect_uri:
                auth_code = database.create_auth_code(request.session["user_id"])
                url = f"{redirect_uri}?code={auth_code}&state={state}"
                return RedirectResponse(url, status_code=303)
            return RedirectResponse("/dashboard", status_code=303)
        return render_template("login.html", {"error_html": "", "redirect_uri": redirect_uri, "state": state})

    async def register(request):
        body_bytes = await request.body()
        form = parse_qs(body_bytes.decode('utf-8'))
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        
        if database.register_user(username, password):
            return render_template("login.html", {"error_html": "<div class='error'>Registration successful! Please login.</div>"})
        else:
            return render_template("login.html", {"error_html": "<div class='error'>Username already taken.</div>"})

    async def login(request):
        body_bytes = await request.body()
        form = parse_qs(body_bytes.decode('utf-8'))
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        redirect_uri = form.get("redirect_uri", [""])[0]
        state = form.get("state", [""])[0]
        
        user_id = database.verify_user(username, password)
        if user_id:
            request.session["user_id"] = user_id
            if redirect_uri:
                auth_code = database.create_auth_code(user_id)
                url = f"{redirect_uri}?code={auth_code}&state={state}"
                return RedirectResponse(url, status_code=303)
            return RedirectResponse("/dashboard", status_code=303)
        else:
            return render_template("login.html", {"error_html": "<div class='error'>Invalid login credentials</div>", "redirect_uri": redirect_uri, "state": state})

    async def logout(request):
        request.session.clear()
        return RedirectResponse("/", status_code=303)

    async def dashboard(request):
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse("/", status_code=303)
            
        api_key, api_secret, proxy = database.get_user_settings(user_id)
        api_key_val = api_key if api_key else ""
        api_secret_val = api_secret if api_secret else ""
        proxy_val = proxy if proxy else ""
        
        gemini_api_key = database.get_or_create_api_key(user_id)
        
        import requests
        session = requests.Session()
        if proxy:
            session.proxies.update({"http": proxy, "https": proxy})
        try:
            res = session.get("https://api.ipify.org?format=json", timeout=3)
            res.raise_for_status()
            current_ip = res.json().get("ip")
        except Exception as e:
            current_ip = f"Error fetching IP: {str(e)}"
        
        history = database.get_history(user_id)
        history_rows = ""
        import datetime
        for h in history:
            dt = datetime.datetime.fromtimestamp(h['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            history_rows += f"<tr><td>{dt}</td><td>{h['action']}</td><td>{h['details']}</td></tr>"
        if not history_rows:
            history_rows = "<tr><td colspan='3'>No operations yet.</td></tr>"

        context = {
            "current_ip": current_ip,
            "api_key_val": api_key_val,
            "api_secret_val": api_secret_val,
            "proxy_val": proxy_val,
            "history_rows": history_rows,
            "gemini_api_key": gemini_api_key
        }
        return render_template("dashboard.html", context)

    async def save_keys(request):
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse("/", status_code=303)
            
        body_bytes = await request.body()
        form = parse_qs(body_bytes.decode('utf-8'))
        api_key = form.get("api_key", [""])[0]
        api_secret = form.get("api_secret", [""])[0]
        proxy = form.get("proxy", [""])[0]
        
        database.update_user_settings(user_id, api_key, api_secret, proxy)
        return RedirectResponse("/dashboard", status_code=303)


    async def token(request):
        body_bytes = await request.body()
        form = parse_qs(body_bytes.decode('utf-8'))
        
        client_id = form.get("client_id", [None])[0]
        client_secret = form.get("client_secret", [None])[0]
        code = form.get("code", [None])[0]
        
        if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
            return JSONResponse({"error": "invalid_client"}, status_code=401)
            
        access_token = database.exchange_code_for_token(code)
        if not access_token:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)
            
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 31536000
        })

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            public_paths = ["/", "/sse", "/authorize", "/login", "/register", "/token", "/dashboard", "/save_keys", "/logout"]
            if request.url.path in public_paths or request.url.path.startswith("/static/"):
                return await call_next(request)
            
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse({"error": "Unauthorized. Please provide API Key as Bearer token."}, status_code=401)
                
            token = auth_header.split(" ")[1]
            user_id = database.get_user_by_token(token)
            if not user_id:
                return JSONResponse({"error": "Invalid API Key"}, status_code=401)
            
            token_ctx = current_user_id.set(user_id)
            try:
                return await call_next(request)
            finally:
                current_user_id.reset(token_ctx)

    class LoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            return response

    # MCP endpoints will be at /sse and /messages
    mcp_app = mcp.http_app(transport="http", path="/sse") 
    
    app = Starlette(routes=[
        Route("/", authorize, methods=["GET"]),
        Route("/authorize", authorize, methods=["GET"]),
        Route("/login", login, methods=["POST"]),
        Route("/register", register, methods=["POST"]),
        Route("/logout", logout, methods=["GET"]),
        Route("/dashboard", dashboard, methods=["GET"]),
        Route("/save_keys", save_keys, methods=["POST"]),
        Route("/token", token, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory="static"), name="static"),
        Mount("/", app=mcp_app)
    ], lifespan=mcp_app.lifespan)

    
    # Секретный ключ для подписи сессий (куки)
    SESSION_SECRET = os.environ.get("SESSION_SECRET", "super-secret-session-key-12345")
    app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400)
    app.add_middleware(AuthMiddleware)
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
