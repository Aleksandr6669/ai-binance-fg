import re
with open("mcp_server.py", "r") as f:
    code = f.read()

# Restore OAuth variables at the top
if 'OAUTH_CLIENT_ID' not in code:
    code = code.replace('import database', 'import database\n\n    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "my-client-id")\n    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "my-client-secret")')

# Replace authorize function to handle OAuth query params
auth_func_new = '''    async def authorize(request):
        client_id = request.query_params.get("client_id", "")
        redirect_uri = request.query_params.get("redirect_uri", "")
        state = request.query_params.get("state", "")
        
        if request.session.get("user_id"):
            if redirect_uri:
                auth_code = database.create_auth_code(request.session["user_id"])
                url = f"{redirect_uri}?code={auth_code}&state={state}"
                return RedirectResponse(url, status_code=303)
            return RedirectResponse("/dashboard", status_code=303)
        return render_template("login.html", {"error_html": "", "redirect_uri": redirect_uri, "state": state})'''

code = re.sub(r'    async def authorize\(request\):.*?return render_template\("login.html", \{"error_html": ""\}\)', auth_func_new, code, flags=re.DOTALL)

# Replace login function to handle redirect_uri
login_func_new = '''    async def login(request):
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
            return render_template("login.html", {"error_html": "<div class='error'>Invalid login credentials</div>", "redirect_uri": redirect_uri, "state": state})'''

code = re.sub(r'    async def login\(request\):.*?return render_template\("login.html", \{"error_html": "<div class=\'error\'>Invalid login credentials</div>"\}\)', login_func_new, code, flags=re.DOTALL)

# Add token endpoint back
if 'async def token(request):' not in code:
    token_code = '''
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
'''
    code = code.replace('    class AuthMiddleware(BaseHTTPMiddleware):', token_code + '\n    class AuthMiddleware(BaseHTTPMiddleware):')

# Add token route back and fix public paths
code = code.replace('public_paths = ["/", "/authorize", "/login", "/register", "/dashboard", "/save_keys", "/logout"]', 'public_paths = ["/", "/sse", "/authorize", "/login", "/register", "/token", "/dashboard", "/save_keys", "/logout"]')
code = code.replace('Route("/save_keys", save_keys, methods=["POST"]),', 'Route("/save_keys", save_keys, methods=["POST"]),\n        Route("/token", token, methods=["POST"]),')

with open("mcp_server.py", "w") as f:
    f.write(code)
