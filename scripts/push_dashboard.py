#!/usr/bin/env python3
"""Push the dashboard YAML config to Home Assistant via WebSocket API.

Usage:
    uv run --with pyyaml --with websockets scripts/push_dashboard.py [YAML_FILE] [URL_PATH] [ICON]

YAML_FILE defaults to config/dashboards/overview.yaml. URL_PATH names the
dashboard to overwrite (e.g. wall-phone); it is created if missing, with ICON
in the sidebar (default mdi:cellphone-screenshot). Without URL_PATH the default
Overview dashboard is overwritten.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import yaml
import websockets


async def push_dashboard(dashboard_path, url_path, icon):
    hass_host = os.environ.get("HASS_HOST", "http://192.168.68.68:8123")
    hass_token = os.environ.get("HASS_TOKEN")

    if not hass_token:
        print("Error: HASS_TOKEN environment variable is required")
        sys.exit(1)

    if not dashboard_path.exists():
        print(f"Error: Dashboard file not found: {dashboard_path}")
        sys.exit(1)

    with open(dashboard_path, encoding="utf-8") as f:
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

        if url_path:
            await ws.send(json.dumps({"id": 1, "type": "lovelace/dashboards/list"}))
            msg = json.loads(await ws.recv())
            if url_path not in {d["url_path"] for d in msg["result"]}:
                await ws.send(json.dumps({
                    "id": 2,
                    "type": "lovelace/dashboards/create",
                    "url_path": url_path,
                    "title": config.get("title", url_path),
                    "icon": icon,
                    "show_in_sidebar": True,
                    "require_admin": False,
                    "mode": "storage",
                }))
                msg = json.loads(await ws.recv())
                if not msg.get("success"):
                    print(f"Failed to create dashboard {url_path}: {msg}")
                    sys.exit(1)
                print(f"Created dashboard {url_path}")

        await ws.send(json.dumps({
            "id": 3,
            "type": "lovelace/config/save",
            "url_path": url_path,
            "config": config,
        }))
        msg = json.loads(await ws.recv())
        if msg.get("success"):
            print("Dashboard pushed successfully!")
        else:
            print(f"Failed: {msg}")
            sys.exit(1)


if __name__ == "__main__":
    default = Path(__file__).parent.parent / "config" / "dashboards" / "overview.yaml"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    url_path = sys.argv[2] if len(sys.argv) > 2 else None
    icon = sys.argv[3] if len(sys.argv) > 3 else "mdi:cellphone-screenshot"
    asyncio.run(push_dashboard(path, url_path, icon))
