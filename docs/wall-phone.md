# Wall phone (Galaxy Note 9)

An old Galaxy Note 9 on the wall, permanently on the charger, showing the
**Wall Phone** dashboard (`config/dashboards/wall_phone.yaml`): clock and weather,
live solar / load / battery / grid with a power-flow chart, and tap-to-toggle
tiles for lights and heat pumps. Power figures are read-only.

Push changes to the dashboard with:

```bash
uv run --with pyyaml --with websockets scripts/push_dashboard.py config/dashboards/wall_phone.yaml wall-phone
```

(`HASS_TOKEN` must be set. Always pass `wall-phone`: without it the script
overwrites the main Overview dashboard.)

The wind strip reads `sensor.hourly_forecast`, defined in
[`config/packages/wall_phone.yaml`](../config/packages/wall_phone.yaml). On the
Pi it lives in `/config/packages/`, loaded by `homeassistant: packages:
!include_dir_named packages` in `configuration.yaml`, and the recorder excludes
it. After editing it, copy it to the Pi and reload template entities.

## 1. Home Assistant

1. Reserve **192.168.68.68** for the Pi in the router (Deco app → Advanced →
   Address reservation), so the phone's URL never breaks.
2. Settings → People → **Add person** "Wall Phone", allow login, **not**
   administrator, tick *Can only log in from the local network*.
3. Log in as that user once (step 2.4), then in its profile set
   *Always hide the sidebar* and *Dashboard* → **Wall Phone**.

## 2. Phone

Free setup: Fully Kiosk without a licence, locked in with Android's own app
pinning. Turning on any PLUS feature (Kiosk Mode, screensaver or brightness
schedules, Remote Administration) adds a "Get a License" banner.

1. Install **Fully Kiosk Browser** from the Play Store *before* removing the
   Google account (the Play Store needs it).
2. Remove accounts: Settings → Accounts and backup → Accounts → Google /
   Samsung account → Remove account. Remove them before any factory reset, or
   the reset asks for the old Google login.
3. Fully Kiosk → Settings (everything else off):
   - Web Content → *Start URL*: `http://192.168.68.68:8123/wall-phone/home`
     (`http://` and `:8123` are required; anything else is "connection refused")
   - Device Management → *Keep screen on*, *Launch on boot*
   - Web Auto Reload → *Auto reload on network reconnect*
4. Open the start URL, log in as **Wall Phone**, tick *Keep me logged in*.
5. Pin it: Settings → Biometrics and security → Other security settings →
   **Pin windows** on, with *Ask for PIN before unpinning*; then Recent apps →
   Fully's icon → **Pin this app**. Unpin with Back + Recents held together.
   Pinning does not survive a reboot; re-pin after a power cut.
6. Night: Settings → Display → **Dark mode** → scheduled sunset to sunrise
   (set the Wall Phone user's HA theme to *Auto* so the dashboard follows), and
   *Adaptive brightness* on.

Stuck in Fully's settings-less screen: swipe in from the left edge for its menu.

### Battery

A phone that never unplugs will eventually swell its battery. The Note 9's last
update (One UI 2.5) probably lacks Samsung's *Protect battery* 85% cap: look
under Settings → Device care → Battery → ⋮ → Settings. If it's not there,
charge it from a smart plug that HA switches on a schedule (e.g. a few hours on,
a few off) rather than leaving it on 100% all day. Use a 2 A+ charger.

## 3. Devices still to add to HA

The dashboard shows only what HA can control. As of 2026-10-15:

| Device | Status | How to add |
|---|---|---|
| TP-Link/Tapo plugs | In HA | Lampe salon (on the wall phone). Computer, aquarium pump, aquarium light and TV are for consumption only: they're on the Energy dashboard, not the wall phone. |
| Mitsubishi heat pumps | In HA | **ECHONETLite** (HACS), fully local: Hall `192.168.68.63`, Living room `.84`, Dining room `.89`. Reserve these IPs in the router; the integration is configured by address. ECHONET Lite is enabled per unit in the Mitsubishi Electric NZ app. Living room and Dining room also report lifetime energy (0.1 kWh steps, no live watts; Hall reports neither): they're in the Energy dashboard, and daily `utility_meter` helpers (created in the UI) feed `sensor.heat_pumps_today`. |
| Xiaomi lights (Mi Home) | In HA | **Xiaomi Home** (Xiaomi's official integration, HACS) on the **Singapore** server: Mi Home's New Zealand region lives there. Ceiling lights (group), both bedside lamps, fan, vacuum, night lights and Bluetooth sensors. An older China-server entry only holds stale copies. |
| Matter lights | Not in HA | Matter has no devices paired on this HA (only an old, stale Tapo plug). Add each light with the HA Companion app → Settings → Devices → *Add Matter device*, or share it from its current app with a pairing code. Wi-Fi Matter devices work as is; Thread ones need a border router. |

The wind chart uses the **ApexCharts card** (HACS, frontend only).

Add each new light or `climate.*` entity as a tile under *Lights* or a new
*Heat pumps* section in `wall_phone.yaml` and push again.
