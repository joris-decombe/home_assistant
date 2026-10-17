# Tapo cameras

Two **Tapo C420** battery cameras, each paired to its own **H200** hub:

| Camera | Hub | Hub IP |
|---|---|---|
| Front Door | Tapo Hub Maison | 192.168.68.57 |
| Garage | Tapo Hub Garage | 192.168.68.97 |

The cameras never talk to the LAN directly: everything goes through the hub,
which keeps the recordings on its microSD card. The hubs expose only TCP 443
(control API) and 8800 (TP-Link's own media protocol). There is no RTSP or
ONVIF, so Frigate, go2rtc and the generic camera integrations can't use them.

Everything runs on the Pi, inside Home Assistant:

| What | How |
|---|---|
| Live video | **Tapo: Cameras Control** (HACS, `tapo_control`) "direct streams" over port 8800 |
| Motion / person / vehicle events | **tapo_events** (this repo), polling the hub's event timeline |
| Recordings | **tapo_events**, copying each detection clip from the hub to `/media/tapo` |
| Controls (floodlight, detection, privacy, LED; the sirens are left off the dashboards) | Tapo Control |

The core **TP-Link** integration entries for the two hubs are *disabled*
(not deleted): Tapo Control covers the same controls, and both polling a hub
at once made it answer `INTERNAL_QUERY_ERROR`. The plugs stay on core TP-Link.

## Tapo Control

Installed from HACS. Each hub was added with its IP and the Tapo **cloud
password** (the hubs only accept `admin` + cloud password). This also needs
*Third-Party Compatibility* on in the Tapo app (Me → Tapo Lab). The password
lives only in that config entry (`.storage/core.config_entries` on the Pi).

Setup choices: motion sensor, webhooks, time sync and "Use Stream from Home
Assistant" all **off**. They are ONVIF/RTSP features the hubs don't have.

- Live view: `camera.camera_*_sd_stream_direct` (1280×720, ~13 fps). The Pi 3
  transcodes it to MJPEG with ffmpeg, about one core while someone watches. The
  HD entities (2560×1440) work but are too heavy for the Pi; use SD on
  dashboards. Opening a stream wakes the camera, which costs battery, so the
  dashboards only start it on tap.
- Its own media sync and "Tapo: Recordings" media browser **don't work** with
  H200 hubs. They start with `searchDateWithVideo`, which the H200 never
  answers (10 s timeout). Media sync is switched off; its storage path points
  to `/media/tapo/.tapo_control/<hub>` so nothing lands in the Media panel.
- Battery: `sensor.camera_*_battery_2` (the `_2` because the disabled core
  TP-Link entities still hold the plain names).

## tapo_events

`config/custom_components/tapo_events/`, a small integration with no settings.
It finds the hub cameras through Tapo Control's runtime data and reuses its
connections, so it has no credentials of its own. Everything it reads comes
from the hub's storage, so it never wakes a camera.

Entities, per camera (`camera_front_door`, `camera_garage`):

- `event.*_detection`: fires `person`, `vehicle`, `motion` or `other` for each
  new detection. Attributes: `detections`, `start`, `end`, `duration`,
  `delay` (seconds from the detection's start to HA seeing it) and the raw
  `alarm_type` / `events_1`. Use it for automations and notifications.
- `binary_sensor.*_motion`, `*_person`, `*_vehicle`: on from the moment an
  event is seen until 30 s after it ends.
- `image.*_last_event`: a frame from the latest downloaded clip. Attributes:
  `detection` and `clip` (its path under My media).

How it works:

- Every 10 s it calls `searchDetectionList` for the last 10 minutes (about
  0.2 s per hub). Events already on the timeline at startup are not replayed.
- Event codes, as seen on these C420s (and matching
  [Tapo Control #1445](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/issues/1445)):
  `alarm_type` 2 = motion, 6 = person, 8 = vehicle; `events_1` is a bitmask of
  everything seen (2 motion, 32 person, 128 vehicle). Pets are on but haven't
  triggered yet: when one does, it shows as `other`, with the raw codes in the
  event's attributes. Add the code to `const.py`.
- Clips: after each event, and every 10 minutes, it lists the day's
  recordings and downloads the missing detection clips (timed recordings are
  skipped). The hub serves a clip about a minute after it ends. It uses the
  realtime "playback" request (the H200 returns nothing for the fast
  "download" one), saves the raw MPEG-TS plus the G.711 audio, then runs
  ffmpeg asynchronously to make an MP4 (video copied, audio to AAC) and a
  960 px thumbnail.
- The first run after a restart backfills 7 days; later runs check today and
  yesterday. A download keeps the Pi busy (pytapo decrypts in Python) for
  roughly the clip's length.

Files: `/media/tapo/<camera>/<YYYY-MM-DD>/<HH-MM-SS> <detection>.mp4`, with
thumbnails in a hidden `.thumbs/` next to them. Browse them in **Media → My
media → tapo**. Local copies older than 7 days are deleted. Nothing is ever
deleted from the hubs, which keep their own loop recording.

`/media` is **excluded from the automatic backups** (only `share` and `ssl`
folders are included), so clips never reach Cloudflare R2.

Deploy changes like a package, then restart (HA doesn't reload Python
modules):

```bash
cd config/custom_components && tar cf - tapo_events | ssh -i ~/.ssh/ha-rpi -p 22222 root@192.168.68.68 'cd /mnt/data/supervisor/homeassistant/custom_components && tar xf - && sync'
```

Debug logs: call `logger.set_level` with `custom_components.tapo_events: debug`.
pytapo's own debug output is routed there during downloads.

**One login per hub.** The H200 keeps one session per account. Tapo Control
logs in twice per hub, once as the hub and once as its camera, so each login
logged the other out (`-40401` in its debug log). With `tapo_events` polling
every 10 s, the hub's own entities (siren, LED…) kept going unavailable: 8
session errors in 3 minutes, against 0 with `tapo_events` paused. On discovery,
`tapo_events` therefore points the camera controller's `transport` at the hub
controller's, so both share one login (camera requests are only wrapped in
`controlChild`). Media sessions (live view, clips) authenticate separately on
port 8800 and aren't affected.

It depends on Tapo Control's internals (`hass.data["tapo_control"][entry_id]
["childDevices"][i]["controller"]` and pytapo's `transport`), so check it after
Tapo Control updates.

Tapo Control also treats the hubs as battery-powered, so it refreshes their own
entities only every 10 minutes.

The garage hub is two Deco Wi-Fi hops away, so its logins and requests are
slower than the house hub's.

## Dashboards

- Wall phone: **Cameras** view (`config/dashboards/wall_phone.yaml`).
- Overview: **Security** view, with the detection settings too.

Both show `image.*_last_event` with a play button that opens the SD live
stream in a dialog, plus a 24 h logbook of the `event.*_detection` entities.
The "Clips" tiles open the camera's folder in the Media panel.
