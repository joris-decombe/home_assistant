"""One event entity per hub camera: fires on each new detection."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import Camera
from .const import EVENT_TYPES, SIGNAL_NEW_CAMERA, SIGNAL_UPDATE


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    @callback
    def add(cam: Camera) -> None:
        async_add_entities([DetectionEvent(cam)])

    for cam in entry.runtime_data.cameras.values():
        add(cam)
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_CAMERA, add))


class DetectionEvent(EventEntity):
    _attr_device_class = EventDeviceClass.MOTION
    _attr_event_types = EVENT_TYPES
    _attr_should_poll = False

    def __init__(self, cam: Camera) -> None:
        self._cam = cam
        self._attr_unique_id = f"{cam.dev_id}_detection"
        # Not on Tapo Control's device: HA no longer lets another integration
        # join a device by its identifiers, so these stand alone.
        self._attr_name = f"{cam.name} detection"

    @property
    def available(self) -> bool:
        return self._cam.available

    async def async_added_to_hass(self) -> None:
        self._cam.listeners.append(self._on_event)
        self.async_on_remove(lambda: self._cam.listeners.remove(self._on_event))
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self._cam.dev_id),
                self.async_write_ha_state,
            )
        )

    @callback
    def _on_event(self, event_type: str, attributes: dict) -> None:
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()
