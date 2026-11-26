#!/usr/bin/env python3
"""Manage the Tuya Local entry for Jodie's heater from this PC.

Usage:
    uv run --with websockets --with "qrcode[pil]" scripts/tuya_local_entry.py rekey [--user-code CODE]
    uv run --with websockets scripts/tuya_local_entry.py disable
    uv run --with websockets scripts/tuya_local_entry.py enable

rekey   Fetches the heater's current local key from the Tuya cloud through
        Tuya Local's own config flow (cloud mode) and saves it on the
        existing entry through its options flow, so entity IDs stay the same.
        If Tuya Local's cloud login has expired it needs the Smart Life user
        code (Smart Life: Me > Settings > Account and Security > User Code),
        writes a QR code to tuya_login_qr.png and waits while you scan it
        with Smart Life's scanner. The key is never printed. The options flow
        tests the connection before saving, so a wrong key saves nothing.
        Afterwards it disables and re-enables the entry: changing options sets
        off a reload loop in Tuya Local (see docs/jodie-heater.md).
disable / enable
        Takes the entry offline or back, e.g. so scripts/tuya_probe.py can
        talk to the heater (it accepts one connection at a time).

HASS_TOKEN comes from the environment, or else from .claude/settings.local.json.
HASS_HOST defaults to http://192.168.168.68:8123.
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

import websockets

HOST = os.environ.get("HASS_HOST", "http://192.168.168.68:8123")
TITLE = "Heater Jodie"
PROTOCOL = "3.3"  # not "auto": auto saves the protocol it finds and reloads again


def token():
    if os.environ.get("HASS_TOKEN"):
        return os.environ["HASS_TOKEN"]
    settings = Path(__file__).resolve().parent.parent / ".claude" / "settings.local.json"
    return json.loads(settings.read_text())["mcpServers"]["homeassistant"]["env"]["HASS_TOKEN"]


def call(path, body=None, method=None):
    req = urllib.request.Request(
        HOST + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def find_entry():
    entries = call("/api/config/config_entries/entry?domain=tuya_local")
    for e in entries:
        if e["title"] == TITLE:
            return e
    sys.exit(f"No tuya_local entry titled {TITLE!r}: {[e['title'] for e in entries]}")


async def set_disabled(entry_id, disabled):
    ws_url = HOST.replace("http", "ws", 1) + "/api/websocket"
    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token()}))
        await ws.recv()
        await ws.send(json.dumps({
            "id": 1,
            "type": "config_entries/disable",
            "entry_id": entry_id,
            "disabled_by": "user" if disabled else None,
        }))
        result = json.loads(await ws.recv())
        if not result.get("success"):
            sys.exit(f"config_entries/disable failed: {result}")
    print("disabled" if disabled else "enabled")


def field_default(flow, name):
    for f in flow.get("data_schema") or []:
        if f.get("name") == name:
            return f.get("default")
    return None


def rekey(user_code):
    entry = find_entry()
    flows = "/api/config/config_entries/flow"
    flow = call(flows, {"handler": "tuya_local", "show_advanced_options": False})
    fid = flow["flow_id"]
    try:
        flow = call(f"{flows}/{fid}", {"setup_mode": "cloud"})
        if flow.get("step_id") == "cloud":
            if not user_code:
                sys.exit("Tuya Local isn't logged in to the Tuya cloud any more: run again with --user-code "
                         "(Smart Life: Me > Settings > Account and Security > User Code).")
            flow = call(f"{flows}/{fid}", {"user_code": user_code})
        if flow.get("step_id") == "scan":
            import qrcode

            data = flow["data_schema"][0]["selector"]["qr_code"]["data"]
            qrcode.make(data, error_correction=qrcode.constants.ERROR_CORRECT_Q).save("tuya_login_qr.png")
            print("Scan tuya_login_qr.png with Smart Life's scanner, confirm the login,")
            input("then press Enter here (the QR expires after a few minutes)... ")
            flow = call(f"{flows}/{fid}", {})
            Path("tuya_login_qr.png").unlink(missing_ok=True)
        if flow.get("step_id") != "choose_device":
            sys.exit(f"Unexpected step {flow.get('step_id')}: {flow.get('errors')}")

        options = flow["data_schema"][0]["selector"]["select"]["options"]
        print("Devices on the account:", ", ".join(o["label"] for o in options))
        device = next((o["value"] for o in options if o["label"].startswith("Chambre Jodie")), None)
        if device is None:
            sys.exit("The heater isn't on this Smart Life account.")
        flow = call(f"{flows}/{fid}", {"device_id": device, "hub_id": "None"})
        print("Looking for it on the LAN (about 20 s)...")
        flow = call(f"{flows}/{fid}", {})  # search step
        key = field_default(flow, "local_key")
        host = field_default(flow, "host") or "192.168.168.54"
        if not key:
            sys.exit(f"No key in step {flow.get('step_id')}")
        print(f"Got a {len(key)}-character key; heater found at {host}.")
    finally:
        try:
            call(f"{flows}/{fid}", method="DELETE")
        except Exception:
            pass

    opts = "/api/config/config_entries/options/flow"
    flow = call(opts, {"handler": entry["entry_id"]})
    flow = call(f"{opts}/{flow['flow_id']}", {
        "local_key": key, "host": host, "protocol_version": PROTOCOL, "poll_only": False,
    })
    if flow.get("type") != "create_entry":
        call(f"{opts}/{flow['flow_id']}", method="DELETE")
        sys.exit(f"Tuya Local couldn't connect with that key ({flow.get('errors')}); nothing saved.")
    print("Key saved on the entry.")
    asyncio.run(set_disabled(entry["entry_id"], True))
    asyncio.run(asyncio.sleep(5))
    asyncio.run(set_disabled(entry["entry_id"], False))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["rekey", "disable", "enable"])
    p.add_argument("--user-code", help="Smart Life user code, only needed when the cloud login expired")
    a = p.parse_args()
    if a.action == "rekey":
        rekey(a.user_code)
    else:
        asyncio.run(set_disabled(find_entry()["entry_id"], a.action == "disable"))


if __name__ == "__main__":
    main()
