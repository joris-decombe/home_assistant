"""Events and recordings for Tapo cameras behind an H200 hub.

Tapo Control streams these cameras, but reads motion over ONVIF, which hub
cameras don't have, and its media sync stalls because the H200 times out on
searchDateWithVideo. The hub does keep each camera's detection timeline (what
the Tapo app shows under Events) and its clips, so this reads both through the
connections Tapo Control already holds: no credentials of its own, and the
battery cameras stay asleep since everything comes from the hub's SD card.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ALARM_TYPES,
    EVENT_BITS,
    EVENT_TYPES,
    FAILURES_BEFORE_UNAVAILABLE,
    HOLD_SECONDS,
    SCAN_INTERVAL,
    SEEN_TTL_SECONDS,
    SIGNAL_NEW_CAMERA,
    SIGNAL_UPDATE,
    SYNC_INTERVAL_SECONDS,
    TAPO_CONTROL,
)
from .recordings import Recorder

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.IMAGE]


def decode(event: dict) -> list[str]:
    """Return the detections in a searchDetectionList item, most specific first."""
    found = {ALARM_TYPES.get(int(event.get("alarm_type", 0)))}
    bits = int(event.get("events_1", 0))
    found |= {name for bit, name in EVENT_BITS.items() if bits & bit}
    found.discard(None)
    return [t for t in EVENT_TYPES if t in found] or ["other"]


@dataclass
class Camera:
    """One hub camera and what we know about its recent events."""

    dev_id: str
    name: str
    available: bool = False
    failures: int = 0
    seeded: bool = False
    seen: dict[int, float] = field(default_factory=dict)  # start_time -> seen at
    active_until: dict[str, float] = field(default_factory=dict)
    last_event: dict | None = None
    listeners: list = field(default_factory=list)  # event entities' callbacks
    # Latest downloaded clip and a frame from it.
    image: bytes | None = None
    image_time: datetime | None = None
    clip: str | None = None  # path under /media
    last_sync: float = 0
    sync_wanted: bool = True


class Poller:
    """Polls every hub camera Tapo Control knows about."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.cameras: dict[str, Camera] = {}
        self.recorder = Recorder(hass)
        self._busy = False

    def _children(self):
        """Yield (dev_id, child data) for every hub camera in Tapo Control."""
        for entry_data in (self.hass.data.get(TAPO_CONTROL) or {}).values():
            if not isinstance(entry_data, dict):
                continue
            hub = entry_data.get("controller")
            for child in entry_data.get("childDevices") or []:
                info = (child.get("camData") or {}).get("basic_info") or {}
                controller = child.get("controller")
                if not controller or not info.get("dev_id"):
                    continue
                # Tapo Control logs in to the hub twice (hub and camera), and
                # the H200 keeps one session per account: each login logs the
                # other out (-40401), so with this polling the hub's entities
                # kept going unavailable. Share the hub's login; camera
                # requests only add a controlChild wrapper on top of it.
                if hub and getattr(controller, "transport", None) is not hub.transport:
                    _LOGGER.debug("%s: sharing the hub's session", info["dev_id"])
                    controller.transport = hub.transport
                yield info["dev_id"], child

    async def async_poll(self, _now=None) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            for dev_id, child in list(self._children()):
                await self._poll_camera(dev_id, child)
        finally:
            self._busy = False

    async def _poll_camera(self, dev_id: str, child: dict) -> None:
        cam = self.cameras.get(dev_id)
        if cam is None:
            info = child["camData"]["basic_info"]
            cam = self.cameras[dev_id] = Camera(
                dev_id=dev_id, name=info.get("device_alias") or dev_id
            )
            await self.recorder.load_latest(cam)
            async_dispatcher_send(self.hass, SIGNAL_NEW_CAMERA, cam)

        controller = child["controller"]
        try:
            # Defaults to the last 10 minutes, in the camera's clock.
            events = await self.hass.async_add_executor_job(controller.getEvents)
        except Exception as err:  # pytapo raises bare Exceptions
            # The hub is slow to answer while it streams, so allow a few misses.
            cam.failures += 1
            if cam.failures == FAILURES_BEFORE_UNAVAILABLE:
                _LOGGER.warning("Can't read events for %s: %s", cam.name, err)
                cam.available = False
                async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(dev_id))
            return
        if not cam.available:
            _LOGGER.debug("Reading events for %s", cam.name)
        cam.available = True
        cam.failures = 0

        now = time.time()
        for event in sorted(events, key=lambda e: e["start_time"]):
            start, end = int(event["start_time"]), int(event["end_time"])
            kinds = decode(event)
            if start not in cam.seen:
                # Events already there at startup are history, not news.
                cam.seen[start] = now if cam.seeded else 0
                if cam.seeded:
                    self._fire(cam, event, kinds)
            if not cam.seen[start]:
                continue
            # An event still being recorded may grow, so extend from end_time.
            until = max(end, cam.seen[start]) + HOLD_SECONDS
            for kind in ("motion", *kinds):
                if kind != "other" and until > cam.active_until.get(kind, 0):
                    cam.active_until[kind] = until
        cam.seeded = True
        cam.seen = {
            s: t for s, t in cam.seen.items() if s > now - SEEN_TTL_SECONDS
        }
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(dev_id))

        if cam.sync_wanted or now - cam.last_sync > SYNC_INTERVAL_SECONDS:
            self.entry.async_create_background_task(
                self.hass, self._sync(cam, controller), f"tapo_events sync {cam.name}"
            )
            cam.sync_wanted = False
            cam.last_sync = now

    async def _sync(self, cam: Camera, controller) -> None:
        if await self.recorder.sync(cam, controller):
            async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(cam.dev_id))

    @callback
    def _fire(self, cam: Camera, event: dict, kinds: list[str]) -> None:
        start, end = int(event["start_time"]), int(event["end_time"])
        cam.last_event = {
            "detections": kinds,
            "start": datetime.fromtimestamp(start).astimezone().isoformat(),
            "end": datetime.fromtimestamp(end).astimezone().isoformat(),
            "duration": end - start,
            "delay": round(time.time() - start),
            "alarm_type": event.get("alarm_type"),
            "events_1": event.get("events_1"),
        }
        _LOGGER.debug("%s: %s", cam.name, cam.last_event)
        # Its clip lands on the hub once recorded; sync keeps retrying until then.
        cam.sync_wanted = True
        for listener in cam.listeners:
            listener(kinds[0], cam.last_event)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    poller = entry.runtime_data = Poller(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        async_track_time_interval(
            hass, poller.async_poll, SCAN_INTERVAL, cancel_on_shutdown=True
        )
    )
    hass.async_create_task(poller.async_poll())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(hass, entry, device) -> bool:
    """Entities have no device, so any device left on this entry is stale."""
    return True
