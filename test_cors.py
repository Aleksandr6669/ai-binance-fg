from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
mcp = FastMCP("Test")
try:
    mcp.add_middleware(Middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]))
    print("Middleware added successfully!")
except Exception as e:
    print(f"Failed to add middleware: {e}")
