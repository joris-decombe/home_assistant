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
| `config/dashboards/overview.yaml` | The main Overview dashboard: Home (wall-phone content plus rooms, vacuum, EV charger), Energy, Security, Plugs, Media, Sonos, Printer, System |
| `vm/`, `docker-compose.yml`, `config/configuration.yaml` | **Legacy** from the earlier Hyper-V VM and Docker setups. The VM is kept, shut down, as a fallback. Not used by the Pi |

## Pushing a dashboard

```bash
HASS_TOKEN=<token> uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```

Give the dashboard's URL path (`wall-phone`). Without one, the script pushes to
the main Overview dashboard, which is only right for
`config/dashboards/overview.yaml`.

## Claude Code MCP

Claude Code uses HA's built-in MCP server over HTTPS
(`https://home.dx2-66.com/api/mcp`), authenticated with an HA token and a
Cloudflare Access service token. Set up with `claude mcp add`, as shown in
[docs/remote-access.md](docs/remote-access.md#claude-code-mcp-over-https).

`.claude/settings.local.json` (gitignored, from the `.example`) still holds the
HA host and long-lived token used by the scripts here. Its old `npx` MCP entry
isn't used.

## Backups

Nightly at 03:30, keeping 7. Backups are encrypted and stored both on the Pi and
in the Cloudflare R2 bucket `ha-backups`, through HA's built-in Cloudflare R2
integration. Its API token is scoped to that bucket with Object Read & Write
only. A backup is about 60 MB, so 7 copies fit well inside R2's 10 GB free tier.
(HA's AWS S3 integration only works with Amazon, so R2 needs its own
integration.) **Keep the encryption key** (Settings → System → Backups → Configure → Encryption key →
download the emergency kit), because a backup can't be restored without it.
