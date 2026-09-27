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

def test_privacy_redaction():
    text = "Appelez-moi au +212612345678 pour la commande."
    assert redact(text) == "Appelez-moi au [REDACTED] pour la commande."

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
    assert res["basket"][0]["line_total_mad"] == 18

def test_unknown_product():
    basket = []
    parsed = {
        "intent": "add",
        "product_id": "pizza",
        "quantity": 1,
        "modifier_ids": []
    }
    res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None)
    
    assert res["state"] == "CLARIFY"
    assert res["error"] == "Unknown product_id"

def test_confirm_in_review():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "confirm"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    
    assert res["state"] == "CONFIRMED"