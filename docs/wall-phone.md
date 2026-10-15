# Wall phone (Galaxy S20)

An old Galaxy S20 on the wall, permanently on the charger, showing the
**Wall Phone** dashboard (`config/dashboards/wall_phone.yaml`): clock and weather,
live solar / load / battery / grid with a power-flow chart, and tap-to-toggle
tiles for lights and heat pumps. Power figures are read-only.

Push changes to the dashboard with:

```bash
uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```

(`HASS_TOKEN` must be set. Always pass `wall-phone`: without it the script
overwrites the main Overview dashboard.)

## 1. Home Assistant

1. Reserve **192.168.68.68** for the Pi in the router (Deco app → Advanced →
   Address reservation), so the phone's URL never breaks.
2. Settings → People → **Add person** "Wall Phone", allow login, **not**
   administrator, tick *Can only log in from the local network*.
3. Log in as that user once (step 2.4), then in its profile set
   *Always hide the sidebar* and *Dashboard* → **Wall Phone**.

## 2. Phone

1. Factory reset (optional but cleaner), skip the Google/Samsung account, join
   the home Wi-Fi.
2. **Battery protection** (important on a phone that never unplugs; it stops
   the battery swelling): Settings → Battery and device care → Battery →
   More battery settings → **Protect battery** (caps charging at 85%).
3. Install **Fully Kiosk Browser** from the Play Store. The free version works;
   a PLUS licence (one-off, per device) removes the watermark and enables motion
   wake and the Home Assistant integration.
4. Fully Kiosk → Settings:
   - Web Content → *Start URL*: `http://192.168.68.68:8123/wall-phone/home`
   - Device Management → *Keep screen on*, *Launch on boot*
   - Web Auto Reload → *Auto reload on network reconnect*
   - Screen saver / Screen brightness → dim between 22:00 and 07:00
   - Kiosk Mode → *Enable* (set an exit PIN)
5. Open the start URL, log in as **Wall Phone**, tick *Keep me logged in*.
6. Optional (PLUS): Fully Kiosk → Remote Administration on, then add the
   **Fully Kiosk Browser** integration in HA to control the screen and
   brightness from automations (e.g. screen off when nobody's home).

Settings → Display → *Screen timeout* doesn't matter once Fully keeps the
screen on. Use the official 25 W charger or any 2 A+ USB-C supply.

## 3. Devices still to add to HA

The dashboard shows only what HA can control. As of 2026-10-15:

| Device | Status | How to add |
|---|---|---|
| TP-Link/Tapo plugs (Lampe salon) | In HA | Done |
| Mitsubishi heat pumps | Not in HA | In the **Mitsubishi Electric NZ** app, enable *ECHONET Lite* for each unit and reserve the units' IPs in the router, then install **ECHONETLite** (HACS) and add each unit by IP. Fully local, no cloud. |
| Xiaomi lights (Mi Home) | Not in HA | Install **Xiaomi Home** (Xiaomi's official integration, via HACS) and sign in with the Mi Home account. |
| Matter lights | Not in HA | Matter has no devices paired on this HA (only an old, stale Tapo plug). Add each light with the HA Companion app → Settings → Devices → *Add Matter device*, or share it from its current app with a pairing code. Wi-Fi Matter devices work as is; Thread ones need a border router. |

Add each new light or `climate.*` entity as a tile under *Lights* or a new
*Heat pumps* section in `wall_phone.yaml` and push again.
