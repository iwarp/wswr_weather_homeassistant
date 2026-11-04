"""Fixtures for testing."""

import sys
from homeassistant import config_entries
import pytest
import pytest_socket

if not hasattr(config_entries.OptionsFlow, "config_entry"):
    config_entries.OptionsFlow.config_entry = property(  # type: ignore[attr-defined]
        lambda self: self.hass.config_entries.async_get_entry(self.handler)
    )


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef, request) -> None:
    """Allow Windows asyncio event loop self-pipe socket creation."""
    if sys.platform == "win32" and fixturedef.argname == "event_loop":
        pytest_socket.enable_socket()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations."""
    return
