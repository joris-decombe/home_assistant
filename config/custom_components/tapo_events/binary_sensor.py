"""Motion, person and vehicle binary sensors for each hub camera."""

from __future__ import annotations

import time

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import Camera
from .const import DETECTIONS, SIGNAL_NEW_CAMERA, SIGNAL_UPDATE

DEVICE_CLASSES = {
    "motion": BinarySensorDeviceClass.MOTION,
    "person": BinarySensorDeviceClass.OCCUPANCY,
    "vehicle": BinarySensorDeviceClass.MOVING,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    @callback
    def add(cam: Camera) -> None:
        async_add_entities(Detection(cam, kind) for kind in DETECTIONS)

    for cam in entry.runtime_data.cameras.values():
        add(cam)
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_CAMERA, add))


class Detection(BinarySensorEntity):
    """On while an event of this kind is recorded, and HOLD_SECONDS after."""

    _attr_should_poll = False

    def __init__(self, cam: Camera, kind: str) -> None:
        self._cam = cam
        self._kind = kind
        self._attr_name = f"{cam.name} {kind}"
        self._attr_device_class = DEVICE_CLASSES[kind]
        self._attr_unique_id = f"{cam.dev_id}_{kind}"

    @property
    def available(self) -> bool:
        return self._cam.available

    @property
    def is_on(self) -> bool:
        return time.time() < self._cam.active_until.get(self._kind, 0)

    @property
    def extra_state_attributes(self) -> dict | None:
        return self._cam.last_event

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self._cam.dev_id),
                self.async_write_ha_state,
            )
        )
