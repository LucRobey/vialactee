import pytest
import asyncio
from unittest.mock import MagicMock
from core.CommandRouter import CommandRouter, router


@pytest.mark.anyio
async def test_command_router_dispatch_live_deck_luminosity():
    mock_mm = MagicMock()
    mock_mm.listener = MagicMock()
    mock_mm.listener.luminosite = 0.5

    instruction = {
        "page": "live_deck",
        "action": "set_luminosity",
        "payload": {"value": 80}
    }
    result = await router.dispatch(mock_mm, instruction)
    assert result == {"applied": True}
    assert mock_mm.listener.luminosite == 0.8
    mock_mm._persist_app_config_value.assert_called_once_with("luminosity", 80)


@pytest.mark.anyio
async def test_command_router_invalid_payload():
    mock_mm = MagicMock()
    instruction = {
        "page": "live_deck",
        "action": "set_luminosity",
        "payload": "not a dict"
    }
    result = await router.dispatch(mock_mm, instruction)
    assert result["applied"] is False
    assert result["reason"] == "invalid_payload"


@pytest.mark.anyio
async def test_command_router_unknown_instruction():
    mock_mm = MagicMock()
    instruction = {
        "page": "unknown_page",
        "action": "unknown_action",
        "payload": {}
    }
    result = await router.dispatch(mock_mm, instruction)
    assert result["applied"] is False
    assert result["reason"] == "unsupported_instruction"


@pytest.mark.anyio
async def test_command_router_custom_registration():
    custom_router = CommandRouter()

    @custom_router.register("test_page", "test_action")
    async def handle_test(mm, payload):
        return {"applied": True, "echo": payload.get("data")}

    mock_mm = MagicMock()
    res = await custom_router.dispatch(mock_mm, {
        "page": "test_page",
        "action": "test_action",
        "payload": {"data": 123}
    })
    assert res == {"applied": True, "echo": 123}
