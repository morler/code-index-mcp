try:
    from mcp.server.fastmcp import FastMCP

    print("FastMCP available:", FastMCP is not None)
except ImportError as e:
    print("FastMCP import error:", e)
