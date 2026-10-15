# Home Assistant

Configuration, dashboards and docs for our Home Assistant, which runs as
**Home Assistant OS on a Raspberry Pi 3**:

- At home: `http://192.168.68.68:8123`
- Away: `https://home.dx2-66.com` (Cloudflare Tunnel behind Cloudflare Access;
  see [docs/remote-access.md](docs/remote-access.md))

This repo isn't the live configuration. Most of HA's state (integrations,
helpers, `.storage/`) lives on the Pi. Files here are pushed or copied to it.
[CLAUDE.md](CLAUDE.md) explains how each piece gets there.

## What's here

| Path | What |
|---|---|
| `config/dashboards/wall_phone.yaml` | Dashboard for the wall-mounted Galaxy Note 9: clock, wind/weather chart, power, heat pumps, lights. See [docs/wall-phone.md](docs/wall-phone.md) |
| `config/packages/wall_phone.yaml` | Its helpers: hourly forecast sensor, ceiling-light Off/Night/Full control, heat-pump energy today |
| `scripts/push_dashboard.py` | Pushes a dashboard YAML to HA over the WebSocket API |
| `rpi/` | Builds a verified HAOS image for a Raspberry Pi ([rpi/README.md](rpi/README.md)) |
| `docs/` | Wall phone and remote access guides |
| `vm/`, `docker-compose.yml`, `config/configuration.yaml`, `config/dashboards/smart_home.yaml` | **Legacy** from the earlier Hyper-V VM and Docker setups. The VM is kept, shut down, as a fallback. Not used by the Pi |

## Pushing a dashboard

```bash
HASS_TOKEN=<token> uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```

Always give the dashboard's URL path (`wall-phone`). Without it, the script
overwrites the main Overview dashboard.

## Claude Code MCP

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Fill in `HASS_HOST` (`http://192.168.68.68:8123`) and a long-lived access token
(HA profile → Security → Long-lived access tokens), then restart Claude Code.
The file is gitignored.
