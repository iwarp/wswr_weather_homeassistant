import voluptuous as vol

from homeassistant import config_entries
from .const import CONF_API_URL, DOMAIN, CONF_INTERVAL

DATA_SCHEMA = vol.Schema({
    vol.Required("api_url", default=CONF_API_URL): str,
    vol.Required("interval", default=CONF_INTERVAL): int
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
            errors={},
            description_placeholders={
                "api_url": "Your API endpoint URL",
                "interval": "Update frequency in minutes",
            }
        )
