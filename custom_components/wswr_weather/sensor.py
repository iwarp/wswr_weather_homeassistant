import asyncio
import logging
from datetime import timedelta

import async_timeout
import aiohttp
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_API_URL,  CONF_INTERVAL, SENSOR_NAME_MAPPING

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=CONF_INTERVAL)

class WeatherStationCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Weather Station API."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="WSWR Weather Station API",
            update_interval=SCAN_INTERVAL,
        )
        self.session = aiohttp.ClientSession()

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                async with self.session.get(CONF_API_URL) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error fetching data: {response.status}")
                    data = await response.json()

                    _LOGGER.debug("WSWR JSON:", data)
                    # If the API returns a list of records, use the first one as the latest.
                    if isinstance(data, list) and data:
                        return data[0]
                    return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err


class WeatherStationSensor(SensorEntity):
    """Representation of a sensor for one key from the Weather Station API data."""

    def __init__(self, coordinator: WeatherStationCoordinator, sensor_key: str) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._sensor_key = sensor_key
        # Use a friendly name if available; otherwise, fall back.
        friendly_name = SENSOR_NAME_MAPPING.get(sensor_key, f"Weather Station {sensor_key}")
        self._attr_name = friendly_name
        self._attr_unique_id = f"weather_station_{sensor_key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._sensor_key)

    @property
    def extra_state_attributes(self):
        """Return additional attributes (if needed)."""
        return {"measurement": self._sensor_key}

    async def async_update(self) -> None:
        """Request an update from the coordinator."""
        await self.coordinator.async_request_refresh()
