"""MCP server entry point for the MyFlightbook API."""

from mcp.server.fastmcp import FastMCP

from myflightbook_mcp.client import MFBClient

mcp = FastMCP("myflightbook")


@mcp.tool()
async def ping() -> str:
    """Proof-of-life check — returns 'pong'."""
    return "pong"


@mcp.tool()
def get_aircraft(access_token: str) -> list[dict]:
    """
    List all aircraft registered to the MFB user.
    Returns a list of {"id": int, "tail": str, "model": str} dicts.
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).get_aircraft()


@mcp.tool()
def add_aircraft(access_token: str, tail_number: str, model_id: int, instance_type: int = 1) -> dict:
    """
    Register a new aircraft by ICAO tail number and MFB model ID.
    model_id: integer MFB model ID. Find it at myflightbook.com or via MakesAndModels().
    instance_type: 1 = real aircraft (default), 2 = UAS, 3 = simulator.
    Returns the newly created aircraft record {"id", "tail", "model"}.
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).add_aircraft(tail_number, model_id, instance_type)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
