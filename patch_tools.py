import re

with open("mcp_server.py", "r") as f:
    content = f.read()

# 1. Import Context
if "from fastmcp import FastMCP, Context" not in content:
    content = content.replace("from fastmcp import FastMCP", "from fastmcp import FastMCP, Context")

# 2. Add global_session_map
if "global_session_map = {}" not in content:
    content = content.replace("current_client_id = contextvars.ContextVar(\"current_client_id\")", "current_client_id = contextvars.ContextVar(\"current_client_id\")\nglobal_session_map = {}")

# 3. Update ASGIAuthMiddleware
middleware_code = """
            token = auth_header.split(" ")[1]
            client_id = database.get_client_id_by_token(token)
            if not client_id:
                await self.send_401(send)
                return

            query_string = scope.get("query_string", b"").decode("utf-8")
            if "sessionId=" in query_string:
                import urllib.parse
                parsed_query = urllib.parse.parse_qs(query_string)
                if "sessionId" in parsed_query:
                    session_id = parsed_query["sessionId"][0]
                    global_session_map[session_id] = client_id

            token_ctx = current_client_id.set(client_id)"""
            
if "global_session_map[session_id] = client_id" not in content:
    old_middleware = """
            token = auth_header.split(" ")[1]
            client_id = database.get_client_id_by_token(token)
            if not client_id:
                await self.send_401(send)
                return

            token_ctx = current_client_id.set(client_id)"""
    content = content.replace(old_middleware, middleware_code)

# 4. Update get_user_client definition
old_def = "def get_user_client(api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None):"
new_def = "def get_user_client(ctx: Context = None, api_key: Optional[str] = None, api_secret: Optional[str] = None, proxy: Optional[str] = None):"
content = content.replace(old_def, new_def)

# 5. Update get_user_client body
old_body = """    # Иначе берем ключи из базы данных
    try:
        client_id = current_client_id.get()
    except LookupError:
        raise Exception("Authentication context lost. Please reconnect the application.")"""
new_body = """    # Иначе берем ключи из базы данных
    client_id = None
    if ctx and hasattr(ctx, "session_id"):
        client_id = global_session_map.get(ctx.session_id)
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            raise Exception("Authentication context lost. Please reconnect the application.")"""
content = content.replace(old_body, new_body)

# 6. Update ALL tools
tools = [
    "save_binance_credentials",
    "delete_binance_credentials",
    "check_binance_credentials_status",
    "get_binance_balance",
    "get_binance_open_orders",
    "get_binance_order_history",
    "get_binance_positions",
    "place_binance_order",
    "cancel_binance_order",
    "cancel_all_binance_orders",
    "place_binance_oco_order",
    "get_binance_klines",
    "get_current_ip"
]

for tool in tools:
    # Match def tool_name(...)
    pattern = r"(def " + tool + r"\()([^)]*)(\)\s*(?:->\s*[^:]+)?\s*:)"
    
    def repl(m):
        args = m.group(2)
        if "ctx: Context" not in args:
            if args.strip() == "":
                args = "ctx: Context"
            else:
                args = "ctx: Context, " + args
        return m.group(1) + args + m.group(3)
        
    content = re.sub(pattern, repl, content)
    
    # Also update calls to get_user_client inside the tool
    # Wait, some tools don't call get_user_client
    if tool in ["save_binance_credentials", "delete_binance_credentials", "check_binance_credentials_status"]:
        # These call current_client_id.get() directly
        old_try = """    try:
        client_id = current_client_id.get()
    except LookupError:
        return "Error: Authentication context lost. Please reconnect the application.\"
"""
        new_try = """    client_id = global_session_map.get(ctx.session_id) if hasattr(ctx, "session_id") else None
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            return "Error: Authentication context lost. Please reconnect the application."
"""
        content = content.replace(old_try, new_try)
    else:
        # These call get_user_client
        content = re.sub(r"get_user_client\((?!ctx)", "get_user_client(ctx=ctx, ", content)

with open("mcp_server.py.new", "w") as f:
    f.write(content)
print("Done")
