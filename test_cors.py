from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
mcp = FastMCP("Test")
app = mcp.http_app()
cors_app = CORSMiddleware(app, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
print(type(cors_app))
