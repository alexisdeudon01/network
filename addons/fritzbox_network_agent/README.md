# FRITZ!Box Network Diagnostic Add-on

This add-on is built for Home Assistant OS and bundles:
- `fritzbox-mcp-server` binary (downloaded at container startup with checksum verification)
- Diagnostic engine (`diagnostic.py`) using MCP + Home Assistant REST API
- Flask dashboard exposed via Home Assistant Ingress

## Required add-on options
- `fritz_host` (default `192.168.178.1`)
- `fritz_port` (default `49000`)
- `fritz_username`
- `fritz_password`
- `ha_url` (default `http://supervisor/core`)
- `ha_token` (Home Assistant long-lived access token)

## Notes
- Place this folder under your HAOS local add-ons path.
- Install as a local add-on and start it from Supervisor.
- For ingress-only mode, leave host port mapping disabled.
