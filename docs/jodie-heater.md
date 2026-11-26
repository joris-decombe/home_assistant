# Jodie's heater

A **Goldair Platinum GPPH710** (1000 W electronic inverter panel heater with
Wi-Fi) in Jodie's room. Inside it are two chips: the heater's own controller
(buttons, display, thermostat) and a Tuya Wi-Fi module that talks to the
network. Home Assistant controls it locally, with no cloud, through
**Tuya Local** (`make-all/tuya-local`, HACS custom repository).

| What | Value |
|---|---|
| HA entity | `climate.heater_jodie` (plus `light.heater_jodie_display`, `lock.heater_jodie_child_lock`, `time.heater_jodie_timer`, `sensor.heater_jodie_power_level`, `binary_sensor.heater_jodie_problem`) |
| Tuya Local entry | "Heater Jodie", device config `goldair_gpph_heater.yaml` |
| Address | `192.168.168.54`, TCP 6668, protocol **3.3** (MAC `50:02:91:65:32:2d`) |
| Device ID | `2245045250029165322d` |
| Cloud account | Smart Life, device "Chambre Jodie (GPPH SERIES)" |
| Automations | `config/packages/jodie_heater.yaml`: off from 07:00 (retrying until 07:30, then a notification), display off at 20:30, watchdog reload after 15 min unavailable |
| Manual | [Goldair Electronic Inverter Panel Heater with WiFi (Mitre 10 NZ)](https://ccapi.mitre10.co.nz/medias/sys_master/root/hb1/hea/9155343876126/297127_ItemAssem/297127-ItemAssem.pdf) |
| Warranty | 3 years, Goldair NZ 0800 232 633 |

Smart Life is only needed to pair the heater and fetch its key. Day to day,
HA talks to it directly, so the app can be uninstalled. Never **remove** the
heater in the app: that resets it and changes its key.

## Symptoms and causes

| What you see | Most likely cause | Fix |
|---|---|---|
| Entity unavailable, entry `setup_retry` "tuya-local device offline", log error **901** "Unable to Connect" | Heater unplugged, off at the wall, or off the Wi-Fi | `tuya_probe.py scan`; check the heater has power |
| Entry offline, log error **904** "Unexpected Payload", heater pings fine | **Local key changed** (it was re-paired or reset) | [Re-key](#re-key-after-a-re-pair) |
| Entities stay **unknown**, log error **900** "json obj data unvalid" | Key is right, but the Wi-Fi module has no state from the heater yet (seen after power-up and resets) | Press any button on the heater once |
| Heater "ignores" commands, target stuck at **5 °C** | Preset **away** (Goldair's anti-freeze, AF), which holds 5 °C; switching back to comfort keeps 5 °C as the target | Set comfort and a real target, on the heater or in HA |
| Commands acknowledged but nothing happens, same state reported (22 Nov 2026) | Not fully explained; a power cycle at the wall cleared it | Switch off at the wall for a few seconds |
| Entry loads and unloads every few seconds after changing its options | Tuya Local bug (see below) | `tuya_local_entry.py disable`, then `enable` |
| Smart Life can't control it either | Not a hardware fault by itself: the same three causes above apply to the app | As above |

An acknowledgement from the heater isn't proof that it acted: the Wi-Fi
module echoes commands. Check the heater's display.

## Tools

Both scripts are in `scripts/`. Neither prints the local key.

**`tuya_probe.py`** runs inside the HA container on the Pi and reads the
device ID, address and key from Tuya Local's entry:

```bash
ssh -i ~/.ssh/ha-rpi -p 22222 root@192.168.168.68 'docker exec -i homeassistant python3 - scan' < scripts/tuya_probe.py
```

- `scan`: what answers on port 6668 across the LAN, and the heater's UDP
  broadcast (version and device ID). It **stops broadcasting while HA holds
  a connection**, so "no broadcast" is normal when the entry is loaded.
- `history [DAYS]`: the heater's state changes from HA's database (read-only):
  target, room, preset, power level, and whether a user or an automation
  caused them. This settled the 5 °C question in a minute.
- `status`: one status query.
- `listen [SECS]`: holds a connection open and prints every change the
  heater reports while you press its buttons. Proves that the two chips talk.

`status` and `listen` compete with HA, because the heater accepts only one
connection at a time. Disable the entry first and enable it afterwards.

**`tuya_local_entry.py`** runs on this PC (token from `HASS_TOKEN` or
`.claude/settings.local.json`):

```bash
uv run --with websockets scripts/tuya_local_entry.py disable
uv run --with websockets scripts/tuya_local_entry.py enable
uv run --with websockets --with "qrcode[pil]" scripts/tuya_local_entry.py rekey [--user-code CODE]
```

## Re-key after a re-pair

Each pairing in Smart Life (including after a Wi-Fi reset) gives the heater
a new local key, while the device ID stays the same. To put the new key in
HA without recreating the entry (entity IDs and automations stay the same):

1. Run `tuya_local_entry.py rekey`. It starts a Tuya Local config flow in
   cloud mode, picks the heater from the account, reads the key from the
   flow's last form, aborts that flow and saves the key through the
   existing entry's options flow (protocol 3.3). The options flow tests the
   connection, so a bad key saves nothing.
2. If Tuya Local isn't logged in to the cloud any more, the script asks for
   `--user-code`: in Smart Life, **Me → ⚙ Settings → Account and Security →
   User Code**. It then writes `tuya_login_qr.png`: scan it with Smart
   Life's scanner, confirm the login, and press Enter. The login lasts a
   while (it was still valid a few hours later on 26 November) but not
   forever.
3. The script then disables and re-enables the entry to stop the reload
   loop that changing options causes.
4. If the entities stay unknown, press a button on the heater.

Pairing it again from scratch: hold the heater's **WiFi button for 5
seconds** until the Wi-Fi light flashes fast, then Smart Life → Add device,
on the 2.4 GHz network.

## Tuya Local quirks seen here

- **Reload loop.** `async_setup_entry` calls `entry.add_update_listener(...)`
  on every setup and never removes it. After an options change the entry
  reloaded every few seconds for minutes, with several connections at once
  hammering the heater (errors 901, entities flipping unavailable/unknown).
  Disabling and re-enabling the entry stopped it; an HA restart would too.
- **Error 900 counts as reachable.** For devices that never answer status
  queries, Tuya Local treats error 900 as "online, no data". So with an empty
  Wi-Fi module the entry loads fine and the entities stay unknown, with
  nothing in the log at the default level.
- **Protocol auto** cycles through versions and saves the one it finds,
  which is an options change: keep the entry pinned to **3.3**. The 3.22
  ("device22") variant times out on this heater.
- **Debug logging**: `logger.set_level` with
  `custom_components.tuya_local: debug` (and `tinytuya: debug` for the raw
  messages). It's very chatty on the Pi: set it back to `warning` after.

## Data points

From `goldair_gpph_heater.yaml`:

| dp | Meaning | Values |
|---|---|---|
| 1 | Power | `true` = heat, `false` = off |
| 2 | Target °C | 5–35 (comfort), 5–21 (eco), fixed 5 (anti-freeze) |
| 3 | Room °C | |
| 4 | Preset | `C` comfort, `ECO` eco, `AF` anti-freeze (HA: away) |
| 6 | Child lock | |
| 12 | Fault bits | 0 = no fault |
| 101 | Power level | `1`–`5`, `stop` |
| 102 | Timer | minutes |
| 104 | Display | |
| 105 | Power mode | `auto`, `user` (fixed level from dp 101), `stop` |
| 106 | Eco target °C | 5–21 |

## History

- **21–22 November 2026:** HA lost it for 11 hours ("Unable to Connect"
  every 10 minutes until a restart), which is why the watchdog exists. Then
  it acknowledged every command but acted on none, until it was switched
  off at the wall.
- **25 November, 07:46:** off the network (unplugged), around the internet
  outage.
- **26 November:** plugged back in, it looked dead, in HA and in Smart Life,
  even after several Wi-Fi resets and re-pairs. It wasn't broken:
  1. The re-pairs had changed its key (error 904). Fetched through Tuya
     Local's cloud flow and set on the entry.
  2. It came back in anti-freeze mode at manual power level 1, so 5 °C.
  3. Its Wi-Fi module had no state until a button was pressed (error 900).
  After a button press, a direct connection got its full state, it
  reported button changes live, and HA's 21 °C showed on its display.
  HA's history showed HA never set anti-freeze or 5 °C.
