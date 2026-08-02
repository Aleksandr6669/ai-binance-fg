from fastapi import FastAPI
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
mcp = FastMCP("test")
mcp_app = mcp.http_app(transport="sse")

app.mount("/mcp", mcp_app)
print("Mounted successfully")
