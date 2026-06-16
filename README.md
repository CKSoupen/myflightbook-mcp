# myflightbook-mcp

An MCP server wrapping the [MyFlightbook](https://myflightbook.com) SOAP API. Lets any AI agent (Claude, etc.) manage a pilot's digital logbook — add flights, manage aircraft, query pending flights, retrieve currency and totals.

**Stateless by design** — no credentials stored in the server. Every tool call accepts the caller's OAuth2 access token, making this safe and reusable by any MFB user.

## Install

```bash
pip install myflightbook-mcp
```

> **Note:** PyPI release is pending. Until then, install from source:

```bash
git clone https://github.com/CKSoupen/myflightbook-mcp.git
cd myflightbook-mcp
pip install -e .
```

## OAuth2 setup

MyFlightbook uses OAuth2. See [OAUTH_SETUP.md](OAUTH_SETUP.md) for the full flow. Quick reference:

1. Register a client app at <https://myflightbook.com/logbook/mvc/oauth>
   - Scopes needed: `addflight readflight readaircraft currency totals`
   - Callback URL: your redirect URI (e.g. `http://localhost:8080/callback`)
2. Authorization URL: `https://myflightbook.com/logbook/mvc/oAuth/Authorize`
3. Token exchange: `POST https://myflightbook.com/logbook/mvc/oAuth/OAuthToken`

## Usage

### As an MCP server (stdio transport)

```bash
myflightbook-mcp
# or
python -m myflightbook_mcp
```

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "myflightbook": {
      "command": "myflightbook-mcp"
    }
  }
}
```

Pass your OAuth2 token as an argument to each tool call — the server itself holds no credentials.

### As a Python library

```python
from myflightbook_mcp.client import MFBClient

client = MFBClient(access_token="your_oauth2_token")
aircraft = client.get_aircraft()
print(aircraft)
# [{'id': 42001, 'tail': 'ZS-SZM', 'model': 'Boeing 737-800'}]
```

## Available MCP tools

| Tool | Description |
|------|-------------|
| `ping` | Proof-of-life check — returns `"pong"` |
| `get_aircraft` | List all aircraft registered to the MFB user |
| `add_aircraft` | Register a new aircraft by tail number and MFB model ID |
| `get_property_types` | List all custom property types (Flight Number, Name of PIC, etc.) |
| `add_flight` | Add a completed flight to the logbook |
| `get_flights` | Query logbook flights by date range |
| `check_flight` | Validate a flight entry before committing |
| `create_pending_flight` | Schedule a pending (future) flight |
| `get_pending_flights` | List all pending flights |
| `update_pending_flight` | Update a pending flight (e.g. add actuals) |
| `commit_pending_flight` | Promote a pending flight to a full logbook entry |
| `delete_pending_flight` | Remove a pending flight |
| `get_currency` | Retrieve pilot currency status (recency, ratings, medical) |
| `get_totals` | Retrieve all-time flight time totals by category and class |

### `add_flight` / `check_flight` flight dict

```python
{
    "aircraft_id": 42001,          # int — from get_aircraft
    "date": "2026-06-16",          # str YYYY-MM-DD
    "total_time": 2.5,             # float (hours)
    "pic": 2.5,                    # float
    "sic": 0.0,                    # float
    "route": "FAJS-FZAA",          # str
    "landings": 1,                 # int
    "full_stop_landings": 1,       # int
    "night_landings": 0,           # int (optional)
    "comment": "SIM CHECK",        # str (optional)
    "flight_start": "2026-06-16T08:00:00",  # str ISO UTC (optional)
    "flight_end":   "2026-06-16T10:30:00",  # str ISO UTC (optional)
    "is_public": False,            # bool (optional)
    "custom_properties": [         # list (optional)
        {"prop_id": 95, "value": "SA001"}   # prop_id from get_property_types
    ]
}
```

### Notes on `commit_pending_flight`

`CommitPendingFlight` returns the remaining pending queue, not the new FlightID. `commit_pending_flight` returns `-1` as a sentinel. If you need the committed entry's FlightID, call `get_flights` with today's date immediately after.

## SOAP service

`https://myflightbook.com/logbook/public/WebService.asmx`
WSDL: `https://myflightbook.com/logbook/public/WebService.asmx?WSDL`

## License

MIT
