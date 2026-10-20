"""ServerPush notification integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ServerPushClient

type ServerPushConfigEntry = ConfigEntry[ServerPushClient]

PLATFORMS = [Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: ServerPushConfigEntry) -> bool:
    """Set up one token and its notification entities."""
    entry.runtime_data = ServerPushClient(
        async_get_clientsession(hass), entry.data[CONF_TOKEN]
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ServerPushConfigEntry) -> bool:
    """Unload all notification entities for this entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
