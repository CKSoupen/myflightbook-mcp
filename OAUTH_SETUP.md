# OAuth2 Setup for myflightbook-mcp

MyFlightbook uses OAuth2 for API access. This guide walks through registering a client app and obtaining an access token.

## 1. Register your app

Go to <https://myflightbook.com/logbook/mvc/oauth> and create a new client application.

- **App name:** anything descriptive (e.g. `my-logbook-agent`)
- **Redirect URI:** your callback URL. For local testing: `http://localhost:8080/callback`
- **Scopes to request:**

| Scope | Required for |
|-------|-------------|
| `addflight` | `add_flight`, `create_pending_flight`, `update_pending_flight`, `commit_pending_flight`, `delete_pending_flight` |
| `readflight` | `get_flights`, `get_pending_flights`, `check_flight` |
| `readaircraft` | `get_aircraft`, `add_aircraft`, `get_property_types` |
| `currency` | `get_currency` |
| `totals` | `get_totals` |

Save the **client ID** and **client secret** after registration.

## 2. Authorization code flow

### Step 1 — Build the authorization URL

```
https://myflightbook.com/logbook/mvc/oAuth/Authorize
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=YOUR_REDIRECT_URI
  &scope=addflight+readflight+readaircraft+currency+totals
```

Direct the user to this URL. They log in and approve access. MFB redirects to your `redirect_uri` with `?code=AUTH_CODE`.

### Step 2 — Exchange the code for a token

```bash
curl -X POST https://myflightbook.com/logbook/mvc/oAuth/OAuthToken \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=YOUR_REDIRECT_URI"
```

Response:

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "..."
}
```

### Step 3 — Refresh when expired

```bash
curl -X POST https://myflightbook.com/logbook/mvc/oAuth/OAuthToken \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## 3. Using the token

Pass the `access_token` as the `access_token` argument to every MCP tool call. The server never stores it.

```python
from myflightbook_mcp.client import MFBClient

client = MFBClient(access_token="your_access_token")
print(client.get_aircraft())
```

## Security notes

- Store tokens in environment variables or a secrets manager — never hardcode them.
- Access tokens expire. Build refresh logic into your caller.
- The MFB API uses HTTPS; token values never appear in plaintext on the wire.
