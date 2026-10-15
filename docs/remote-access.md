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
| Cloudflare Zero Trust | Access application **Home Assistant** for `home.dx2-66.com`. Policy action **Allow**: *Include* Emails = the owner's email, *Require* Country = New Zealand, no *Exclude* rules. Sign-in is the Cloudflare account (security key), which is this Zero Trust org's identity provider. The app also enforces its own **MFA: biometrics or security key, every 24 h**. |

## Notes

- Create or keep the Access application **before** the tunnel is up, so the
  hostname is never public without it.
- Keep the policy to Include + Require. An *Exclude* of "Everyone" or of the
  only login method blocks everyone, and a **Bypass** action skips sign-in
  altogether.
- Turn on two-factor auth for the HA owner account (Profile → Security), since
  HA's login is the second gate. The wall-phone user is local-network only.
- The HA Companion app can't pass Access's browser login. To use it remotely,
  add an Access policy that bypasses its paths, or use a service token.
- Failed logins through the tunnel ban the real client IP (via
  `X-Forwarded-For`). Bans are in `/config/ip_bans.yaml`.
- A "400: Bad Request" through the tunnel means HA isn't trusting the add-on
  as a proxy. HA's log says "not set-up for reverse proxies" or "untrusted
  proxy", followed by the address it saw.
- The add-on uses about 30–50 MB of RAM, which matters on the 1 GB Pi 3.

## Claude Code MCP over HTTPS

Claude Code talks to HA's built-in **Model Context Protocol Server** integration
(`mcp_server`, "All LLM APIs") at `https://home.dx2-66.com/api/mcp`. It only sees
entities exposed to Assist (Settings → Voice assistants → Expose).

- A second Access application, **Home Assistant MCP**, covers only
  `home.dx2-66.com/api/mcp`. Cloudflare uses the most specific path match, so it
  wins over the main app. Its only policy is **Service Auth** for the service
  token `claude-code`, with **no MFA** (a service token can't do MFA). On the
  main app, the app-wide MFA requirement made the token fail with a 403.
- Claude Code (local scope, stored in `~/.claude.json`, not in the repo):
  ```bash
  claude mcp add --transport http --scope local homeassistant https://home.dx2-66.com/api/mcp --header "Authorization: Bearer <HA token>" --header "CF-Access-Client-Id: <id>" --header "CF-Access-Client-Secret: <secret>"
  ```
- Troubleshooting: a 403 page from Cloudflare Access names the matched app's
  `App AUD`, which shows which app handled the request. Error 1033 means the
  tunnel or the Pi is down. Error 1010 means a client with no browser-like
  User-Agent was blocked.
