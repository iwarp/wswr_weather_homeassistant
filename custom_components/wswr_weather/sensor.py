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

from .const import DOMAIN, CONF_API_URL,  CONF_INTERVAL

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=CONF_INTERVAL)

# Mapping from raw JSON keys to friendly sensor names.
SENSOR_NAME_MAPPING = {
    "id": "Record ID",
    "record_time": "Record Time",
    "dewtemp_01mnavg": "Dew Point (1-min Avg)",
    "presqfe_01hrmax": "Station Pressure QFE (1-hr Max)",
    "presqnh_01hrmin": "Sea-Level Pressure QNH (1-hr Min)",
    "pressen_01hrchg": "Pressure Change (1-hr)",
    "airtemp_01mnavg": "Air Temperature (1-min Avg)",
    "rainfal_01mnacc": "Rainfall (1-min Accum)",
    "relhumd_01hrmax": "Relative Humidity (1-hr Max)",
    "relhumd_01hrmin": "Relative Humidity (1-hr Min)",
    "airtemp_01hrmin": "Air Temperature (1-hr Min)",
    "pressen_01mnavg": "Pressure (1-min Avg)",
    "pressen_01hrmax": "Pressure (1-hr Max)",
    "windgst_01hrtim": "Wind Gust Time (1-hr)",
    "rainfal_10mnmax": "Rainfall (10-min Max)",
    "solradn_01mnavg": "Solar Radiation (1-min Avg)",
    "windccw_01mnmax": "Wind CCW (1-min Max)",
    "windcw__10mnmax": "Wind CW (10-min Max)",
    "windrun_01hracc": "Wind Run (1-hr Accum)",
    "windspd_01mnavg": "Wind Speed (1-min Avg)",
    "wvpk2ht_xxmnavg": "WVPK2HT (1-min Avg)",
    "power_v_01mnavg": "Power Voltage (1-min Avg)",
    "windgst_10mnmax": "Wind Gust (10-min Max)",
    "windccw_10mnmax": "Wind CCW (10-min Max)",
    "windcw__01hrmax": "Wind CW (1-hr Max)",
    "wndccwm_01hrmax": "Wind CW Mean (1-hr Max)",
    "presqfe_01mnavg": "Station Pressure QFE (1-min Avg)",
    "presqnh_01hrmax": "Sea-Level Pressure QNH (1-hr Max)",
    "presmsl_01hrmin": "Pressure MSL (1-hr Min)",
    "presmsl_01mnavg": "Pressure MSL (1-min Avg)",
    "presmsl_01hrmax": "Pressure MSL (1-hr Max)",
    "presqfe_01hrmin": "Station Pressure QFE (1-hr Min)",
    "solradn_10mnacc": "Solar Radiation (10-min Accum)",
    "pressen_01hrmin": "Pressure (1-hr Min)",
    "rainfal_01hracc": "Rainfall (1-hr Accum)",
    "solradn_01hracc": "Solar Radiation (1-hr Accum)",
    "rainfal_10mnacc": "Rainfall (10-min Accum)",
    "relhumd_01mnavg": "Relative Humidity (1-min Avg)",
    "winddir_10mnavg": "Wind Direction (10-min Avg)",
    "windgst_01hrdir": "Wind Gust Direction (1-hr)",
    "winddir_01hravg": "Wind Direction (1-hr Avg)",
    "winddir_01mnavg": "Wind Direction (1-min Avg)",
    "windgst_01hrmax": "Wind Gust (1-hr Max)",
    "windcw__01mnmax": "Wind CW (1-min Max)",
    "windgst_01mnmax": "Wind Gust (1-min Max)",
    "windlul_01mnmin": "Wind Lull (1-min Min)",
    "airtemp_01hrmax": "Air Temperature (1-hr Max)",
    "solradn_01mnacc": "Solar Radiation (1-min Accum)",
    "windlul_10mnmin": "Wind Lull (10-min Min)",
    "windspd_01hravg": "Wind Speed (1-hr Avg)",
    "windspd_10mnavg": "Wind Speed (10-min Avg)",
    "wndcwm__01hrmax": "Wind CW Mean (1-hr Max)",
    "wnddirm_01mnavg": "Wind Dir Mean (1-min Avg)",
    "wnddirm_10mnavg": "Wind Dir Mean (10-min Avg)",
    "wndgstm_01hrdir": "Wind Gust Mean Dir (1-hr)",
    "windccw_01hrmax": "Wind CCW (1-hr Max)",
    "wndcwm__01mnmax": "Wind CW Mean (1-min Max)",
    "rainfal_24hracc": "Rainfall (24-hr Accum)",
    "rainfal_07dyacc": "Rainfall (7-day Accum)"
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Weather Station sensor entities from a config entry."""
    coordinator = WeatherStationCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    # Create one sensor per key in the latest JSON object.
    sensors = [
        WeatherStationSensor(coordinator, sensor_key)
        for sensor_key in coordinator.data.keys()
    ]
    async_add_entities(sensors, update_before_add=True)


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
