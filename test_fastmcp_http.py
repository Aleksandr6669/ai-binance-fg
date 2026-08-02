import asyncio
from fastmcp import FastMCP
from starlette.testclient import TestClient

mcp = FastMCP("test")
app = mcp.http_app(transport="http", path="/")

client = TestClient(app)
print("GET / ->", client.get("/").status_code)
print("POST / ->", client.post("/").status_code)
