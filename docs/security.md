# Security hardening (Pi)

State of the Pi's attack surface after the October 2026 review, and what is
left to do by hand. HAOS is an appliance with a read-only root filesystem, so
OS hardening means keeping it current and turning off what isn't needed, not
editing the host.

## Exposure

| Path | Reachable from | Protection |
|---|---|---|
| `https://home.dx2-66.com` | Internet | Cloudflare Access (owner email, NZ only, MFA every 24 h), then HA login. See `remote-access.md`. |
| `home.dx2-66.com/api/mcp` | Internet | Access service token, then HA token. |
| HA `:8123` (HTTP) | LAN only | HA login, IP ban after 5 failures. |
| Host SSH `:22222` (dropbear) | LAN only | Key only (`-s`), one ed25519 key (`~/.ssh/ha-rpi`), no root password. |
| Observer `:4357`, rpcbind `:111` | LAN only | Built into HAOS. Can't be turned off. |
| go2rtc `:18555`, Sonos `:1400`, ECHONET `3610/udp`, SSDP, mDNS | LAN only | HA integrations. |

**IPv6 is disabled on the Pi** (`enu1u1`, method `disabled`). With it on, the
Pi had a public `2404:…` address and HA listened on `[::]:8123` with no host
firewall, so the only thing between HA and the internet was the router's IPv6
firewall. Thread or Matter devices need IPv6 back; check the router blocks
inbound IPv6 before re-enabling it. LLMNR is off on that interface too; mDNS
(`homeassistant.local`) stays on.

## Settings

- **Users:** the owner (`pimooss`) is the only admin. `wallphone` is a
  non-admin and **local-only**, so its login doesn't work through the tunnel.
- **Tokens:** two long-lived tokens, both the owner's: `claude`
  (`.claude/settings.local.json`) and `claude-code` (the MCP server in
  `~/.claude.json`). Review sessions under Profile → Security now and then.
- **HTTP** (`.storage/http`): `ip_ban_enabled`, `login_attempts_threshold: 5`,
  `use_x_frame_options`, `trusted_proxies` limited to the add-on network.
- **Add-ons:** Cloudflared (auto-update on, since it faces the internet) and
  Terminal & SSH (web terminal only: no keys or password, so port 22 isn't
  open). Matter Server and its integration were removed (no devices).
  The ESPHome, Music Assistant and Community add-on stores are built in to
  this Supervisor and can't be removed; nothing is installed from them.
- **Analytics:** all off.
- **Custom integrations** (HACS): `alphaess`, `echonetlite`, `evnex`,
  `xiaomi_home`, `hacs`. They run inside HA with full access, so keep the
  list short and read release notes before updating.

## Still to do by hand

1. **MFA for the owner:** Profile → Security → Multi-factor authentication
   modules → Authenticator app. HA's login is the second gate behind Access.
2. **Router UPnP:** turn it off in the Deco app (More → Advanced → UPnP) and
   check there are no port forwards. Then remove HA's `upnp` integration,
   which only reads router stats.
3. **Old VM:** the Hyper-V `HomeAssistant` VM holds a full copy of the config
   and credentials. Delete it once the Pi has proved itself.
