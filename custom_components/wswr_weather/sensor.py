import logging
from datetime import timedelta
from typing import Callable

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
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType
)

from .const import DOMAIN, CONF_API_URL,  CONF_INTERVAL, SENSOR_NAME_MAPPING

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=CONF_INTERVAL)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Weather Station sensor entities from a config entry."""
    _LOGGER.info("WSWR Weather Station - async_setup_platform")

    _LOGGER.info("WSWR Weather Station - Creating coordinator")
    coordinator = WeatherStationCoordinator(hass)

    _LOGGER.info("WSWR Weather Station - refresh_data")
    await coordinator.async_config_entry_first_refresh()

    # Create one sensor per key in the latest JSON object.
    sensors = [
        WeatherStationSensor(coordinator, sensor_key)
        for sensor_key in coordinator.data.keys()
        if sensor_key not in ("id", "record_time", "power_v_01mnavg", "wvpk2ht_xxmnavg")
    ]

    _LOGGER.debug("WSWR Weather Station - Creating Sensors: " + str(len(sensors)))
    async_add_entities(sensors, update_before_add=True)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Weather Station sensor entities from a config entry."""
    
    _LOGGER.info("WSWR Weather Station - async_setup_entry")

    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    coordinator = WeatherStationCoordinator(hass)

    await coordinator.async_config_entry_first_refresh()

    # Create the sensors
    sensors = [
        WeatherStationSensor(coordinator, sensor_key)
        for sensor_key in coordinator.data.keys()
        if sensor_key not in ("id", "record_time", "power_v_01mnavg", "wvpk2ht_xxmnavg")
    ]

    _LOGGER.debug("WSWR Weather Station - Creating Sensors: " + str(len(sensors)))

    async_add_entities(sensors, update_before_add=True)


def get_sensor_properties(sensor_key: str):
    """Infer sensor properties based on the sensor key."""
    sensor_key_lower = sensor_key.lower()
    properties = {}
    # Temperature sensors
    if sensor_key_lower.startswith("airtemp") or sensor_key_lower.startswith("dewtemp"):
        properties.update({"device_class": "temperature", "unit": "°C"})
    # Pressure sensors (including various pressure measurements)
    elif (
        sensor_key_lower.startswith("pres")
        or sensor_key_lower.startswith("pressen")
        or "presqfe" in sensor_key_lower
        or "presqnh" in sensor_key_lower
        or "presmsl" in sensor_key_lower
    ):
        properties.update({"device_class": "pressure", "unit": "hPa"})
    # Humidity sensors
    elif sensor_key_lower.startswith("relhumd"):
        properties.update({"device_class": "humidity", "unit": "%"})
    # Rainfall sensors (explicitly in millimeters)
    elif sensor_key_lower.startswith("rainfal"):
        properties.update({"unit": "mm", "state_class": "measurement"})
    # Wind direction sensors (explicitly in degrees)
    elif sensor_key_lower.startswith("winddir") or "wnddirm" in sensor_key_lower:
        properties.update({"unit": "°"})
    # Wind speed, gust, or lull sensors
    elif (
        sensor_key_lower.startswith("windspd")
        or sensor_key_lower.startswith("windgst")
        or sensor_key_lower.startswith("windlul")
    ):
        properties.update({"unit": "km/h", "state_class": "measurement"})
    # Solar radiation sensors
    elif sensor_key_lower.startswith("solradn"):
        properties.update({"unit": "W/m²"})
    # Voltage sensors
    elif sensor_key_lower.startswith("power_v"):
        properties.update({"device_class": "voltage", "unit": "V"})
    # Fallback: no specific unit/device_class inferred
    return properties

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
                _LOGGER.debug("Getting Data from:", CONF_API_URL)
                async with self.session.get(CONF_API_URL) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error fetching data: {response.status}")
                    data = await response.json()

                    # _LOGGER.debug("WSWR JSON:", data)
                    # If the API returns a list of records, use the first one as the latest.
                    if isinstance(data, list) and data:
                        return data[0]
                    return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err


class WeatherStationSensor(SensorEntity):
    """Representation of a sensor for each type of Weather Station API data."""

    def __init__(self, coordinator: WeatherStationCoordinator, sensor_key: str) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._sensor_key = sensor_key

        # Use a friendly name if available; otherwise, fall back.
        friendly_name = SENSOR_NAME_MAPPING.get(sensor_key, f"Weather Station {sensor_key}")
                # Infer sensor properties such as device_class and unit_of_measurement
        properties = get_sensor_properties(sensor_key)

        self._attr_name = friendly_name
        # self._attr_unique_id = f"weather_station_{sensor_key}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{sensor_key}"
        if "device_class" in properties:
            self._attr_device_class = properties["device_class"]
        if "unit" in properties:
            self._attr_unit_of_measurement = properties["unit"]


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
