"""UI setup, token replacement and reauthentication for ServerPush."""

from collections.abc import Mapping
from typing import Any

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    CannotConnect,
    InvalidAuth,
    ServerPushClient,
    ServerPushError,
    normalize_token,
)
from .const import DEFAULT_NAME, DOMAIN


def _schema(*, name: str | None = None, replacement: bool = False) -> probatio.Schema:
    """Never prefill a stored secret in a form."""
    fields: dict[Any, Any] = {}
    if name is not None:
        fields[probatio.Optional(CONF_NAME, default=name)] = str
    token_key = (
        probatio.Optional(probatio.Secret(CONF_TOKEN))
        if replacement
        else probatio.Required(probatio.Secret(CONF_TOKEN))
    )
    fields[token_key] = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    return probatio.Schema(fields)


class ServerPushConfigFlow(ConfigFlow, domain=DOMAIN):
    """Manage a separate config entry for each token."""

    VERSION = 1

    async def _async_validate_token(self, token: str) -> dict[str, str]:
        """Map validation failures to safe, translated form errors."""
        try:
            await ServerPushClient(
                async_get_clientsession(self.hass), token
            ).async_validate_token()
        except InvalidAuth:
            return {CONF_TOKEN: "invalid_token"}
        except CannotConnect:
            return {"base": "cannot_connect"}
        except ServerPushError:
            return {"base": "unknown"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create an entry without sending a test notification."""
        errors = {}
        if user_input is not None:
            try:
                token = normalize_token(user_input[CONF_TOKEN])
            except InvalidAuth:
                errors[CONF_TOKEN] = "invalid_token"
            else:
                self._async_abort_entries_match({CONF_TOKEN: token})
                errors = await self._async_validate_token(token)
                if not errors:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, "").strip() or DEFAULT_NAME,
                        data={CONF_TOKEN: token},
                    )
        return self.async_show_form(
            step_id="user", data_schema=_schema(name=""), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace a token while preserving entry and entity identities."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                token = normalize_token(
                    user_input.get(CONF_TOKEN, "").strip() or entry.data[CONF_TOKEN]
                )
            except InvalidAuth:
                errors[CONF_TOKEN] = "invalid_token"
            else:
                if any(
                    other.entry_id != entry.entry_id and other.data[CONF_TOKEN] == token
                    for other in self._async_current_entries()
                ):
                    errors[CONF_TOKEN] = "duplicate_token"
                else:
                    if token != entry.data[CONF_TOKEN]:
                        errors = await self._async_validate_token(token)
                    if not errors:
                        return self.async_update_reload_and_abort(
                            entry,
                            reason="reconfigure_successful",
                            title=user_input.get(CONF_NAME, entry.title).strip()
                            or DEFAULT_NAME,
                            data_updates={CONF_TOKEN: token},
                        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(name=entry.title, replacement=True),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start token replacement after a rejected send."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Accept a replacement for an invalid or revoked token."""
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            try:
                token = normalize_token(user_input[CONF_TOKEN])
            except InvalidAuth:
                errors[CONF_TOKEN] = "invalid_token"
            else:
                if any(
                    other.entry_id != entry.entry_id and other.data[CONF_TOKEN] == token
                    for other in self._async_current_entries()
                ):
                    errors[CONF_TOKEN] = "duplicate_token"
                else:
                    errors = await self._async_validate_token(token)
                    if not errors:
                        return self.async_update_reload_and_abort(
                            entry,
                            reason="reauth_successful",
                            data_updates={CONF_TOKEN: token},
                        )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=_schema(), errors=errors
        )
