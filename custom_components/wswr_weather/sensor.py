"""Sensor platform for the WSWR Weather Station integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import CONF_API_URL, CONF_INTERVAL, DOMAIN, SENSOR_NAME_MAPPING

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=CONF_INTERVAL)

EXCLUDED_SENSOR_KEYS = (
    "id",
    "record_time",
    "power_v_01mnavg",
    "wvpk2ht_xxmnavg",
)

WIND_DIRECTION_DEVICE_CLASS = SensorDeviceClass.WIND_DIRECTION


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weather Station sensor entities from a config entry."""
    _LOGGER.info("WSWR Weather Station - async_setup_entry")

    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    api_url = config.get("api_url", CONF_API_URL)
    interval = config.get("interval", CONF_INTERVAL)

    coordinator = WeatherStationCoordinator(hass, api_url, interval, config_entry)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        WeatherStationSensor(coordinator, sensor_key)
        for sensor_key in coordinator.data
        if sensor_key not in EXCLUDED_SENSOR_KEYS
    ]

    _LOGGER.debug("WSWR Weather Station - Creating Sensors: %s", len(sensors))
    async_add_entities(sensors)


def get_sensor_properties(sensor_key: str) -> dict[str, Any]:
    """Infer sensor properties based on the sensor key."""
    sensor_key_lower = sensor_key.lower()
    properties: dict[str, Any] = {}

    # Wind Gust Time/Direction (avoid matching generic 'windgst' speed first)
    if "windgst" in sensor_key_lower:
        if "tim" in sensor_key_lower:
            return {}
        if "dir" in sensor_key_lower:
            return {"device_class": WIND_DIRECTION_DEVICE_CLASS, "unit": DEGREE}

    # Wind Direction (general)
    if "winddir" in sensor_key_lower or "wnddirm" in sensor_key_lower:
        return {"device_class": WIND_DIRECTION_DEVICE_CLASS, "unit": DEGREE}

    # Temperature sensors
    if sensor_key_lower.startswith("airtemp") or sensor_key_lower.startswith("dewtemp"):
        properties.update(
            {
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit": UnitOfTemperature.CELSIUS,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Pressure sensors
    elif (
        sensor_key_lower.startswith("pres")
        or sensor_key_lower.startswith("pressen")
        or "presqfe" in sensor_key_lower
        or "presqnh" in sensor_key_lower
        or "presmsl" in sensor_key_lower
    ):
        properties.update(
            {
                "device_class": SensorDeviceClass.PRESSURE,
                "unit": UnitOfPressure.HPA,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Humidity sensors
    elif sensor_key_lower.startswith("relhumd"):
        properties.update(
            {
                "device_class": SensorDeviceClass.HUMIDITY,
                "unit": PERCENTAGE,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Rainfall sensors. The "acc" keys are rolling-window totals (last 1 min,
    # 1 hr, 24 hr, 7 days) that fall as old readings drop out, so they are
    # measurements, not ever-increasing meters.
    elif sensor_key_lower.startswith("rainfal"):
        properties.update(
            {
                "device_class": SensorDeviceClass.PRECIPITATION,
                "unit": UnitOfLength.MILLIMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Wind Speed / Gust / Lull / Cross Wind
    elif (
        sensor_key_lower.startswith("windspd")
        or sensor_key_lower.startswith("windgst")
        or sensor_key_lower.startswith("windlul")
        or "windcw" in sensor_key_lower
        or "windccw" in sensor_key_lower
    ):
        properties.update(
            {
                "device_class": SensorDeviceClass.WIND_SPEED,
                "unit": UnitOfSpeed.KNOTS,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Wind Run (Distance), also a rolling-window total
    elif "windrun" in sensor_key_lower:
        properties.update(
            {
                "device_class": SensorDeviceClass.DISTANCE,
                "unit": UnitOfLength.KILOMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Solar radiation sensors
    elif sensor_key_lower.startswith("solradn"):
        properties.update(
            {
                "device_class": SensorDeviceClass.IRRADIANCE,
                "unit": UnitOfIrradiance.WATTS_PER_SQUARE_METER,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    # Voltage sensors
    elif sensor_key_lower.startswith("power_v"):
        properties.update(
            {
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            }
        )

    return properties


class WeatherStationCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Weather Station API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_url: str,
        interval: int,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="WSWR Weather Station API",
            update_interval=timedelta(minutes=interval),
        )
        if config_entry is not None:
            self.config_entry = config_entry
        self.api_url = api_url
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            async with asyncio.timeout(30):
                _LOGGER.debug("Getting Data from: %s", self.api_url)
                async with self.session.get(self.api_url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error fetching data: {response.status}")
                    data = await response.json()

                    # If the API returns a list of records, use the first one as the latest.
                    if isinstance(data, list) and data:
                        return data[0]
                    return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err


class WeatherStationSensor(CoordinatorEntity[WeatherStationCoordinator], SensorEntity):
    """Representation of a sensor for each type of Weather Station API data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WeatherStationCoordinator, sensor_key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key

        entry_id = coordinator.config_entry.entry_id
        self._attr_name = SENSOR_NAME_MAPPING.get(
            sensor_key, f"Weather Station {sensor_key}"
        )
        self._attr_unique_id = f"{entry_id}-{sensor_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="WSWR Weather Station",
            manufacturer="WSWR Upper Hutt",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://wswr.co.nz",
        )

        properties = get_sensor_properties(sensor_key)
        if "device_class" in properties:
            self._attr_device_class = properties["device_class"]
        if "unit" in properties:
            self._attr_native_unit_of_measurement = properties["unit"]
        if "state_class" in properties:
            self._attr_state_class = properties["state_class"]

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._sensor_key)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return additional attributes."""
        return {"measurement": self._sensor_key}
