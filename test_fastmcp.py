import asyncio
from fastmcp import FastMCP, Context
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import contextvars

cv = contextvars.ContextVar("cv", default="default")

class Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = cv.set(request.headers.get("x-auth", "none"))
        try:
            return await call_next(request)
        finally:
            cv.reset(token)

mcp = FastMCP("test")

@mcp.tool()
def test_tool(ctx: Context) -> str:
    req_ctx = ctx.request_context
    return f"cv={cv.get()}, req_ctx={type(req_ctx)}"

mcp._app.add_middleware(Middleware)
mcp.run("stdio")
