"""Tests for the WSWR Weather Station sensor."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
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
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.wswr_weather.const import DOMAIN
from custom_components.wswr_weather.sensor import (
    WIND_DIRECTION_DEVICE_CLASS,
    WeatherStationCoordinator,
    WeatherStationSensor,
    get_sensor_properties,
)


@pytest.mark.parametrize(
    ("sensor_key", "expected_props"),
    [
        (
            "airtemp_01mnavg",
            {
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit": UnitOfTemperature.CELSIUS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "presqfe_01hrmax",
            {
                "device_class": SensorDeviceClass.PRESSURE,
                "unit": UnitOfPressure.HPA,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "relhumd_01hrmax",
            {
                "device_class": SensorDeviceClass.HUMIDITY,
                "unit": PERCENTAGE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "rainfal_01mnacc",
            {
                "device_class": SensorDeviceClass.PRECIPITATION,
                "unit": UnitOfLength.MILLIMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "rainfal_24hracc",
            {
                "device_class": SensorDeviceClass.PRECIPITATION,
                "unit": UnitOfLength.MILLIMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "rainfal_01mnavg",
            {
                "device_class": SensorDeviceClass.PRECIPITATION,
                "unit": UnitOfLength.MILLIMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "windspd_01mnavg",
            {
                "device_class": SensorDeviceClass.WIND_SPEED,
                "unit": UnitOfSpeed.KNOTS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "winddir_01mnavg",
            {"device_class": WIND_DIRECTION_DEVICE_CLASS, "unit": DEGREE},
        ),
        (
            "solradn_01mnavg",
            {
                "device_class": SensorDeviceClass.IRRADIANCE,
                "unit": UnitOfIrradiance.WATTS_PER_SQUARE_METER,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "power_v_01mnavg",
            {
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        (
            "windrun_01hracc",
            {
                "device_class": SensorDeviceClass.DISTANCE,
                "unit": UnitOfLength.KILOMETERS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        # Specific cases
        ("windgst_01hrtim", {}),  # Time string
        (
            "windgst_01hrdir",
            {"device_class": WIND_DIRECTION_DEVICE_CLASS, "unit": DEGREE},
        ),
        (
            "windcw__10mnmax",
            {
                "device_class": SensorDeviceClass.WIND_SPEED,
                "unit": UnitOfSpeed.KNOTS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ),
        ("unknown_sensor", {}),
    ],
)
def test_get_sensor_properties(sensor_key, expected_props):
    """Test sensor property inference."""
    assert get_sensor_properties(sensor_key) == expected_props


async def test_sensor_entity(hass):
    """Test the sensor entity."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator.data = {"airtemp_01mnavg": 20.5}
    coordinator.last_update_success = True

    sensor = WeatherStationSensor(coordinator, "airtemp_01mnavg")

    assert sensor.unique_id == "test_entry-airtemp_01mnavg"
    assert sensor.has_entity_name is True
    assert sensor.native_value == 20.5
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.extra_state_attributes == {"measurement": "airtemp_01mnavg"}
    assert sensor.device_info is not None
    assert (DOMAIN, "test_entry") in sensor.device_info["identifiers"]


async def test_coordinator_update_success(hass):
    """Test coordinator data fetch returning a list of records."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = [{"airtemp_01mnavg": 19.1}]

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch(
        "custom_components.wswr_weather.sensor.async_get_clientsession",
        return_value=mock_session,
    ):
        coordinator = WeatherStationCoordinator(hass, "http://test.url", 1)
        data = await coordinator._async_update_data()

    assert data == {"airtemp_01mnavg": 19.1}


async def test_coordinator_update_dict_success(hass):
    """Test coordinator data fetch returning a dict directly."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"airtemp_01mnavg": 19.1}

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch(
        "custom_components.wswr_weather.sensor.async_get_clientsession",
        return_value=mock_session,
    ):
        coordinator = WeatherStationCoordinator(hass, "http://test.url", 1)
        data = await coordinator._async_update_data()

    assert data == {"airtemp_01mnavg": 19.1}


async def test_coordinator_update_http_error(hass):
    """Test coordinator raises UpdateFailed on non-200 status."""
    mock_response = AsyncMock()
    mock_response.status = 500

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch(
        "custom_components.wswr_weather.sensor.async_get_clientsession",
        return_value=mock_session,
    ):
        coordinator = WeatherStationCoordinator(hass, "http://test.url", 1)
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_update_client_error(hass):
    """Test coordinator raises UpdateFailed on a network error."""
    mock_session = MagicMock()
    mock_session.get.side_effect = aiohttp.ClientError("boom")

    with patch(
        "custom_components.wswr_weather.sensor.async_get_clientsession",
        return_value=mock_session,
    ):
        coordinator = WeatherStationCoordinator(hass, "http://test.url", 1)
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
