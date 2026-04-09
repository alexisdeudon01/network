#!/usr/bin/env python3
import json
import os
import subprocess
from dataclasses import dataclass, asdict
from typing import Any, Dict

import requests


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Calls fritz-mcp in one-shot mode (if supported)."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments or {}},
    }
    proc = subprocess.run(
        [_env("MCP_BINARY", "/opt/fritzbox-agent/bin/fritz-mcp"), "--transport", "stdio"],
        input=(json.dumps(payload) + "\n").encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    output = proc.stdout.decode(errors="ignore").strip().splitlines()
    for line in reversed(output):
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == 1:
            return msg
    return {"error": {"message": proc.stderr.decode(errors="ignore") or "No MCP response"}}


def get_ha_entity_state(entity_id: str) -> float | None:
    base = _env("HA_URL", "http://supervisor/core").rstrip("/")
    token = _env("HA_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(f"{base}/api/states/{entity_id}", headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    state = resp.json().get("state")
    try:
        return float(state)
    except (TypeError, ValueError):
        return None


@dataclass
class DiagnosticResult:
    segment: str
    diagnosis: str
    recommendation: str
    raw_metrics: Dict[str, Any]


def run_diagnosis() -> DiagnosticResult:
    speed_down = get_ha_entity_state("sensor.speedtest_download")
    speed_up = get_ha_entity_state("sensor.speedtest_upload")
    ping = get_ha_entity_state("sensor.speedtest_ping")

    rx = call_mcp_tool("GetCommonLinkProperties")
    tx = call_mcp_tool("GetAdslInfo")
    wan = call_mcp_tool("GetStatusInfo")

    rx_rate = float(rx.get("result", {}).get("rx_rate_mbps", 0) or 0)
    tx_rate = float(tx.get("result", {}).get("tx_rate_mbps", 0) or 0)
    wan_up = bool(wan.get("result", {}).get("is_connected", False))

    diagnosis = "Unknown"
    recommendation = "Collect more data and retry diagnosis."
    segment = "baseline"

    if not wan_up:
        segment = "outage"
        diagnosis = "Full outage"
        recommendation = "Trigger FRITZ!Box reboot and check ISP link."
    elif rx_rate < 200 or tx_rate < 200:
        segment = "powerline_critical"
        diagnosis = "Electrical noise/wiring issue"
        recommendation = "Move adapters to different outlets and remove noisy chargers."
    elif 200 <= rx_rate <= 400 or 200 <= tx_rate <= 400:
        segment = "powerline_medium"
        diagnosis = "Partial interference"
        recommendation = "Monitor over time and test alternate outlets."
    elif (speed_down is not None and speed_down < 100) and rx_rate > 400 and tx_rate > 400:
        segment = "isp"
        diagnosis = "ISP bottleneck"
        recommendation = "Retry speedtest and report issue to ISP if persistent."
    elif (speed_down and speed_up and ping is not None) and rx_rate > 400 and tx_rate > 400:
        segment = "local_wifi"
        diagnosis = "Local Wi-Fi issue"
        recommendation = "Check Wi-Fi band, channel congestion, and RSSI near device."

    return DiagnosticResult(
        segment=segment,
        diagnosis=diagnosis,
        recommendation=recommendation,
        raw_metrics={
            "speedtest_download_mbps": speed_down,
            "speedtest_upload_mbps": speed_up,
            "speedtest_ping_ms": ping,
            "powerline_rx_mbps": rx_rate,
            "powerline_tx_mbps": tx_rate,
            "wan_connected": wan_up,
            "mcp_raw": {"rx": rx, "tx": tx, "wan": wan},
        },
    )


if __name__ == "__main__":
    print(json.dumps(asdict(run_diagnosis()), indent=2))
