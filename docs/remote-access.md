# Remote access: https://home.dx2-66.com

Home Assistant on the Pi is reachable over HTTPS through a **Cloudflare Tunnel**.
The tunnel is outbound only, so no router ports are open. Cloudflare terminates
TLS, and **Cloudflare Access** sits in front, so only allowed emails get to HA's
own login page. At home, `http://192.168.68.68:8123` keeps working unchanged
(used by the wall phone, the MCP server and the Xiaomi Home sign-in).

```
browser ──HTTPS──▶ Cloudflare (Access) ──tunnel──▶ Cloudflared add-on ──▶ HA :8123
```

## Pieces

| Where | What |
|---|---|
| HA add-on | **Cloudflared** (`9074a9fa_cloudflared`, repo `github.com/brenner-tobias/ha-addons`): `external_hostname: home.dx2-66.com`, `tunnel_name: homeassistant`. Locally managed tunnel: on first start it logs a Cloudflare login URL; approving it for the `dx2-66.com` zone creates the tunnel and the `home` DNS record. |
| HA HTTP settings | `use_x_forwarded_for: true`, `trusted_proxies: [172.30.33.0/24]` (the add-on network), `ip_ban_enabled: true`, `login_attempts_threshold: 5`. Since 2026, HA keeps these in `.storage/http` and **ignores an `http:` block in `configuration.yaml`** (it raises a repair issue). Change them through the `http/config/configure` websocket call, which stores them as *pending* and restarts. Then confirm with `http/config/promote` before `revert_at`, or HA reverts on its own. |
| Cloudflare Zero Trust | Access application **Home Assistant** for `home.dx2-66.com`, policy *Allow* for the owner's email, login by one-time PIN. |

## Notes

- Create or keep the Access application **before** the tunnel is up, so the
  hostname is never public without it.
- Turn on two-factor auth for the HA owner account (Profile → Security), since
  HA's login is the second gate.
- The HA Companion app can't pass Access's browser login. To use it remotely,
  add an Access policy that bypasses its paths, or use a service token.
- Failed logins through the tunnel ban the real client IP (via
  `X-Forwarded-For`). Bans are in `/config/ip_bans.yaml`.
- A "400: Bad Request" through the tunnel means HA isn't trusting the add-on
  as a proxy. HA's log says "not set-up for reverse proxies" or "untrusted
  proxy", followed by the address it saw.
- The add-on uses about 30–50 MB of RAM, which matters on the 1 GB Pi 3.
