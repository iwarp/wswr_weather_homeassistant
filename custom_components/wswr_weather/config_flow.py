import voluptuous as vol

from homeassistant import config_entries
from .const import CONF_API_URL, DOMAIN, CONF_INTERVAL

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_URL, default="https://api.wswr.jkent.tech/weatherdata/mostrecent/60"): str,
    vol.Required(CONF_INTERVAL, default=1): int
})

class WeatherStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Weather Station integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="WSWR Weather Station API", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors={}
        )
