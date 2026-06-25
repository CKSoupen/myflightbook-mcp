#!/usr/bin/env bash
# Personal launch wrapper for myflightbook-mcp.
# Sources /opt/cleo/env/mfb.env, refreshes the OAuth2 access token, then
# starts the MCP server with MFB_ACCESS_TOKEN in the environment.
# This allows PA and Dev to call all MFB tools without passing access_token.

set -euo pipefail

ENV_FILE="${MFB_ENV_PATH:-/opt/cleo/env/mfb.env}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Run mfb_oauth_init.py first." >&2
    exit 1
fi

# Load credentials
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Refresh the access token and write new tokens back to mfb.env
NEW_TOKEN=$(python3 - <<'PYEOF'
import json, os, sys, urllib.parse, urllib.request

ENV_FILE = os.environ.get("MFB_ENV_PATH", "/opt/cleo/env/mfb.env")
TOKEN_URL = "https://myflightbook.com/logbook/mvc/oAuth/OAuthToken"
REDIRECT_URI = "https://n8n.rama-family.com/webhook/mfb-oauth-callback"

client_id     = os.environ.get("MFB_CLIENT_ID", "")
client_secret = os.environ.get("MFB_CLIENT_SECRET", "")
refresh_token = os.environ.get("MFB_REFRESH_TOKEN", "")

if not all([client_id, client_secret, refresh_token]):
    # No credentials — fall through to existing token
    sys.stdout.write("")
    sys.exit(0)

payload = urllib.parse.urlencode({
    "grant_type":    "refresh_token",
    "refresh_token": refresh_token,
    "client_id":     client_id,
    "client_secret": client_secret,
    "redirect_uri":  REDIRECT_URI,
}).encode()

try:
    req = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
except Exception as e:
    print(f"Token refresh failed: {e}", file=sys.stderr)
    sys.stdout.write("")
    sys.exit(0)

access_token = result.get("access_token", "")
new_refresh  = result.get("refresh_token", "")

if not access_token:
    print(f"Refresh returned no token: {result}", file=sys.stderr)
    sys.stdout.write("")
    sys.exit(0)

# Update mfb.env in-place
lines = []
with open(ENV_FILE) as f:
    for line in f:
        s = line.strip()
        if s.startswith("MFB_ACCESS_TOKEN="):
            lines.append(f"MFB_ACCESS_TOKEN={access_token}\n")
        elif new_refresh and s.startswith("MFB_REFRESH_TOKEN="):
            lines.append(f"MFB_REFRESH_TOKEN={new_refresh}\n")
        else:
            lines.append(line)

tmp = ENV_FILE + ".tmp"
with open(tmp, "w") as f:
    f.writelines(lines)
import os as _os
_os.chmod(tmp, 0o600)
_os.replace(tmp, ENV_FILE)

sys.stdout.write(access_token)
PYEOF
)

# If refresh produced a new token, export it; otherwise keep the one from mfb.env
if [[ -n "$NEW_TOKEN" ]]; then
    export MFB_ACCESS_TOKEN="$NEW_TOKEN"
fi

exec python3 -m myflightbook_mcp
