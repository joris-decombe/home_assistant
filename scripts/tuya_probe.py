"""Talk to Jodie's heater directly, from inside the Home Assistant container.

Run it on the Pi through host SSH (it reads the device ID, host and local key
from Tuya Local's config entry, so no secret travels on the command line):

    ssh -i ~/.ssh/ha-rpi -p 22222 root@192.168.168.68 'docker exec -i homeassistant python3 - status' < scripts/tuya_probe.py

Commands:
    status          One status query, protocol 3.3.
    listen [SECS]   Keeps a connection open (default 240 s) and prints every
                    change the heater reports: press its buttons meanwhile.
    scan            Is it on the network? Ping-free: looks for anything
                    answering Tuya's port 6668 on 192.168.168.0/24 and for the
                    heater's UDP broadcast (version, same device ID).
    history [DAYS]  The heater's state changes from HA's database (default 7
                    days, read-only): on/off, target, room, preset, power level,
                    and whether a user or an automation caused them.

status and listen compete with HA's own connection (the heater takes one at a
time): disable the entry first (scripts/tuya_local_entry.py disable) and
enable it again afterwards. scan and history don't need that.

Reading the answers (see docs/jodie-heater.md):
    dps 1 power, 2 target °C, 3 room °C, 4 preset (C comfort, ECO, AF
    anti-freeze = 5 °C), 6 child lock, 12 fault bits, 101 power level
    (1-5/stop), 102 timer, 104 display, 105 auto/user power, 106 eco target.
    Err 900 "json obj data unvalid": key right, but the Wi-Fi module has no
    state yet (press a button on the heater).
    Err 904 / retcode 1 with an undecryptable payload: wrong local key.
    Err 901: nothing listening, or HA holds the connection.
"""

import concurrent.futures
import datetime
import json
import socket
import sqlite3
import sys
import time

import tinytuya

TITLE = "Heater Jodie"


def entry():
    with open("/config/.storage/core.config_entries") as f:
        entries = json.load(f)["data"]["entries"]
    e = next(x for x in entries if x["domain"] == "tuya_local" and x["title"] == TITLE)
    return {**e["data"], **e["options"]}


def device(c, persistent=False):
    d = tinytuya.Device(c["device_id"], c["host"], c["local_key"], version=3.3)
    d.set_socketTimeout(6)
    d.set_socketPersistent(persistent)
    return d


def status():
    c = entry()
    print(json.dumps(device(c).status()))


def listen(seconds=240):
    c = entry()
    d = device(c, persistent=True)
    print(time.strftime("%H:%M:%S"), "status", json.dumps(d.status()), flush=True)
    end, beat = time.time() + seconds, 0
    while time.time() < end:
        if time.time() - beat > 10:
            d.heartbeat(nowait=True)
            beat = time.time()
        r = d.receive()
        if r and not (isinstance(r, dict) and r.get("Err") == "902"):
            print(time.strftime("%H:%M:%S"), json.dumps(r), flush=True)
    print("done")


def scan():
    c = entry()

    def probe(i):
        s = socket.socket()
        s.settimeout(1.5)
        try:
            s.connect((f"192.168.168.{i}", 6668))
            return i
        except OSError:
            return None
        finally:
            s.close()

    with concurrent.futures.ThreadPoolExecutor(64) as ex:
        found = [i for i in ex.map(probe, range(1, 255)) if i]
    print("answering on 6668:", [f"192.168.168.{i}" for i in found], "(entry host", c["host"] + ")")

    socks = []
    for port in (6666, 6667):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        s.bind(("", port))
        s.settimeout(0.5)
        socks.append(s)
    end = time.time() + 20
    while time.time() < end:
        for s in socks:
            try:
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                msg = json.loads(tinytuya.decrypt_udp(data))
            except Exception:
                continue
            if msg.get("gwId") == c["device_id"]:
                print("broadcast from", addr[0], "version", msg.get("version"), "same device ID")
                return
    print("no broadcast from the heater in 20 s")


def history(days=7):
    db = sqlite3.connect("file:/config/home-assistant_v2.db?mode=ro", uri=True, timeout=30)
    since = time.time() - days * 86400
    rows = db.execute(
        """select s.last_updated_ts, s.state, a.shared_attrs,
                  s.context_user_id_bin is not null, s.context_parent_id_bin is not null
           from states s join states_meta m on s.metadata_id = m.metadata_id
           left join state_attributes a on s.attributes_id = a.attributes_id
           where m.entity_id = 'climate.heater_jodie' and s.last_updated_ts > ?
           order by s.last_updated_ts""",
        (since,),
    )
    nz = datetime.datetime.now().astimezone().tzinfo
    prev, gaps = None, 0
    for ts, state, attrs, by_user, by_automation in rows:
        if state in ("unavailable", "unknown"):
            gaps += 1
            continue
        a = json.loads(attrs or "{}")
        key = (state, a.get("temperature"), a.get("preset_mode"), a.get("swing_mode"))
        if key == prev:
            continue
        prev = key
        when = datetime.datetime.fromtimestamp(ts, nz).strftime("%d/%m %H:%M")
        cause = "user" if by_user else "automation" if by_automation else ""
        print(when, state, "target", a.get("temperature"), "room", a.get("current_temperature"),
              a.get("preset_mode"), "power", a.get("swing_mode"), cause)
    print(f"({gaps} unavailable/unknown rows left out)")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["status"]
    {"status": status, "listen": listen, "scan": scan, "history": history}[cmd](*map(int, args))
