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
  copy them across.

## Pushing changes to the Pi

**Dashboards** (storage-mode Lovelace, pushed over the WebSocket API):
```bash
HASS_TOKEN=... uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```
Pass the dashboard's `url_path` (e.g. `wall-phone`). Without one it pushes to the
main **Overview** dashboard, which is only right for
`config/dashboards/overview.yaml`. It creates the dashboard if it doesn't exist.

**Packages** (`config/packages/*.yaml` → `/config/packages/` on the Pi, loaded by
`homeassistant: packages: !include_dir_named packages`): copy the file over host
SSH, run `sync`, validate, then reload (no restart needed for templates or scripts):
```bash
ssh -i ~/.ssh/ha-rpi -p 22222 root@192.168.68.68 'cat > /mnt/data/supervisor/homeassistant/packages/wall_phone.yaml && sync' < config/packages/wall_phone.yaml
# then POST /api/config/core/check_config, and /api/services/template/reload (and script/reload)
```
On the HAOS host, `/config` is `/mnt/data/supervisor/homeassistant`.

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

1 GB RAM. It runs from an SD card (the Intel SSD isn't connected yet), and swap
already sits around 300–550 MB. Keep add-ons and integrations lean: Matter Server
is stopped on purpose (no devices), and the recorder uses `commit_interval: 30`,
`purge_keep_days: 7`. **Run `sync` after writing files**: a power cut once
truncated a freshly installed HACS integration to empty files. The `rpi_power`
"under-voltage" repair is a sticky since-boot flag. One event at power-on is
normal; repeated events while running mean a power problem.

## Backups

Automatic backups: daily at 03:30, keeping 7, encrypted, stored on
`hassio.local` and `google_drive.jorisdecombe_gmail_com`. They're configured
over WebSocket (`backup/config/info`, `backup/config/update`). Google Drive is a
stopgap: the user wants a scoped **Backblaze B2** bucket long term. Never print
the encryption key; the owner downloads it from the UI.

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

The wind chart is `custom:apexcharts-card` (HACS). Its `EVAL:` label formatters
index `sensor.hourly_forecast` by point order. You can't log in to HA from the
browser tool, so test card changes in a local page: serve the card JS and a fake
`hass` object at 412 px. After installing a HACS card, the phone needs a reload.

## Devices and integrations worth knowing

- **Mitsubishi heat pumps:** ECHONETLite (HACS), local. Hall `.63`, Living room
  `.84`, Dining room `.89`. Living room and Dining room report lifetime kWh only
  (no live watts); Hall reports none. Approximate power comes from `derivative`
  helpers, and daily kWh from `utility_meter` helpers, all created in the UI.
- **Xiaomi Home** (official, HACS) on the **Singapore** server: Mi Home's New
  Zealand region lives there. The China server only held stale devices.
- **Alpha ESS** (solar and battery, in the basement), **Evnex** EV charger, and
  TP-Link/Tapo plugs. The Energy dashboard's devices and their live `stat_rate`
  power sensors feed the `power-sankey` cards.
- The user wants Alpha ESS controls **read-only** on dashboards (no
  tap-to-control on its switches or numbers).
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
