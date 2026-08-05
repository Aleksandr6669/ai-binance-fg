import asyncio
from fastmcp import FastMCP
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

mcp = FastMCP("test")
@mcp.tool()
def hello() -> str:
    return "world"

app = FastAPI()
mcp.attach_to_app(app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
