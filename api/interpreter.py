"""Gemini-backed extraction of bounded ordering intents."""

from __future__ import annotations

import json
import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ParsedIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    intent: Literal["add", "change", "confirm", "cancel", "repeat", "unknown"]
    product_id: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=99)
    modifier_ids: list[str] = Field(default_factory=list)
    missing_field: str | None = None


def _unknown() -> dict:
    return ParsedIntent(
        intent="unknown",
        product_id=None,
        quantity=None,
        modifier_ids=[],
        missing_field=None,
    ).model_dump()


def _ids_are_valid(parsed: ParsedIntent, menu: list[dict], pending: dict | None) -> bool:
    products = {item["id"]: item for item in menu}
    product_id = parsed.product_id or (pending or {}).get("product_id")
    if parsed.product_id is not None and parsed.product_id not in products:
        return False

    if not parsed.modifier_ids:
        return True
    if product_id not in products:
        return False

    valid_modifiers = {modifier["id"] for modifier in products[product_id].get("modifiers", [])}
    return all(modifier_id in valid_modifiers for modifier_id in parsed.modifier_ids)


async def interpret(
    text: str,
    menu: list,
    basket: list,
    state: str,
    pending: dict | None,
) -> dict:
    """Return a validated intent or a safe unknown result on every failure."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _unknown()

    prompt = {
        "task": "Extract one ordering intent. Never invent menu IDs or prices.",
        "rules": [
            "Use only product_id and modifier_ids present in the supplied menu.",
            "Use intent unknown when the request is ambiguous or unsupported.",
            "Use quantity null when the customer did not provide a quantity and it cannot safely be inferred.",
            "A confirmation is explicit only when the customer clearly says confirm or equivalent.",
            "Return data only; do not write a customer-facing response.",
        ],
        "state": state,
        "basket": basket,
        "pending": pending,
        "menu": menu,
        "customer_text": text,
    }

    try:
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=json.dumps(prompt, ensure_ascii=False),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=ParsedIntent,
            ),
        )
        parsed = ParsedIntent.model_validate_json(response.text or "")
        if not _ids_are_valid(parsed, menu, pending):
            return _unknown()
        return parsed.model_dump()
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError, Exception):
        # Provider, timeout, malformed-output, schema and ID failures all fail closed.
        return _unknown()
