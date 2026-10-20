"""Small asynchronous client for the ServerPush webhook API."""

import re

from aiohttp import ClientError, ClientSession, ClientTimeout, ContentTypeError

from .const import BASE_URL, STATUSES


class ServerPushError(Exception):
    """A request could not be completed."""


class InvalidAuth(ServerPushError):
    """The webhook token is invalid or revoked."""


class CannotConnect(ServerPushError):
    """The service could not be reached."""


class RateLimited(ServerPushError):
    """The request or monthly message allowance was exceeded."""


class InvalidMessage(ServerPushError):
    """The message does not meet the API limits."""


def normalize_token(token: str) -> str:
    """Accept a raw URL-safe token, never a webhook URL."""
    token = token.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise InvalidAuth("Enter the token, without a URL.")
    return token


class ServerPushClient:
    """Send messages without logging secret webhook URLs or retrying POSTs."""

    def __init__(self, session: ClientSession, token: str) -> None:
        self._session = session
        self._token = normalize_token(token)

    async def async_validate_token(self) -> None:
        """Check token validity without sending a message or consuming quota."""
        try:
            async with self._session.get(
                f"{BASE_URL}/api/v1/chats/{self._token}/validate",
                timeout=ClientTimeout(total=15),
                allow_redirects=False,
            ) as response:
                if response.status == 404:
                    raise InvalidAuth
                if response.status != 200:
                    raise ServerPushError("ServerPush rejected token validation.")
                try:
                    result = await response.json()
                except ValueError, ContentTypeError:
                    raise ServerPushError("Unexpected ServerPush response.") from None
                if not isinstance(result, dict) or result.get("valid") is not True:
                    raise ServerPushError("Unexpected ServerPush response.")
        except TimeoutError, ClientError:
            raise CannotConnect("Could not reach ServerPush.") from None

    async def async_send_message(
        self, status: str, message: str, title: str | None = None
    ) -> None:
        """Send one message; an ambiguous network failure must not be retried."""
        if (
            status not in STATUSES
            or not 1 <= len(message) <= 20_000
            or (title is not None and len(title) > 200)
        ):
            raise InvalidMessage

        payload = {"message": message, "status": status}
        if title is not None:
            payload["title"] = title
        try:
            async with self._session.post(
                f"{BASE_URL}/api/v1/chats/{self._token}/post/messages",
                json=payload,
                timeout=ClientTimeout(total=15),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403, 404):
                    raise InvalidAuth
                if response.status == 429:
                    raise RateLimited
                if response.status == 422:
                    raise InvalidMessage
                if response.status != 201:
                    raise ServerPushError("ServerPush rejected the request.")
                try:
                    result = await response.json()
                except ValueError, ContentTypeError:
                    raise ServerPushError("Unexpected ServerPush response.") from None
                if not isinstance(result, dict) or result.get("ok") is not True:
                    raise ServerPushError("Unexpected ServerPush response.")
        except TimeoutError, ClientError:
            # aiohttp errors can include the full URL containing the secret token.
            raise CannotConnect("Could not reach ServerPush.") from None
