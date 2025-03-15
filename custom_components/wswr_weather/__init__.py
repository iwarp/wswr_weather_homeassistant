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
