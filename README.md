# myflightbook-mcp

An MCP server wrapping the [MyFlightbook](https://myflightbook.com) SOAP API. Any AI agent (Claude, etc.) can install this and manage a pilot's digital logbook.

## What it does

Exposes MyFlightbook operations as MCP tools: add flights, manage aircraft, query pending flights, retrieve currency and totals.

**Stateless by design** — no credentials stored in the server. Every tool call accepts the caller's OAuth2 access token, making this safe and reusable by any MFB user.

## Install

```bash
pip install myflightbook-mcp
```

Or from source:

```bash
git clone https://github.com/CKSoupen/myflightbook-mcp.git
cd myflightbook-mcp
pip install -e .
```

## Getting an OAuth2 token

1. Register a client app at <https://myflightbook.com/logbook/mvc/oauth>
2. Scopes needed: `addflight readflight readaircraft` (add `currency totals` for currency/totals tools)
3. OAuth2 endpoints:
   - Authorization: `https://myflightbook.com/logbook/mvc/oAuth/Authorize`
   - Token exchange: `https://myflightbook.com/logbook/mvc/oAuth/OAuthToken`

## Usage

### As an MCP server (stdio transport, for Claude / other agents)

```bash
myflightbook-mcp
# or
python -m myflightbook_mcp
```

Add to your Claude Desktop `config.json`:

```json
{
  "mcpServers": {
    "myflightbook": {
      "command": "myflightbook-mcp",
      "env": {
        "MFB_ACCESS_TOKEN": "<your_token>"
      }
    }
  }
}
```

### As a Python library

```python
from myflightbook_mcp.client import MFBClient

client = MFBClient(access_token="<your_oauth2_token>")
aircraft = client.get_aircraft()
print(aircraft)
# [{'id': 42001, 'tail': 'ZS-SZM', 'model': 'Boeing 737-800'}]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `ping` | Proof-of-life check |

More tools (aircraft, flights, pending flights, currency, totals) arriving in subsequent releases.

## SOAP service

`https://myflightbook.com/logbook/public/WebService.asmx`  
WSDL: `https://myflightbook.com/logbook/public/WebService.asmx?WSDL`

## License

MIT
