from fastmcp import FastMCP
mcp = FastMCP("test")
app = mcp.http_app(transport="http", path="/")
for route in app.routes:
    print(route.path, route.methods)
