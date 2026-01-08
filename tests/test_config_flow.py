"""Tests for the WSWR Weather Station config flow."""
from unittest.mock import MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.wswr_weather.const import DOMAIN, CONF_API_URL, CONF_INTERVAL

async def test_form(hass):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.wswr_weather.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_url": "http://test.url",
                "interval": 5,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "WSWR Weather Station API"
    assert result2["data"] == {
        "api_url": "http://test.url",
        "interval": 5,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(hass):
    """Test options flow."""
    entry = await _create_mock_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch("custom_components.wswr_weather.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "api_url": "http://new.url",
                "interval": 10
            },
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        "api_url": "http://new.url",
        "interval": 10
    }


async def _create_mock_entry(hass):
    """Create a mock config entry."""
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="WSWR Weather Station API",
        data={"api_url": CONF_API_URL, "interval": CONF_INTERVAL},
        source="user",
        options={},
        entry_id="test_entry_id",
        discovery_keys={},
        minor_version=1,
        unique_id="test_unique_id",
    )
    # We need to add the entry to hass to test options flow
    # In a real test we'd use MockConfigEntry from pytest-homeassistant-custom-component
    # but for this context we simulate it or rely on existing fixtures if available.
    # Assuming standard pytest-homeassistant structure:
    try:
        from pytest_homeassistant_custom_component.common import MockConfigEntry
        entry = MockConfigEntry(
             domain=DOMAIN,
             title="WSWR Weather Station API",
             data={"api_url": CONF_API_URL, "interval": CONF_INTERVAL},
        )
        entry.add_to_hass(hass)
    except ImportError:
         print("MockConfigEntry not available, skipping add_to_hass details")
    
    return entry
