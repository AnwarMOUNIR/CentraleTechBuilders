import pytest
from api.logic import next_step
from api.privacy import redact

SAMPLE_MENU = [
    {
        "id": "coffee",
        "name": "Café",
        "base_price_mad": 12,
        "modifiers": [
            {"id": "large", "label": "Grand", "delta_mad": 6},
            {"id": "no_sugar", "label": "Sans sucre", "delta_mad": 0}
        ]
    }
]

def test_exact_phone_redaction():
    text = "Appelez-moi au +212612345678 pour la commande."
    redacted = redact(text)
    assert redacted == "Appelez-moi au [REDACTED] pour la commande."
    assert redact("+212612345678") == "[REDACTED]"

def test_add_item_logic():
    basket = []
    parsed = {
        "intent": "add",
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": ["large", "no_sugar"]
    }
    res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None)
    assert res["state"] == "REVIEW"
    assert res["total_mad"] == 18
    assert len(res["basket"]) == 1

def test_valid_pending_clarification():
    basket = []
    pending = {
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": [],
        "missing_field": "modifier"
    }
    parsed = {"intent": "add", "modifier_ids": ["large"]}
    res = next_step(parsed, basket, "CLARIFY", SAMPLE_MENU, pending)
    assert res["state"] == "REVIEW"
    assert len(res["basket"]) == 1

def test_invalid_pending_answer_remaining_in_clarify():
    basket = []
    pending = {
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": [],
        "missing_field": "modifier"
    }
    parsed = {"intent": "add", "modifier_ids": ["invalid_mod"]}
    res = next_step(parsed, basket, "CLARIFY", SAMPLE_MENU, pending)
    assert res["state"] == "CLARIFY"
    assert res["error"] == "Unknown modifier_id"
    assert len(res["basket"]) == 0

def test_unclear_pending_answer_does_not_add_base_item():
    pending = {
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": [],
        "missing_field": "modifier"
    }
    res = next_step({"intent": "unknown"}, [], "CLARIFY", SAMPLE_MENU, pending)
    assert res["state"] == "CLARIFY"
    assert res["basket"] == []
    assert res["pending"] == pending

def test_pending_response_has_all_contract_fields():
    res = next_step({"intent": "unknown"}, [], "CLARIFY", SAMPLE_MENU, {"product_id": "coffee"})
    assert res["pending"] == {
        "product_id": "coffee",
        "quantity": None,
        "modifier_ids": [],
        "missing_field": None
    }

def test_successful_confirmation_non_empty_basket():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "confirm"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["state"] == "CONFIRMED"
    assert res["total_mad"] == 12

def test_quantity_or_modifier_correction():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "change", "quantity": 2, "modifier_ids": ["large"]}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["state"] == "REVIEW"
    assert res["basket"][0]["quantity"] == 2
    assert res["basket"][0]["modifier_ids"] == ["large"]
    assert res["basket"][0]["line_total_mad"] == 36