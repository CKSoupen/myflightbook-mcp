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


@mcp.tool()
def get_property_types(access_token: str) -> list[dict]:
    """
    List all custom property types available for this MFB user.
    Returns: [{"id": int, "name": str, "type": str}, ...]
    Use the id values in add_flight's custom_properties parameter.
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).get_property_types()


@mcp.tool()
def add_flight(access_token: str, flight: dict) -> int:
    """
    Add a completed flight to the MFB logbook.
    flight dict keys:
      aircraft_id (int), date (str YYYY-MM-DD),
      total_time (float), sic (float), pic (float),
      route (str e.g. "FAJS-FZAA"), landings (int), full_stop_landings (int),
      night_landings (int, optional), comment (str, optional),
      flight_start (str ISO UTC, optional), flight_end (str ISO UTC, optional),
      is_public (bool, optional, default False),
      custom_properties (list of {"prop_id": int, "value": str|int|float|bool}).
    Returns MFB-assigned FlightID (int).
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).add_flight(flight)


@mcp.tool()
def get_flights(
    access_token: str, start_date: str, end_date: str, max_count: int = 50
) -> list[dict]:
    """
    Query flights in MFB logbook by date range (YYYY-MM-DD).
    Returns list of flight records.
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).get_flights(start_date, end_date, max_count)


@mcp.tool()
def check_flight(access_token: str, flight: dict) -> dict:
    """
    Validate a flight entry before committing. Same flight dict shape as add_flight.
    Returns {"valid": bool, "messages": list[str]}.
    Empty messages list means the flight passed validation.
    access_token: caller's MFB OAuth2 bearer token.
    """
    return MFBClient(access_token).check_flight(flight)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
