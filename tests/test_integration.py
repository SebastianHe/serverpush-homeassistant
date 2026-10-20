"""Exercise setup and sends through Home Assistant, not entity stubs."""

import pytest
from aiohttp import ClientConnectionError
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_NAME, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.serverpush.const import BASE_URL, DOMAIN, STATUSES

TOKEN = "test-secret-token"
URL = f"{BASE_URL}/api/v1/chats/{TOKEN}/post/messages"
VALIDATE_URL = f"{BASE_URL}/api/v1/chats/{TOKEN}/validate"


async def setup_entry(hass, *, token=TOKEN, title="Haus"):
    """Set up a real config entry."""
    entry = MockConfigEntry(domain=DOMAIN, title=title, data={CONF_TOKEN: token})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entities_for(hass, entry):
    """Find entities without relying on the configured UI language."""
    return {
        item.unique_id.removeprefix(f"{entry.entry_id}_"): item.entity_id
        for item in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
    }


async def test_user_setup_and_duplicate(hass, aioclient_mock):
    aioclient_mock.get(VALIDATE_URL, json={"valid": True})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: f" {TOKEN} ", CONF_NAME: " Haus "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Haus"
    assert result["data"] == {CONF_TOKEN: TOKEN}
    await hass.async_block_till_done()
    entry = result["result"]
    assert set(entities_for(hass, entry)) == set(STATUSES)
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][0] == "GET"
    assert str(aioclient_mock.mock_calls[0][1]) == VALIDATE_URL
    assert aioclient_mock.mock_calls[0][2] is None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 1


async def test_default_name_and_multiple_tokens(hass, aioclient_mock):
    aioclient_mock.get(VALIDATE_URL, json={"valid": True})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_TOKEN: TOKEN}
    )
    assert result["title"] == "ServerPush"
    await hass.async_block_till_done()
    second = await setup_entry(hass, token="another-token")
    first_entities = entities_for(hass, result["result"])
    second_entities = entities_for(hass, second)
    assert len(first_entities) == len(second_entities) == 4
    assert set(first_entities.values()).isdisjoint(second_entities.values())


@pytest.mark.parametrize(
    "token", ["", "   ", "https://serverpush.net/token", "a/b", "a?b"]
)
async def test_invalid_token_format(hass, token):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_TOKEN: token}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TOKEN: "invalid_token"}


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("title", [None, "Backup"])
async def test_notify_action(hass, aioclient_mock, status, title):
    entry = await setup_entry(hass)
    aioclient_mock.post(URL, status=201, json={"ok": True, "id": 42})
    entity_id = entities_for(hass, entry)[status]
    data = {"message": "**Fertig**"}
    if title is not None:
        data["title"] = title
    await hass.services.async_call(
        "notify",
        "send_message",
        data,
        target={"entity_id": entity_id},
        blocking=True,
    )
    assert aioclient_mock.call_count == 1
    expected = {"message": "**Fertig**", "status": status}
    if title is not None:
        expected["title"] = title
    assert aioclient_mock.mock_calls[0][2] == expected
    assert hass.states.get(entity_id).state not in ("unknown", "unavailable")


@pytest.mark.parametrize(
    ("http_status", "error_key"),
    [
        (401, "invalid_auth"),
        (403, "invalid_auth"),
        (404, "invalid_auth"),
        (429, "rate_limited"),
        (422, "invalid_message"),
        (500, "send_failed"),
        (302, "send_failed"),
    ],
)
async def test_send_errors(hass, aioclient_mock, http_status, error_key, caplog):
    entry = await setup_entry(hass)
    entity_id = entities_for(hass, entry)["error"]
    aioclient_mock.post(URL, status=http_status, text="secret response " + TOKEN)
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"message": "Test"},
            target={"entity_id": entity_id},
            blocking=True,
        )
    assert exc.value.translation_key == error_key
    assert aioclient_mock.call_count == 1
    assert hass.states.get(entity_id).state == "unknown"
    assert TOKEN not in str(exc.value)
    assert TOKEN not in caplog.text
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert bool(flows) == (error_key == "invalid_auth")
    if flows:
        assert flows[0]["context"]["source"] == SOURCE_REAUTH


@pytest.mark.parametrize("exception", [ClientConnectionError(URL), TimeoutError(URL)])
async def test_network_error_does_not_leak_token_or_retry(
    hass, aioclient_mock, exception, caplog
):
    entry = await setup_entry(hass)
    aioclient_mock.post(URL, exc=exception)
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"message": "Test"},
            target={"entity_id": entities_for(hass, entry)["info"]},
            blocking=True,
        )
    assert exc.value.translation_key == "cannot_connect"
    assert aioclient_mock.call_count == 1
    assert TOKEN not in str(exc.value)
    assert TOKEN not in caplog.text


@pytest.mark.parametrize(
    "message,title", [("", None), ("x" * 20001, None), ("x", "t" * 201)]
)
async def test_local_limits(hass, aioclient_mock, message, title):
    entry = await setup_entry(hass)
    data = {"message": message}
    if title is not None:
        data["title"] = title
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "notify",
            "send_message",
            data,
            target={"entity_id": entities_for(hass, entry)["info"]},
            blocking=True,
        )
    assert aioclient_mock.call_count == 0


async def test_token_rotation_preserves_entities_and_uses_new_token(
    hass, aioclient_mock
):
    entry = await setup_entry(hass)
    before = entities_for(hass, entry)
    aioclient_mock.get(
        f"{BASE_URL}/api/v1/chats/replacement-token/validate", json={"valid": True}
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    assert TOKEN not in str(result)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "replacement-token", CONF_NAME: "Neu"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data[CONF_TOKEN] == "replacement-token"
    assert entry.title == "Neu"
    assert entities_for(hass, entry) == before
    assert aioclient_mock.call_count == 1
    aioclient_mock.post(
        f"{BASE_URL}/api/v1/chats/replacement-token/post/messages",
        status=201,
        json={"ok": True, "id": 1},
    )
    await hass.services.async_call(
        "notify",
        "send_message",
        {"message": "Test"},
        target={"entity_id": before["info"]},
        blocking=True,
    )
    assert aioclient_mock.call_count == 2


async def test_reconfigure_blank_token_keeps_current(hass, aioclient_mock):
    entry = await setup_entry(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        data={CONF_NAME: "Anders", CONF_TOKEN: ""},
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data[CONF_TOKEN] == TOKEN
    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize("source", [SOURCE_RECONFIGURE, SOURCE_REAUTH])
@pytest.mark.parametrize(
    "replacement,expected_error",
    [("bad/url", "invalid_token"), ("other-token", "duplicate_token")],
)
async def test_replacement_errors(hass, source, replacement, expected_error):
    entry = await setup_entry(hass)
    await setup_entry(hass, token="other-token")
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": source, "entry_id": entry.entry_id},
        data=entry.data if source == SOURCE_REAUTH else None,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: replacement}
    )
    assert result["errors"] == {CONF_TOKEN: expected_error}
    assert entry.data[CONF_TOKEN] == TOKEN


async def test_reauth_preserves_entities(hass, aioclient_mock):
    aioclient_mock.get(
        f"{BASE_URL}/api/v1/chats/new-token/validate", json={"valid": True}
    )
    entry = await setup_entry(hass)
    before = entities_for(hass, entry)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "new-token"}
    )
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert entry.data[CONF_TOKEN] == "new-token"
    assert entities_for(hass, entry) == before


async def test_unload(hass):
    entry = await setup_entry(hass)
    ids = entities_for(hass, entry).values()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(
        hass.states.get(entity_id) is None
        or hass.states.get(entity_id).state == "unavailable"
        for entity_id in ids
    )


@pytest.mark.parametrize("response", [{"ok": False}, [], {"id": 1}])
async def test_unexpected_response(hass, aioclient_mock, response):
    entry = await setup_entry(hass)
    aioclient_mock.post(URL, status=201, json=response)
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"message": "Test"},
            target={"entity_id": entities_for(hass, entry)["info"]},
            blocking=True,
        )
    assert exc.value.translation_key == "send_failed"
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("content_type", ["application/json", "text/html"])
async def test_invalid_json_response(hass, aioclient_mock, content_type):
    entry = await setup_entry(hass)
    aioclient_mock.post(
        URL, status=201, text="not JSON", headers={"Content-Type": content_type}
    )
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"message": "Test"},
            target={"entity_id": entities_for(hass, entry)["info"]},
            blocking=True,
        )
    assert exc.value.translation_key == "send_failed"
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_RECONFIGURE, SOURCE_REAUTH])
@pytest.mark.parametrize(
    "http_status,response,expected_errors",
    [
        (404, {"detail": "Invalid webhook token."}, {CONF_TOKEN: "invalid_token"}),
        (500, {}, {"base": "unknown"}),
        (302, {}, {"base": "unknown"}),
        (429, {}, {"base": "unknown"}),
        (200, {"valid": False}, {"base": "unknown"}),
        (200, {"valid": 1}, {"base": "unknown"}),
        (200, {}, {"base": "unknown"}),
        (200, [], {"base": "unknown"}),
    ],
)
async def test_validation_failure_and_retry(
    hass, aioclient_mock, source, http_status, response, expected_errors, caplog
):
    entry = await setup_entry(hass, token="stored-token")
    before = entities_for(hass, entry)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": source, "entry_id": entry.entry_id},
        data=entry.data if source == SOURCE_REAUTH else None,
    )
    aioclient_mock.get(VALIDATE_URL, status=http_status, json=response)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == expected_errors
    assert entry.data[CONF_TOKEN] == "stored-token"
    assert entities_for(hass, entry) == before
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert aioclient_mock.call_count == 1
    assert TOKEN not in str(result)
    assert TOKEN not in caplog.text
    aioclient_mock.clear_requests()
    aioclient_mock.get(VALIDATE_URL, json={"valid": True})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TOKEN}
    )
    assert result["type"] is (
        FlowResultType.CREATE_ENTRY if source == SOURCE_USER else FlowResultType.ABORT
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_RECONFIGURE, SOURCE_REAUTH])
@pytest.mark.parametrize(
    "exception", [ClientConnectionError(VALIDATE_URL), TimeoutError(VALIDATE_URL)]
)
async def test_validation_network_error(
    hass, aioclient_mock, source, exception, caplog
):
    entry = await setup_entry(hass, token="stored-token")
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": source, "entry_id": entry.entry_id},
        data=entry.data if source == SOURCE_REAUTH else None,
    )
    aioclient_mock.get(VALIDATE_URL, exc=exception)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_TOKEN] == "stored-token"
    assert aioclient_mock.call_count == 1
    assert TOKEN not in str(result)
    assert TOKEN not in caplog.text


@pytest.mark.parametrize("content_type", ["application/json", "text/html"])
async def test_validation_invalid_json(hass, aioclient_mock, content_type):
    aioclient_mock.get(
        VALIDATE_URL, text="not JSON", headers={"Content-Type": content_type}
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
    assert not hass.config_entries.async_entries(DOMAIN)
