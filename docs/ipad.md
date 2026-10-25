# Kitchen iPad

An iPad 9th generation (`iPad12,1`, 10.2" LCD, iPadOS 26) in landscape in the
kitchen, running the Home Assistant companion app in **kiosk mode** and
showing the **iPad** dashboard (`config/dashboards/ipad.yaml`, url path
`ipad-home`). It's logged in as the local-only, non-admin `ipad` user. Its
CSS viewport is 1080×810, which gives three columns.

## The dashboard

- **Home** fits on one screen: the clock (with the next sunset or sunrise)
  and who's home across the top, then weather with the 12 h wind chart and
  the week ahead, live energy, heating, the car, lights, music and the
  vacuum. The badges next to the people only appear when something needs a
  look: someone at the door or in the garage, Jodie's heater on, the vacuum
  stuck, low batteries, Pi under-voltage. Section headings open their detail
  tab.
- **Climate**: each heat pump's thermostat with modes and fan, Jodie's
  heater with presets, every room's temperature and humidity with a 24 h
  trend, the standing fan, heat-pump energy per day for two weeks, and two
  days of room temperatures.
- **Energy**: the live power flow, the battery, the Energy dashboard's own
  graphs (pick a day, week or month), and live and daily figures per device.
  Read-only.
- **Solar charging**, **Kids**, **Cameras** and **Quakes** are the wall
  phone's views in three columns; **Music** is the wall phone's, split into
  rooms, player and volumes.
- **System**: the iPad's battery, brightness and screen mode (with *Screen off
  now* and *Reload*), every battery-powered device lowest first, backups,
  the Pi's power, the inverter and printer ink.

Each tab opens with its title and one live line (on Home, the clock) over a
panorama of the south coast: Cook Strait and the Kaikōura ranges, the beach,
harakeke in flower and toetoe. Home is three column sections rather than one
section per topic, because sections side by side line up with the tallest
one, which made it scroll.

The theme is **South Coast**, `config/themes/south_coast.yaml`
(`/config/themes/` on the Pi, then `frontend.reload_themes`): sea teal and
sand with a pōhutukawa-red accent, by day and by night. Its pictures are
`config/www/ipad/coast-{day,night}.svg` (`/config/www/ipad/`, served at
`/local/ipad/`), drawn by `scripts/coast_svg.py`; bump the `?v=` in the theme
after redrawing them. Every view sets `theme: South Coast`, so it only applies
here. It also narrows the gaps between columns: with HA's default 32 px
gaps, three columns need 1088 px, so the old layout only ever showed two.

## Screen and battery

`config/packages/ipad.yaml` drives the screen through the app's remote
commands (`notify.mobile_app_ipad`, message `kiosk_*`):

| Phase (`sensor.ipad_kiosk_phase`) | When | Brightness | Screensaver |
|---|---|---|---|
| day | sun up | 60% | dim, 15% |
| evening | sunset to 22:30 | 35% | dim, 6% |
| night | 22:30 to 06:30 | 20% | blank |
| away | Joris and Pauline both out | 35% | blank, at once |
| quake | Wellington shaking (MMI 3+) | 100% | dismissed |

Brightness is only set while the screen is awake (set under the screensaver,
it lights the screen up behind it), so it's applied on waking. It also wakes
the screen when someone comes home (not at night), goes back to Home 30 s
after the screensaver starts, and reloads the page at 04:00.

An LCD doesn't burn in, so the point is the backlight and heat: a cooler iPad
on a charger ages its battery more slowly. The bigger problem is that the
9th gen has no 80% charge limit (only A16/M-series iPads do), so on a charger
it sits at 100% and the battery will eventually swell. The package charges
it from a smart plug between 30 and 80% once there is one: name the plug's
switch **`switch.ipad_charger`** and the automation starts working (it
charges if the battery stops reporting, so the iPad never runs flat). Until
then it does nothing.

## Setting up the iPad

1. Home Assistant app → Settings → Companion app → **Kiosk mode**:
   - Enabled, Dashboard **iPad** (so `kiosk_default` returns to it)
   - Keep screen on, Hide sidebar and top bar controls, Hide status bar
   - Auto reload: **Never** (the 04:00 reload covers it)
   - Accept kiosk remote commands: on
   - Screensaver: on, Mode **Dim** (the package switches it to Blank at
     night), Time to start **2 minutes**, **Wake on camera motion** on
2. Settings → Companion app → Sensors → **Camera Motion**: frame rate
   **2 fps** (default 8; plenty for someone walking up, at a quarter of the
   work), threshold 40%, clear delay 15 s.
3. iPad Settings → Display & Brightness → Appearance **Automatic** (the theme
   goes dark at sunset), **Auto-Brightness** off under Accessibility →
   Display & Text Size (HA sets it), True Tone on.
4. In HA on the iPad (turn kiosk mode off for a moment): Profile → Theme
   **South Coast**, dark mode Auto. The views set the theme themselves; this
   only colours the tab bar to match.
5. Settings → Battery: Low Power Mode stays off (it can pause the app's
   updates).
6. Guided Access (Accessibility) keeps the app in front: triple-click the
   Home button to start it.
