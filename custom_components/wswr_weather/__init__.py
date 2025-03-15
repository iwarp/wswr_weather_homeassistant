"""WSWR.co.nz  Weather Station integration."""

import logging
from custom_components.wswr_weather.sensor import WeatherStationCoordinator, WeatherStationSensor

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the WSWR Weather Station component."""
    _LOGGER.info("WSWR Weather Station - async_setup")

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Weather Station sensor entities from a config entry."""
    _LOGGER.info("WSWR Weather Station - async_setup_entry")

    _LOGGER.info("WSWR Weather Station - Creating coordinator")
    coordinator = WeatherStationCoordinator(hass)

    _LOGGER.info("WSWR Weather Station - refresh_data")
    await coordinator.async_config_entry_first_refresh()

    # Create one sensor per key in the latest JSON object.
    sensors = [
        WeatherStationSensor(coordinator, sensor_key)
        for sensor_key in coordinator.data.keys()
    ]

    _LOGGER.debug("WSWR Weather Station - Creating Sensors", sensors)

    async_add_entities(sensors, update_before_add=True)
