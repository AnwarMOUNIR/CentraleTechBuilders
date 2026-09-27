import asyncio
import httpx

from api.interpreter import interpret as real_interpret
from api.interpreter_mock import interpret as mock_interpret


MENU = [
    {
        "id": "coffee",
        "name": "Coffee",
        "base_price_mad": 12,
        "modifiers": [
            {"id": "small", "label": "Small", "delta_mad": 0},
            {"id": "large", "label": "Large", "delta_mad": 6},
            {"id": "no_sugar", "label": "No sugar", "delta_mad": 0},
        ],
    }
]


def run(coroutine):
    return asyncio.run(coroutine)


def test_mock_adds_large_coffee_without_sugar():
    result = run(mock_interpret("One large coffee without sugar", MENU, [], "REQUEST", None))
    assert result == {
        "intent": "add",
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": ["large", "no_sugar"],
        "missing_field": None,
    }


def test_mock_change_and_commands():
    changed = run(mock_interpret("Make that two coffees", MENU, [], "REVIEW", None))
    assert changed["intent"] == "change"
    assert changed["quantity"] == 2
    for text, intent in (("Confirm", "confirm"), ("Cancel", "cancel"), ("Repeat", "repeat")):
        assert run(mock_interpret(text, MENU, [], "REVIEW", None))["intent"] == intent


def test_mock_answers_pending_quantity():
    pending = {"product_id": "coffee", "quantity": None, "modifier_ids": ["large"], "missing_field": "quantity"}
    result = run(mock_interpret("two", MENU, [], "CLARIFY", pending))
    assert result["intent"] == "add"
    assert result["quantity"] == 2


def test_local_interpreter_fails_closed_when_ollama_is_unavailable(monkeypatch):
    from api import interpreter
    class OfflineClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): raise httpx.ConnectError('offline')
    monkeypatch.setattr(interpreter.httpx, 'AsyncClient', lambda **kwargs: OfflineClient())
    result = run(real_interpret("One coffee", MENU, [], "REQUEST", None))
    assert result == {
        "intent": "unknown",
        "product_id": None,
        "quantity": None,
        "modifier_ids": [],
        "missing_field": None,
    }
