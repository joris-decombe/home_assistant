# Home Assistant Smart Home Setup

Home Assistant OS running in a Hyper-V VM with Claude Code MCP integration.

## Quick Start

1. **Create the Hyper-V VM**
   ```powershell
   # Run as Administrator
   cd C:\Users\joris\code\home_assistant\vm
   .\setup-ha-vm.ps1
   ```

2. **Complete Setup**
   - Find the VM's IP: `Get-VM HomeAssistant | Get-VMNetworkAdapter | Select IPAddresses`
   - Open `http://<IP>:8123`
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
   Edit `.claude/settings.local.json` and fill in your HA IP and token.

5. **Restart Claude Code** to load the MCP server

## Architecture

Home Assistant OS runs in a Hyper-V Gen 2 VM with an External Virtual Switch,
giving it direct access to the LAN for device discovery (mDNS, SSDP, UPnP).

## Files

| File | Purpose |
|------|---------|
| `vm/setup-ha-vm.ps1` | Hyper-V VM setup script |
| `config/dashboards/smart_home.yaml` | Dashboard configuration |
| `.claude/settings.local.json` | MCP server config (not committed) |
| `rpi/` | Builds a Home Assistant OS image for a Raspberry Pi ([rpi/README.md](rpi/README.md)) |

## Dashboard

The Smart Home dashboard includes:
- **Home** - Weather, sun position, people tracking, shopping list
- **Media** - Sony TV, Sonos speakers (media controls)
- **Sonos** - Detailed Sonos EQ, surround, and speaker settings
- **Printer** - HP ENVY 5000 status and ink levels
- **System** - HA updates and backup status

## Adding Devices

Devices on the LAN are auto-discovered. To add manually:
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for your device brand
4. Follow the setup wizard

Edit `config/dashboards/smart_home.yaml` and push via the WebSocket API or
edit the dashboard directly in the HA UI.
