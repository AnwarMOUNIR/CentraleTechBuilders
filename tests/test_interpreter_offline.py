import os
import pytest
from api.interpreter_mock import interpret as mock_interpret
from api.interpreter import interpret as real_interpret

@pytest.mark.asyncio
async def test_mock_interpreter_add_item():
    result = await mock_interpret("Un grand café", [], [], "REQUEST", None)
    assert result["intent"] == "add"
    assert result["product_id"] == "coffee"
    assert "large" in result["modifier_ids"]

@pytest.mark.asyncio
async def test_mock_interpreter_unknown():
    result = await mock_interpret("Something unrelated", [], [], "REQUEST", None)
    assert result["intent"] == "unknown"
    assert result["product_id"] is None

@pytest.mark.asyncio
async def test_real_interpreter_fails_safely_without_key(monkeypatch):
    # Ensure no API key is present in the environment
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    result = await real_interpret("Un café", [], [], "REQUEST", None)
    
    # It must return the unknown shape instead of crashing
    assert result["intent"] == "unknown"
    assert result["product_id"] is None