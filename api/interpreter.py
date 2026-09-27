"""Ollama-backed extraction of bounded ordering intents."""

from __future__ import annotations

import json
import os
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ParsedIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    intent: Literal["add", "change", "confirm", "cancel", "repeat", "unknown"]
    product_id: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=99)
    modifier_ids: list[str] = Field(default_factory=list)
    missing_field: str | None = None


from api.catalog import CATALOG


class SelectedItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    product_id: str
    quantity: int | None = Field(default=None, ge=1, le=99)
    modifier_ids: list[str] = Field(default_factory=list)


class QwenOrderingReasoning(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['order', 'inquiry', 'change', 'confirm', 'cancel', 'repeat', 'unknown']
    restaurant_id: str | None = None
    items: list[SelectedItem] = Field(default_factory=list)
    unmatched_items: list[str] = Field(default_factory=list)
    suggestion_or_question: str | None = None


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
    """Analyze messy personal order, match menu items across restaurants, answer inquiries using local Qwen."""
    from api.storage import search_catalog, conversation_context
    candidates = search_catalog(text, CATALOG, basket + ([pending] if pending and pending.get('product_id') else []))
    catalog_desc = [
        {
            'restaurant_id': r['id'],
            'restaurant_name': r['name'],
            'menu': [
                {
                    'product_id': item['id'],
                    'name': item['name'],
                    'price_mad': item['base_price_mad'],
                    'modifiers': [m['id'] for m in item.get('modifiers', [])]
                }
                for item in r['menu']
            ]
        }
        for r in candidates
    ]

    system = (
        'You are the ClearOrder intelligent ordering assistant with full access to all partner restaurants.\n'
        'You have a retrieved subset of catalog items below; absence does not prove an item is unavailable. Ask for a more specific item when needed.\n'
        'For changes, preserve unspecified quantities and options; return quantity=null when not stated. Never treat liking a suggestion as confirmation.\n'
        'Rules:\n'
        '1. If the customer is ordering items (casual, messy, conversational, or multi-item): action="order". '
        'Set restaurant_id to the restaurant that offers the requested items. Fit each item using exact product_id, quantity, and valid modifier_ids. '
        'Put requested items not on any menu into unmatched_items.\n'
        '2. If the customer asks what is available at other restaurants, what restaurants exist, or is exploring preferences: action="inquiry". '
        'In suggestion_or_question, you MUST write a helpful, natural-speech summary of what other restaurants offer based on the catalog (e.g. Lilac Kitchen for burgers and tacos, Cornerstone Grill for sandwiches and pastilla, Little Olive Kitchen for salads, Cedar Spice House for mezze, Orange Grove Kitchen for seafood pizza, Demo Cafe for coffee and croissants).\n'
        '3. If changing items: action="change".\n'
        '4. If confirming: action="confirm".\n'
        '5. If cancelling: action="cancel".\n'
        '6. If repeating order: action="repeat".\n'
        'Retrieved Restaurant Catalog:\n' + json.dumps(catalog_desc, ensure_ascii=False)
        + '\nCurrent order context: ' + json.dumps({'basket':basket,'state':state,'pending':pending})
    )

    try:
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
        payload = {
            'model': os.getenv('OLLAMA_MODEL', 'qwen3:4b'),
            'stream': False,
            'format': QwenOrderingReasoning.model_json_schema(),
            'think': False,
            'keep_alive': int(os.getenv('OLLAMA_KEEP_ALIVE', '-1')),
            'options': {'temperature': 0, 'num_ctx': 4096, 'num_predict': 350},
            'messages': [
                {'role': 'system', 'content': system},
                *conversation_context.get(),
                {'role': 'user', 'content': text[:500]},
            ],
        }
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(f'{base_url}/api/chat', json=payload)
            response.raise_for_status()
        raw_content = response.json()['message']['content']

        # Handle legacy tests mocking `ParsedIntent` schema:
        if '"intent"' in raw_content:
            parsed = ParsedIntent.model_validate_json(raw_content)
            context = pending or (basket[-1] if parsed.intent == 'change' and basket else None)
            if not _ids_are_valid(parsed, menu, context):
                return _unknown()
            return parsed.model_dump()

        reasoning = QwenOrderingReasoning.model_validate_json(raw_content)

        # Find which restaurant was selected or default to current menu
        target_r = next((r for r in CATALOG if r['id'] == reasoning.restaurant_id), None)
        active_menu = target_r['menu'] if target_r else menu
        active_r_id = target_r['id'] if target_r else None
        products = {p['id']: p for r in candidates for p in r['menu']}

        if reasoning.action == 'order':
            valid_items = []
            for item in reasoning.items:
                if item.product_id in products:
                    valid_mods = {m['id'] for m in products[item.product_id].get('modifiers', [])}
                    filtered_mods = [m for m in item.modifier_ids if m in valid_mods]
                    valid_items.append({'product_id': item.product_id, 'quantity': item.quantity or 1, 'modifier_ids': filtered_mods})
            if not valid_items and not reasoning.unmatched_items:
                return _unknown()
            return {
                'intent': 'add',
                'restaurant_id': active_r_id,
                'items': valid_items,
                'product_id': valid_items[0]['product_id'] if valid_items else None,
                'quantity': valid_items[0]['quantity'] if valid_items else 1,
                'modifier_ids': valid_items[0]['modifier_ids'] if valid_items else [],
                'unmatched_items': reasoning.unmatched_items,
                'missing_field': None,
            }
        elif reasoning.action == 'inquiry':
            return {
                'intent': 'inquiry',
                'restaurant_id': active_r_id,
                'suggestion_or_question': reasoning.suggestion_or_question,
                'items': [],
                'product_id': None,
                'quantity': None,
                'modifier_ids': [],
                'missing_field': None,
            }
        elif reasoning.action == 'change':
            return {
                'intent': 'change',
                'restaurant_id': active_r_id,
                'items': [i.model_dump() for i in reasoning.items],
                'product_id': reasoning.items[0].product_id if reasoning.items else None,
                'quantity': reasoning.items[0].quantity if reasoning.items else None,
                'modifier_ids': reasoning.items[0].modifier_ids if reasoning.items else [],
                'suggestion_or_question': reasoning.suggestion_or_question,
                'missing_field': None,
            }
        elif reasoning.action == 'confirm':
            return {'intent': 'confirm', 'product_id': None, 'quantity': None, 'modifier_ids': [], 'missing_field': None}
        elif reasoning.action == 'cancel':
            return {'intent': 'cancel', 'product_id': None, 'quantity': None, 'modifier_ids': [], 'missing_field': None}
        elif reasoning.action == 'repeat':
            return {'intent': 'repeat', 'product_id': None, 'quantity': None, 'modifier_ids': [], 'missing_field': None}
        return _unknown()
    except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError):
        return _unknown()
