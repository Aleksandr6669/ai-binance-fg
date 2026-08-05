import asyncio
from mcp_server import mcp

if __name__ == "__main__":
    # This runs the FastMCP server using the standard input/output (stdio) transport,
    # which is required for local IDE integrations like Gemini or Cursor.
    mcp.run()
