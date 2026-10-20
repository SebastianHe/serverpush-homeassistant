"""Four fixed notification levels for each ServerPush token."""

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ServerPushConfigEntry
from .api import (
    CannotConnect,
    InvalidAuth,
    InvalidMessage,
    RateLimited,
    ServerPushError,
)
from .const import BASE_URL, DEFAULT_NAME, DOMAIN, STATUSES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ServerPushConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the four levels belonging to this token."""
    async_add_entities(ServerPushNotifyEntity(entry, status) for status in STATUSES)


class ServerPushNotifyEntity(NotifyEntity):
    """A destination with a fixed ServerPush status."""

    _attr_has_entity_name = True
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, entry: ServerPushConfigEntry, status: str) -> None:
        self._entry = entry
        self._status = status
        self._attr_unique_id = f"{entry.entry_id}_{status}"
        self._attr_translation_key = status
        name = (
            DEFAULT_NAME
            if entry.title == DEFAULT_NAME
            else f"{DEFAULT_NAME} {entry.title}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=name,
            manufacturer=DEFAULT_NAME,
            configuration_url=BASE_URL,
        )

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send exactly once and expose safe, translated errors."""
        try:
            await self._entry.runtime_data.async_send_message(
                self._status, message, title
            )
        except InvalidAuth:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from None
        except InvalidMessage:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_message"
            ) from None
        except RateLimited:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="rate_limited"
            ) from None
        except CannotConnect:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from None
        except ServerPushError:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="send_failed"
            ) from None
