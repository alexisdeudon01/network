#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template

from diagnostic import run_diagnosis

app = Flask(__name__)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def get_state(entity_id: str):
    base = _env("HA_URL", "http://supervisor/core").rstrip("/")
    token = _env("HA_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(f"{base}/api/states/{entity_id}", headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    return resp.json().get("state")


def color_for_sync(rate):
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        return "gray"
    if rate > 400:
        return "green"
    if rate >= 200:
        return "orange"
    return "red"


@app.route("/")
def index():
    metrics = {
        "download": get_state("sensor.speedtest_download"),
        "upload": get_state("sensor.speedtest_upload"),
        "ping": get_state("sensor.speedtest_ping"),
        "rx": get_state("sensor.fritz_powerline_1260e_rx_rate"),
        "tx": get_state("sensor.fritz_powerline_1260e_tx_rate"),
    }
    return render_template(
        "index.html",
        metrics=metrics,
        rx_color=color_for_sync(metrics["rx"]),
        tx_color=color_for_sync(metrics["tx"]),
        refresh_seconds=int(_env("AUTO_REFRESH_SECONDS", "30")),
    )


@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    report = run_diagnosis()
    return jsonify(report.__dict__)


@app.route("/api/reboot", methods=["POST"])
def reboot():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "Reboot", "arguments": {}},
    }
    proc = subprocess.run(
        [_env("MCP_BINARY", "/opt/fritzbox-agent/bin/fritz-mcp"), "--transport", "stdio"],
        input=(json.dumps(payload) + "\n").encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    return jsonify({"stdout": proc.stdout.decode(errors="ignore"), "stderr": proc.stderr.decode(errors="ignore")})


if __name__ == "__main__":
    app.run(host=_env("FLASK_HOST", "0.0.0.0"), port=int(_env("FLASK_PORT", "8099")))
