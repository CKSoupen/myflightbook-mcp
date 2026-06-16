"""MCP server entry point for the MyFlightbook API."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("myflightbook")


@mcp.tool()
async def ping() -> str:
    """Proof-of-life check — returns 'pong'."""
    return "pong"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
