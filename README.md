# Home Assistant Smart Home Setup

A Docker-based Home Assistant setup with Claude Code MCP integration.

## Quick Start

1. **Start Home Assistant**
   ```bash
   docker compose up -d
   ```

2. **Complete Setup**
   - Open http://localhost:8124
   - Create your admin account
   - Complete the onboarding wizard

3. **Create Access Token**
   - Click your profile (bottom-left)
   - Scroll to "Long-Lived Access Tokens"
   - Create a token named "Claude MCP"

4. **Configure Claude Code MCP**
   ```bash
   cp .claude/settings.local.json.example .claude/settings.local.json
   ```
   Edit `.claude/settings.local.json` and replace `your_long_lived_access_token_here` with your token.

5. **Restart Claude Code** to load the MCP server

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Home Assistant container config |
| `config/configuration.yaml` | Main HA configuration |
| `config/dashboards/smart_home.yaml` | Custom dashboard |
| `.claude/settings.local.json` | MCP server config (not committed) |

## Dashboard

The Smart Home dashboard includes sections for:
- Home overview (weather, sun, people)
- Lights
- Climate control
- Security (cameras, sensors)
- Media players
- Smart switches
- Automations

Access it from the Home Assistant sidebar after setup.

## Adding Devices

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for your device brand (Hue, LIFX, Nest, etc.)
4. Follow the setup wizard

After adding devices, edit `config/dashboards/smart_home.yaml` to add them to your dashboard.
