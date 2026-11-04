"""Test component setup and unload."""

from unittest.mock import MagicMock, patch

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wswr_weather import options_update_listener
from custom_components.wswr_weather.const import CONF_API_URL, CONF_INTERVAL, DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


async def test_setup_and_unload_entry(hass):
    """Test setting up and unloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WSWR Weather Station API",
        data={"api_url": CONF_API_URL, "interval": CONF_INTERVAL},
        options={"interval": 2},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.wswr_weather.sensor.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.wswr_weather.sensor.WeatherStationCoordinator._async_update_data",
            return_value={"airtemp_01mnavg": 18.2},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][entry.entry_id]["interval"] == 2

    with patch.object(
        hass.config_entries, "async_reload", return_value=True
    ) as mock_reload:
        await options_update_listener(hass, entry)
        mock_reload.assert_called_once_with(entry.entry_id)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]
