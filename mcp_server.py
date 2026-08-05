from fastmcp import FastMCP
from binance_client import BinanceClient
from typing import Optional
import contextvars
import database

current_user_id = contextvars.ContextVar("current_user_id", default=None)

# Create an MCP server
mcp = FastMCP("Binance Trading Server")

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
    # Если скрипт запущен на Hugging Face Spaces или Render, запускаем SSE-сервер на нужном порту
    if os.environ.get("SPACE_ID") or os.environ.get("RENDER"):
        print("Starting on HF Spaces or Render using SSE...")
        import uvicorn
        from starlette.middleware.cors import CORSMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.middleware.sessions import SessionMiddleware
        from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from urllib.parse import parse_qs
        import database
        
        OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "my-client-id")
        OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "my-client-secret")

        def render_template(title, body):
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; color: #333; }}
                    .container {{ max-width: 600px; margin: 40px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    h2 {{ color: #1a1a1a; margin-top: 0; }}
                    input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; margin: 10px 0 20px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
                    button {{ background-color: #FCD535; color: #181A20; border: none; padding: 12px 20px; border-radius: 4px; font-size: 16px; cursor: pointer; font-weight: bold; width: 100%; }}
                    button:hover {{ background-color: #E6C330; }}
                    .tabs {{ display: flex; margin-bottom: 20px; }}
                    .tab {{ flex: 1; text-align: center; padding: 10px; cursor: pointer; background: #f0f2f5; border-radius: 4px 4px 0 0; }}
                    .tab.active {{ background: white; font-weight: bold; border: 1px solid #ddd; border-bottom: none; }}
                    .form-panel {{ display: none; }}
                    .form-panel.active {{ display: block; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
                    th {{ background-color: #f8f9fa; }}
                </style>
                <script>
                    function switchTab(tabId) {{
                        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                        document.querySelectorAll('.form-panel').forEach(p => p.classList.remove('active'));
                        document.getElementById('tab-' + tabId).classList.add('active');
                        document.getElementById('panel-' + tabId).classList.add('active');
                    }}
                </script>
            </head>
            <body>
                <div class="container">
                    {body}
                </div>
            </body>
            </html>
            """

        async def authorize(request):
            client_id = request.query_params.get("client_id", "")
            redirect_uri = request.query_params.get("redirect_uri", "")
            state = request.query_params.get("state", "")
            
            # If user is already logged in, skip login form
            if request.session.get("user_id"):
                if redirect_uri:
                    auth_code = database.create_auth_code(request.session["user_id"])
                    url = f"{redirect_uri}?code={auth_code}&state={state}"
                    return RedirectResponse(url, status_code=303)
                return RedirectResponse("/dashboard", status_code=303)

            body = f"""
            <h2>Welcome to AI Binance Server</h2>
            <div class="tabs">
                <div id="tab-login" class="tab active" onclick="switchTab('login')">Login</div>
                <div id="tab-register" class="tab" onclick="switchTab('register')">Register</div>
            </div>
            
            <div id="panel-login" class="form-panel active">
                <form action="/login" method="post">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="state" value="{state}">
                    <label>Username</label>
                    <input type="text" name="username" required>
                    <label>Password</label>
                    <input type="password" name="password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
            
            <div id="panel-register" class="form-panel">
                <form action="/register" method="post">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="state" value="{state}">
                    <label>Choose Username</label>
                    <input type="text" name="username" required>
                    <label>Choose Password</label>
                    <input type="password" name="password" required>
                    <button type="submit">Register</button>
                </form>
            </div>
            """
            return HTMLResponse(render_template("Login / Register", body))

        async def register(request):
            body_bytes = await request.body()
            form = parse_qs(body_bytes.decode('utf-8'))
            username = form.get("username", [""])[0]
            password = form.get("password", [""])[0]
            
            if database.register_user(username, password):
                return HTMLResponse(render_template("Success", "<h3>Registration successful!</h3><p>You can now <a href='/authorize'>Login</a>.</p>"))
            else:
                return HTMLResponse(render_template("Error", "<h3>Username already taken.</h3><a href='javascript:history.back()'>Go back</a>"), status_code=400)

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
                else:
                    return RedirectResponse("/dashboard", status_code=303)
            else:
                return HTMLResponse(render_template("Error", "<h3>Invalid login credentials</h3><a href='javascript:history.back()'>Go back</a>"), status_code=401)

        async def logout(request):
            request.session.clear()
            return RedirectResponse("/authorize", status_code=303)

        async def dashboard(request):
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse("/authorize", status_code=303)
                
            api_key, api_secret, proxy = database.get_user_settings(user_id)
            api_key_val = api_key if api_key else ""
            api_secret_val = api_secret if api_secret else ""
            proxy_val = proxy if proxy else ""
            
            # Determine current IP
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

            body = f"""
            <h2>Dashboard</h2>
            <p><a href="/logout">Logout</a></p>
            
            <h3>Current Server / Proxy IP</h3>
            <p><strong>{{current_ip}}</strong></p>
            <p style="font-size: 12px; color: #666;">This is the IP address Binance will see. Add it to your API Key whitelist.</p>
            
            <h3>Binance API Settings</h3>
            <p style="font-size: 14px; color: #666;">Enter your Binance API keys and optional proxy here. The AI will use them securely.</p>
            <form action="/save_keys" method="post" style="margin-bottom: 40px;">
                <label>API Key</label>
                <input type="text" name="api_key" value="{{api_key_val}}">
                
                <label>API Secret</label>
                <input type="password" name="api_secret" value="{{api_secret_val}}">
                
                <label>Proxy URL (Optional, e.g. http://user:pass@ip:port)</label>
                <input type="text" name="proxy" value="{{proxy_val}}">
                
                <button type="submit">Save Settings</button>
            </form>
            
            <h3>Recent AI Operations</h3>
            <table>
                <tr><th>Time</th><th>Action</th><th>Details</th></tr>
                {{history_rows}}
            </table>
            """
            # Fixing python formatting issue with curly braces by using string format properly
            body = body.replace("{{current_ip}}", str(current_ip)).replace("{{api_key_val}}", str(api_key_val)).replace("{{api_secret_val}}", str(api_secret_val)).replace("{{proxy_val}}", str(proxy_val)).replace("{{history_rows}}", str(history_rows))

            return HTMLResponse(render_template("Dashboard", body))

        async def save_keys(request):
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse("/authorize", status_code=303)
                
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
                public_paths = ["/authorize", "/login", "/register", "/token", "/", "/dashboard", "/save_keys", "/logout"]
                if request.url.path in public_paths:
                    return await call_next(request)
                
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                    
                token = auth_header.split(" ")[1]
                user_id = database.get_user_by_token(token)
                if not user_id:
                    return JSONResponse({"error": "Invalid token"}, status_code=401)
                
                # Устанавливаем ContextVar для инструментов MCP
                token_ctx = current_user_id.set(user_id)
                try:
                    return await call_next(request)
                finally:
                    current_user_id.reset(token_ctx)

        class LoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                print(f"INCOMING REQUEST: {request.method} {request.url.path}")
                response = await call_next(request)
                print(f"RESPONSE STATUS: {response.status_code}")
                return response

        # Получаем ASGI приложение из FastMCP
        mcp_app = mcp.http_app(transport="http", path="/")
        
        # Создаем роутинг с поддержкой OAuth и дашборда
        app = Starlette(routes=[
            Route("/authorize", authorize, methods=["GET"]),
            Route("/login", login, methods=["POST"]),
            Route("/register", register, methods=["POST"]),
            Route("/logout", logout, methods=["GET"]),
            Route("/dashboard", dashboard, methods=["GET"]),
            Route("/save_keys", save_keys, methods=["POST"]),
            Route("/token", token, methods=["POST"]),
            Mount("/", app=mcp_app)
        ])
        
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
        uvicorn.run(cors_app, host="0.0.0.0", port=port)
    else:
        # Иначе запускаем стандартный локальный stdio сервер
        mcp.run()
