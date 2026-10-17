"""Config flow: nothing to ask, the cameras come from Tapo Control."""

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class TapoEventsFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Tapo hub camera events", data={})
        return self.async_show_form(step_id="user")
