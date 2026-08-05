with open("mcp_server.py.new", "r") as f:
    content = f.read()

old_try = """    try:
        client_id = current_client_id.get()
    except LookupError:
        return "ERROR: Authentication context lost. Please reconnect."
"""
new_try = """    client_id = global_session_map.get(ctx.session_id) if hasattr(ctx, "session_id") else None
    if not client_id:
        try:
            client_id = current_client_id.get()
        except LookupError:
            return "ERROR: Authentication context lost. Please reconnect."
"""
content = content.replace(old_try, new_try)
with open("mcp_server.py.new", "w") as f:
    f.write(content)
print("Done")
