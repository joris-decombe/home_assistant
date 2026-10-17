"""A frame from each hub camera's latest downloaded clip."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import Camera
from .const import SIGNAL_NEW_CAMERA, SIGNAL_UPDATE


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    @callback
    def add(cam: Camera) -> None:
        async_add_entities([LastEventImage(hass, cam)])

    for cam in entry.runtime_data.cameras.values():
        add(cam)
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_CAMERA, add))


class LastEventImage(ImageEntity):
    _attr_content_type = "image/jpeg"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, cam: Camera) -> None:
        super().__init__(hass)
        self._cam = cam
        self._attr_name = f"{cam.name} last event"
        self._attr_unique_id = f"{cam.dev_id}_last_event"

    @property
    def available(self) -> bool:
        return self._cam.image is not None

    @property
    def image_last_updated(self):
        return self._cam.image_time

    @property
    def extra_state_attributes(self) -> dict | None:
        # The clip under HA's Media panel ("My media"), and what triggered it
        # (the end of its name: "11-49-33 person.mp4").
        clip = self._cam.clip
        if not clip:
            return None
        return {
            "clip": clip.removeprefix("/media/"),
            "detection": clip.rsplit(" ", 1)[-1].removesuffix(".mp4"),
        }

    async def async_image(self) -> bytes | None:
        return self._cam.image

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self._cam.dev_id),
                self.async_write_ha_state,
            )
        )
