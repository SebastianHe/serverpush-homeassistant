# ServerPush for Home Assistant

English · [Deutsch](README.de.md)

<img src="custom_components/serverpush/brand/icon.png" alt="ServerPush app icon" width="128" height="128">

Send notifications from Home Assistant to your [ServerPush.net](https://www.serverpush.net) chats – for example, when a window is left open, a backup finishes, or something goes wrong.

- Four notification entities per webhook token: `info`, `success`, `warning`, and `error`.
- Send from automations and scripts using the standard `notify.send_message` action, with an optional title and Markdown in the message.
- Set up multiple chats or tokens independently.
- Configure through the UI, validate tokens without sending a test message, and replace tokens while preserving entities and automations.
- English and German translations, with no polling or extra YAML configuration required.

## Install with HACS

Requirements: Home Assistant **2026.10 or newer**, [HACS installed and configured](https://www.hacs.xyz/docs/use/), and a webhook token for a ServerPush chat. ServerPush message allowances and push settings still apply.

1. Open this repository in HACS using the button:

   [![Open repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SebastianHe&repository=serverpush-homeassistant&category=integration)

   Alternatively, open **HACS → ⋮ → Custom repositories**, enter `https://github.com/SebastianHe/serverpush-homeassistant`, and select **Integration** as the type. Inclusion in the default HACS catalog is not required.
2. Open **ServerPush** in HACS and select **Download**. Confirm the download.
3. Restart Home Assistant.
4. Start setup using the button:

   [![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow/?domain=serverpush)

   Alternatively, go to **Settings → Devices & services → Add integration → ServerPush**.
5. Enter the raw webhook token and an optional name, such as `Home`. Do not enter a complete webhook URL.

The buttons use [My Home Assistant](https://my.home-assistant.io/). Check that it points to your Home Assistant instance. The HACS button requires configured HACS; the setup button works after installation and restart.

### Manual installation

1. Copy `custom_components/serverpush` from this repository to `/config/custom_components/serverpush` in your Home Assistant installation.
2. Restart Home Assistant and add **ServerPush** under **Settings → Devices & services → Add integration**.
3. Enter the raw webhook token and an optional name.

## Usage

An entry named `Home` creates a service device called “ServerPush Home” with four notification entities. With English entity names, the initial IDs are typically:

| Entity | ServerPush status |
| --- | --- |
| `notify.serverpush_home_info` | `info` |
| `notify.serverpush_home_success` | `success` |
| `notify.serverpush_home_warning` | `warning` |
| `notify.serverpush_home_error` | `error` |

Names are translated into English and German. Actual entity IDs depend on the configured language and existing entities; a German warning entity might end in `_warnung`. Select the target in the automation editor or copy its ID from **Settings → Devices & services → Entities**.

```yaml
action: notify.send_message
target:
  entity_id: notify.serverpush_home_warning
data:
  title: "Window left open"
  message: "The bedroom window has been open for 30 minutes."
```

`message` is required (1–20,000 characters). `title` is optional (up to 200 characters). Markdown is passed to ServerPush unchanged. The selected entity determines the status; the action does not need an additional `status` field. Select just one of the four entities for a single notification: each selected entity sends a separate message.

Add more tokens through **Add integration → ServerPush** to create additional entries. The same token can only be configured once. Different tokens may belong to the same chat; each token gets its own entities.

## Validate and replace tokens

Setup validates the token using `GET /api/v1/chats/:token/validate` before creating the entry. Invalid or revoked tokens and tokens for deleted chats are rejected. Validation sends no message and creates no push jobs. It consumes neither message allowance nor the webhook request limit and works even when those limits are exhausted. Connection problems or unexpected API responses leave the form open for another attempt.

Successful validation confirms validity at the time of the request. Sending a message later can still fail because of limits or a token being revoked in the meantime.

Use the integration entry menu → **Reconfigure** to change the name or token. An empty token field keeps the current token. A replacement token is validated before saving. Internal entity identities belong to the integration entry rather than the token, so replacing a token preserves entities and existing automations. Renaming the entry also preserves registered entity IDs.

If a token is rejected while sending, Home Assistant starts a reauthentication flow. The replacement token is validated before saving. Failed messages are not stored or resent automatically.

## Errors and limitations

- Invalid or revoked tokens, network failures, API errors, and exceeded limits are reported as errors to the calling automation.
- ServerPush chat message limits and push settings still apply. An accepted message does not mean that every device receives a push notification.
- Failed POST requests are **not retried automatically**. A message may already have been accepted when a timeout occurs; check the chat before resending.
- There is no polling or queue. The entity state records the last send successfully confirmed to Home Assistant, rather than a delivery receipt from a device.
- The token is stored in the Home Assistant configuration. Forms do not prefill it; the integration does not log tokens or secret webhook URLs. Protect your Home Assistant backups accordingly.
- Messages are sent exclusively over HTTPS to `https://www.serverpush.net`. Custom server addresses are not configurable in this version.

## Development

The test environment requires Python 3.14 and tests against Home Assistant 2026.10.2:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest --cov=custom_components.serverpush --cov-report=term-missing
```

Tests use Home Assistant's real config flow, entity registry, and notification infrastructure. HTTP requests are mocked; no real tokens or messages are needed. Network sockets are disabled during tests.

GitHub Actions also runs HACS validation and Home Assistant hassfest. See [RELEASING.md](RELEASING.md) for publication requirements.

API contract: [ServerPush API documentation](https://www.serverpush.net/api/docs).

## License

[MIT](LICENSE) © 2026 Sebastian Heinisch.
