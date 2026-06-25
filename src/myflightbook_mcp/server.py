"""MCP server entry point for the MyFlightbook API."""

import os

from mcp.server.fastmcp import FastMCP

from myflightbook_mcp.client import MFBClient

mcp = FastMCP("myflightbook")


def _resolve_token(access_token: str | None) -> str:
    """Return provided token, or fall back to MFB_ACCESS_TOKEN environment variable."""
    if access_token:
        return access_token
    token = os.environ.get("MFB_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "access_token not provided and MFB_ACCESS_TOKEN environment variable is not set. "
            "Either pass access_token explicitly or set MFB_ACCESS_TOKEN in the server environment."
        )
    return token


@mcp.tool()
async def ping() -> str:
    """Proof-of-life check — returns 'pong'."""
    return "pong"


@mcp.tool()
def get_aircraft(access_token: str | None = None) -> list[dict]:
    """
    List all aircraft registered to the MFB user.
    Returns a list of {"id": int, "tail": str, "model": str} dicts.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_aircraft()


@mcp.tool()
def add_aircraft(
    tail_number: str, model_id: int, instance_type: int = 1, access_token: str | None = None
) -> dict:
    """
    Register a new aircraft by ICAO tail number and MFB model ID.
    model_id: integer MFB model ID. Find it at myflightbook.com or via MakesAndModels().
    instance_type: 1 = real aircraft (default), 2 = UAS, 3 = simulator.
    Returns the newly created aircraft record {"id", "tail", "model"}.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).add_aircraft(tail_number, model_id, instance_type)


@mcp.tool()
def get_property_types(access_token: str | None = None) -> list[dict]:
    """
    List all custom property types available for this MFB user.
    Returns: [{"id": int, "name": str, "type": str}, ...]
    Use the id values in add_flight's custom_properties parameter.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_property_types()


@mcp.tool()
def add_flight(flight: dict, access_token: str | None = None) -> int:
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
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).add_flight(flight)


@mcp.tool()
def get_flights(
    start_date: str, end_date: str, max_count: int = 50, access_token: str | None = None
) -> list[dict]:
    """
    Query flights in MFB logbook by date range (YYYY-MM-DD).
    Returns list of flight records.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_flights(start_date, end_date, max_count)


@mcp.tool()
def check_flight(flight: dict, access_token: str | None = None) -> dict:
    """
    Validate a flight entry before committing. Same flight dict shape as add_flight.
    Returns {"valid": bool, "messages": list[str]}.
    Empty messages list means the flight passed validation.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).check_flight(flight)


@mcp.tool()
def create_pending_flight(flight: dict, access_token: str | None = None) -> str:
    """
    Schedule a pending (future) flight. Same flight dict shape as add_flight.
    Returns the MFB-assigned PendingID (string UUID).
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).create_pending_flight(flight)


@mcp.tool()
def get_pending_flights(access_token: str | None = None) -> list[dict]:
    """
    List all pending flights for the user.
    Returns list of pending flight dicts (full LogbookEntry fields + PendingID).
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_pending_flights()


@mcp.tool()
def update_pending_flight(
    pending_id: str, flight: dict, access_token: str | None = None
) -> None:
    """
    Update an existing pending flight (e.g. add actuals before committing).
    pending_id: PendingID returned by create_pending_flight.
    flight: same dict shape as add_flight.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    MFBClient(_resolve_token(access_token)).update_pending_flight(pending_id, flight)


@mcp.tool()
def commit_pending_flight(pending_id: str, access_token: str | None = None) -> int:
    """
    Promote a pending flight to a full logbook entry.
    Returns -1 (CommitPendingFlight returns remaining pending list, not the new FlightID).
    Use get_flights() with today's date to retrieve the committed entry if the FlightID is needed.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).commit_pending_flight(pending_id)


@mcp.tool()
def delete_pending_flight(pending_id: str, access_token: str | None = None) -> None:
    """
    Remove a pending flight.
    pending_id: PendingID returned by create_pending_flight.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    MFBClient(_resolve_token(access_token)).delete_pending_flight(pending_id)


@mcp.tool()
def get_currency(access_token: str | None = None) -> list[dict]:
    """
    Retrieve pilot currency status (recency, ratings, medical, etc.).
    Returns list of CurrencyStatusItem dicts with attribute, value, and status fields.
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_currency()


@mcp.tool()
def get_totals(access_token: str | None = None) -> list[dict]:
    """
    Retrieve all-time flight time totals (by category, class, aircraft type, etc.).
    Returns list of TotalsItem dicts. The "Value" field is a float (hours or count).
    access_token: MFB OAuth2 bearer token. If omitted, reads MFB_ACCESS_TOKEN env var.
    """
    return MFBClient(_resolve_token(access_token)).get_totals()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
