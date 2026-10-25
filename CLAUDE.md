# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is (and isn't)

Configuration, scripts and docs for a Home Assistant install. **The repo is not
the live config.** Home Assistant OS runs on a **Raspberry Pi 3** at
`192.168.68.68` (port 8123, DHCP-reserved). Changes reach it only by being pushed
or copied (see below). Most of HA's state lives on the Pi and is managed through
the UI or API, not in this repo: `.storage/`, integrations and UI helpers.

- `vm/` is from the earlier Hyper-V VM setup. The VM `HomeAssistant` is kept,
  shut down, as a fallback (`AutomaticStartAction` = Nothing).
- `config/configuration.yaml` and `docker-compose.yml` are leftovers from a
  scratch Docker container (port 8124). The Pi's real `configuration.yaml`
  differs: it loads `packages/` and has the recorder tuning. Edit it on the Pi.
- `config/dashboards/overview.yaml` is the source of truth for the main
  Overview dashboard (pushed with no `url_path`). Its Home headline and wind
  chart are copies of the wall phone's: change `wall_phone.yaml` first, then
  copy them across. `config/dashboards/ipad.yaml` (`ipad-home`, the kitchen
  iPad) has its own design (see `docs/ipad.md`), but its 12 h wind chart and
  its Solar charging, Quakes, Cameras and Kids views are copies of the wall
  phone's too.

## Pushing changes to the Pi

**Dashboards** (storage-mode Lovelace, pushed over the WebSocket API):
```bash
HASS_TOKEN=... uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```
Pass the dashboard's `url_path` (e.g. `wall-phone`). Without one it pushes to the
main **Overview** dashboard, which is only right for
`config/dashboards/overview.yaml`. It creates the dashboard if it doesn't exist
(an optional third argument sets its sidebar icon, e.g. `mdi:tablet`).

**Packages** (`config/packages/*.yaml` → `/config/packages/` on the Pi, loaded by
`homeassistant: packages: !include_dir_named packages`): copy the file over host
SSH, run `sync`, validate, then reload (no restart needed for templates or scripts):
```bash
ssh -i ~/.ssh/ha-rpi -p 22222 root@192.168.68.68 'cat > /mnt/data/supervisor/homeassistant/packages/wall_phone.yaml && sync' < config/packages/wall_phone.yaml
# then POST /api/config/core/check_config, and /api/services/template/reload (and script/reload)
```
On the HAOS host, `/config` is `/mnt/data/supervisor/homeassistant`.

**Custom integrations** (`config/custom_components/<name>/` →
`/config/custom_components/`): tar them over the same SSH, `sync`, then restart
HA. A config entry reload doesn't re-import changed Python modules.

**HTTP settings** (proxy, IP bans) are **not** read from YAML on this HA version:
they live in `.storage/http`. Change them with the WebSocket call
`http/config/configure` (stores them as *pending* and restarts HA), then
`http/config/promote` before `revert_at`, or HA reverts them. See
`docs/remote-access.md`.

## Talking to HA

- The long-lived token and host are in `.claude/settings.local.json` (gitignored).
  Read the token from there and never print it. That file's `npx` MCP entry is
  unused: the `homeassistant` MCP server is HA's built-in one over HTTPS
  (`claude mcp add`, local scope), behind a Cloudflare Access service token. See
  `docs/remote-access.md`.
- Use the WebSocket API (`/api/websocket`) for registries, config entries, energy
  prefs, HACS (`hacs/repository/download`) and Lovelace. Supervisor endpoints
  (add-ons, backups, `/core/restart`) go through WebSocket `supervisor/api`.
  REST `/api/hassio/*` returns 401 with this token.
- `POST /api/template` is the quickest way to check dashboard Jinja.
- Restarts take 3–5 minutes on the Pi 3. Poll `/api/config` until `state` is `RUNNING`.

## Pi 3 constraints

1 GB RAM. It boots from the SD card, but since 2026-10-16 the data partition
(`/mnt/data`: HA config, add-ons, database and the 1 GB swapfile) lives on a 480 GB
SSD (HPE VK0480GD) in a self-powered VIA USB-SATA enclosure, moved with
Supervisor's `os/datadisk/move`. The SD card's old copy is left as
`hassos-data-old`. Swap sits around 300–550 MB. If the enclosure's power comes
on after the Pi boots, the adapter shows a 0-byte "VirtualDisk" and HA won't
start; replug it with the enclosure powered. Keep add-ons and integrations lean: Matter Server
was removed (no devices), and the recorder uses `commit_interval: 30`,
`purge_keep_days: 7`. **Run `sync` after writing files**: a power cut once
truncated a freshly installed HACS integration to empty files. The `rpi_power`
"under-voltage" repair is a sticky since-boot flag. One event at power-on is
normal; repeated events while running mean a power problem.

## Security

`docs/security.md` lists what is exposed and how. IPv6 is disabled on the Pi
on purpose (HA had a public address with no host firewall), the `wallphone`
user is local-only, and only Cloudflared auto-updates. Leave these alone
unless that doc says otherwise.

## Backups

Automatic backups: daily at 03:30, keeping 7, encrypted, stored on
`hassio.local` and Cloudflare R2 (bucket `ha-backups`, agent
`cloudflare_r2.01M51F575WQ0ZWVYBWK4NWSR5V`, bucket-scoped token). They're
configured over WebSocket (`backup/config/info`, `backup/config/update`);
`backup/info` shows which agents hold each backup. Google Drive was removed
(integration and OAuth client) in October 2026. Folders included: `share` and
`ssl` only; `/media` is left out on purpose (camera clips). Never print
the encryption key (`backup/config/info` returns it, so filter that call's
output); the owner downloads it from the UI.

## Wall-phone dashboard

`config/dashboards/wall_phone.yaml` (pushed to `wall-phone`) is for a Galaxy
Note 9 in free Fully Kiosk: about a 412×846 CSS viewport, a **non-admin** user
(error cards show no details), and no license (PLUS features add a watermark).
`config/packages/wall_phone.yaml` holds its helpers:
- `sensor.hourly_forecast`: 24 h of met.no hourly forecast via
  `weather.get_forecasts`. Excluded from the recorder.
- `select.ceiling_lights` and its scripts: Off / Night / Full for both Yeelight
  ceiling lights.
- `sensor.heat_pumps_today`.
- `sensor.home_battery`: the Alpha ESS charge level, with a templated name
  ("Charging 1.9 kW", "Discharging 640 W", "Battery idle") and icon, so the
  Battery sensor card on both Home views shows the rate too.
- `sensor.car_charger`: the Evnex charger's state in words ("Charging 7.2 kW",
  "Paused by car", "Waiting to charge", "Unplugged"), for the Car section.
  The Car section's *Charge now* switch is the one charger control on it.

Its **Kids** view has Jodie's Yoto player, one-tap story, podcast and radio
tiles (`media_player.play_media` with `yoto://card/<id>`, IDs from the
player's media browser), and dropdowns for multi-card Yoto Club series
(BrainBots, Dinosaurs…): template selects in `config/packages/yoto.yaml`
whose state stays unknown, so picking a card always plays it. Its **Music** view plays Spotify on the Sonos speakers (TV
Room Beam = living room, Dining Room, Hallway). `config/packages/music.yaml`
holds one `input_boolean.music_*` per room. Its automation groups the chosen
speakers (debounced 1 s), and `sensor.music_speaker` names the group's
coordinator, which picks the player card that shows. Spotify music is chosen
from the player's media browser (Sonos → pimooss), or from three **mood**
tiles that change with the time of day (`sensor.music_moods`: morning Jazz ·
Piano · Kids, daytime Focus · Upbeat · Acoustic, evening Dinner · Jazz · Kids,
night Wind down · Piano · Synthwave). Each mood is a pool of playlists in that
sensor's `catalogue` attribute, rotated by `input_text.music_rotation` and
played shuffled by `script.music_play_mood` (through
`script.music_play_playlist`: Spotify URIs that Sonos plays itself) in the
rooms switched on, else the dining room; `sensor.music_mood_1..3` show the
playlist each plays next. `number.music_volume` is one volume for the group
playing (the speakers' average; setting it moves each by the same amount).
The switches don't follow grouping done in the Sonos app or in HA's own
group dialog.

The wind chart is `custom:apexcharts-card` (HACS). Its `EVAL:` label formatters
index `sensor.hourly_forecast` by point order. You can't log in to HA from the
browser tool, so test card changes in a local page: serve the card JS and a fake
`hass` object at 412 px. After installing a HACS card, the phone needs a reload.

## Kitchen iPad

An iPad 9th gen (1080×810 CSS in landscape) in the companion app's kiosk
mode, as the local-only, non-admin `ipad` user, on `ipad-home`. Its theme is
**South Coast** (`config/themes/south_coast.yaml`, with SVG pictures in
`config/www/ipad/` from `scripts/coast_svg.py`); the theme's 16 px column gaps
are what make three columns fit. `config/packages/ipad.yaml` drives brightness
and the screensaver by phase of day through `notify.mobile_app_ipad`
(`kiosk_*` messages, which only reach the app in the foreground), and will
charge it from `switch.ipad_charger` between 30 and 80% once that plug
exists. Details and the iPad's own settings: `docs/ipad.md`.

## Devices and integrations worth knowing

- **Mitsubishi heat pumps:** ECHONETLite (HACS), local. Hall `.63`, Living room
  `.84`, Dining room `.89`. Living room and Dining room report lifetime kWh only
  (no live watts); Hall reports none. Approximate power comes from `derivative`
  helpers, and daily kWh from `utility_meter` helpers, all created in the UI.
- **Jodie's heater:** a Goldair GPPH panel heater, `climate.heater_jodie`, on
  **Tuya Local** (`make-all/tuya-local`, a HACS custom repository), local at
  `.54` (protocol 3.3). It's paired in Smart Life, whose QR sign-in fetched
  its local key; re-pairing changes the key. It reports no power or energy.
  `config/packages/jodie_heater.yaml` turns it off at 07:00 and, if it's on,
  its display off at 20:30. It sits with the
  heat pumps on all three dashboards.
- **Earthquakes:** GeoNet NZ Quakes (core, set up in the UI: 300 km, MMI 3+,
  the last 7 days) makes one `geo_location` entity per quake, for the
  **Quakes** tab on all three dashboards. `config/packages/earthquakes.yaml`
  polls GeoNet's measured intensity every minute: `sensor.wellington_shaking`
  is the second-highest MMI among the ~36 strong-motion sensors within 15 km
  in the last hour, and `binary_sensor.wellington_earthquake` (MMI 3+) shows
  an alert card at the top of each Home view.
- **Xiaomi Home** (official, HACS) on the **Singapore** server: Mi Home's New
  Zealand region lives there. The China server only held stale devices.
- **Alpha ESS** (solar and battery, in the basement), **Evnex** EV charger, and
  TP-Link/Tapo plugs. The Energy dashboard's devices and their live `stat_rate`
  power sensors feed the `power-sankey` cards.
  `config/packages/car_solar_charging.yaml` turns on the charger's *Charge
  now* when the battery is 98%+ and solar is still in surplus
  (`binary_sensor.solar_surplus`). It turns it back off at 1 kW of grid
  import, or when the battery reaches `sensor.car_charging_battery_floor`:
  how low it can go and still refill by sunset, from
  `sensor.solar_left_today` (a fitted sun curve × met.no's hourly
  conditions, no solar forecast integration). `input_boolean.car_solar_charging`
  marks a session it started, so it never stops a Charge now turned on by hand.
  All three dashboards have a **Solar charging** tab for it (wall phone
  first, then copied; the chart's dashed estimate repeats the package's solar
  curve in JS, so change both together).
- **Yoto** (core integration, cloud, found by DHCP): one player, "Jodie", in
  Jodie's room (`media_player.jodie`, battery, headphones, and day/night-mode
  volume, colour and brightness controls). **Spotify** (core, OAuth): the
  Premium account `pimooss` as `media_player.spotify_pimooss`. Added in
  October 2026.
- **Robot vacuum:** Roborock gen 1 (`rockrobo.vacuum.v1`) on Xiaomi Home,
  `vacuum.rockrobo_sg_64457686_v1`. Its MIoT spec has no fault code, only
  status "Error" (state `error`). `config/packages/vacuum.yaml` resumes it once
  per run after a mid-clean error (usually a false "main brush blocked") and
  notifies `mobile_app_plop` if it stops again.
- **Alpha ESS** (HACS v0.8.5, cloud) gets stuck if its API is down when HA
  starts: it loads with no inverters and never polls again.
  `config/packages/alpha_ess.yaml` reloads the entry when the battery charge
  sensor has been unavailable for 15 minutes (at most hourly). Upstream fixes
  this in 0.9.0; wait for the stable release, as the betas change how charge
  schedules are written.
- The user wants Alpha ESS controls **read-only** on dashboards (no
  tap-to-control on its switches or numbers).
- **Tapo cameras:** two C420 battery cameras behind H200 hubs (`.57` house,
  `.97` garage); no RTSP or ONVIF. Live view and controls come from **Tapo
  Control** (HACS). Events and clips come from **`tapo_events`**
  (`config/custom_components/`), which reuses Tapo Control's connections and
  copies detection clips to `/media/tapo`, keeping 7 days. The core TP-Link
  entries for the hubs are disabled on purpose (both on one hub caused
  errors). Never print or store the Tapo password outside HA. See
  `docs/tapo-cameras.md`.
- **Remote access:** `https://home.dx2-66.com` via the Cloudflared add-on, behind
  Cloudflare Access. See `docs/remote-access.md`. Local `http://192.168.68.68:8123`
  stays the address for the wall phone, MCP and the Xiaomi sign-in.

## Raspberry Pi image builder

`rpi/` builds a verified HAOS image with network and SSH settings preloaded
(details in `rpi/README.md`):
```bash
docker build -t haos-rpi-builder rpi
docker run --rm -v "${PWD}/rpi:/work" --env-file rpi/image.env haos-rpi-builder
```

There are no tests, linters or build steps for the rest of the repo.
