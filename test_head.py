import asyncio
from fastmcp import FastMCP
from starlette.testclient import TestClient

mcp = FastMCP("test")
app = mcp.http_app(transport="sse")

client = TestClient(app)
resp = client.head("/sse")
print("Status:", resp.status_code)
print("Headers:", resp.headers)
