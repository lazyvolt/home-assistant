"""LazyVolt Cloud → Peblar charge controller integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import LazyVoltApiClient
from .const import CONF_CLOUD_TOKEN, CONF_PEBLAR_ENTRY_ID, DOMAIN
from .coordinator import LazyVoltCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LazyVolt from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    api = LazyVoltApiClient(
        entry.data["cloud_url"],
        session,
        entry.data[CONF_CLOUD_TOKEN],
    )
    coordinator = LazyVoltCoordinator(hass, api, entry.data[CONF_PEBLAR_ENTRY_ID])
    coordinator.setup_entity_ids()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
