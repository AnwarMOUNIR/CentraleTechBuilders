"""Deterministic English interpreter used without network or API keys."""

from __future__ import annotations

import re


UNKNOWN = {
    "intent": "unknown",
    "product_id": None,
    "quantity": None,
    "modifier_ids": [],
    "missing_field": None,
}

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def _quantity(text: str) -> int | None:
    digit = re.search(r"\b([1-9]|[1-9]\d)\b", text)
    if digit:
        return int(digit.group(1))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return value
    return None


async def interpret(text: str, menu: list, basket: list, state: str, pending: dict | None) -> dict:
    normalized = text.casefold().strip()
    base = dict(UNKNOWN)

    if any(phrase in normalized for phrase in ("cancel", "never mind", "stop order")):
        return {**base, "intent": "cancel"}
    if any(phrase in normalized for phrase in ("confirm", "place order", "yes, order")):
        return {**base, "intent": "confirm"}
    if any(phrase in normalized for phrase in ("repeat", "say that again", "what is my total")):
        return {**base, "intent": "repeat"}

    quantity = _quantity(normalized)
    if pending and pending.get("missing_field") in {"quantity", "qty"} and quantity is not None:
        return {**base, "intent": "add", "quantity": quantity}

    modifiers = []
    if "large" in normalized:
        modifiers.append("large")
    elif "small" in normalized:
        modifiers.append("small")
    if "without sugar" in normalized or "no sugar" in normalized:
        modifiers.append("no_sugar")

    if any(phrase in normalized for phrase in ("change", "make that", "instead")):
        return {
            **base,
            "intent": "change",
            "quantity": quantity,
            "modifier_ids": modifiers,
        }

    if "coffee" in normalized:
        return {
            **base,
            "intent": "add",
            "product_id": "coffee",
            "quantity": quantity or 1,
            "modifier_ids": modifiers,
        }

    return base
