#!/usr/bin/env python3
"""Push the dashboard YAML config to Home Assistant via WebSocket API.

Usage:
    uv run --with pyyaml --with websockets scripts/push_dashboard.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import yaml
import websockets


async def push_dashboard():
    hass_host = os.environ.get("HASS_HOST", "http://192.168.0.35:8123")
    hass_token = os.environ.get("HASS_TOKEN")

    if not hass_token:
        print("Error: HASS_TOKEN environment variable is required")
        sys.exit(1)

    dashboard_path = Path(__file__).parent.parent / "config" / "dashboards" / "smart_home.yaml"
    if not dashboard_path.exists():
        print(f"Error: Dashboard file not found: {dashboard_path}")
        sys.exit(1)

    with open(dashboard_path) as f:
        config = yaml.safe_load(f)

    ws_url = hass_host.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"

    async with websockets.connect(ws_url) as ws:
        msg = json.loads(await ws.recv())
        assert msg["type"] == "auth_required"

        await ws.send(json.dumps({"type": "auth", "access_token": hass_token}))
        msg = json.loads(await ws.recv())
        if msg["type"] != "auth_ok":
            print(f"Auth failed: {msg}")
            sys.exit(1)

        await ws.send(json.dumps({
            "id": 1,
            "type": "lovelace/config/save",
            "config": config,
        }))
        msg = json.loads(await ws.recv())
        if msg.get("success"):
            print("Dashboard pushed successfully!")
        else:
            print(f"Failed: {msg}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(push_dashboard())
