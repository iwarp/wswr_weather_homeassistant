import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from .const import CONF_API_URL, DOMAIN, CONF_INTERVAL

DATA_SCHEMA = vol.Schema({
    vol.Required("api_url", default=CONF_API_URL): str,
    vol.Required("interval", default=CONF_INTERVAL): int
})

class WeatherStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Weather Station integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

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

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("api_url", default=self.config_entry.options.get("api_url", self.config_entry.data.get("api_url", CONF_API_URL))): str,
                vol.Required("interval", default=self.config_entry.options.get("interval", self.config_entry.data.get("interval", CONF_INTERVAL))): int
            }),
        )
