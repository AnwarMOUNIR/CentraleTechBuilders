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
    text = "Appelez-moi au +212612345678 ou visitez rue Mohammed V."
    redacted = redact(text)
    assert "[REDACTED]" in redacted
    assert "[REDACTED_ADDRESS]" in redacted

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

def test_invalid_quantities():
    basket = []
    # Quantité zéro ou négative ou non entière
    for invalid_qty in [0, -1, "deux", 100]:
        parsed = {"intent": "add", "product_id": "coffee", "quantity": invalid_qty, "modifier_ids": []}
        res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None)
        assert res["state"] == "CLARIFY"
        assert res["error"] == "Invalid quantity"

def test_unknown_modifier_returns_clarify():
    basket = []
    parsed = {"intent": "add", "product_id": "coffee", "quantity": 1, "modifier_ids": ["bad_mod"]}
    res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None)
    assert res["state"] == "CLARIFY"
    assert res["error"] == "Unknown modifier_id"
    assert len(res["basket"]) == 0  # Panier préservé

def test_change_intent():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "change"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["state"] == "REQUEST"
    assert len(res["basket"]) == 0  # Le dernier élément a été retiré pour correction

def test_cancel_intent():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "cancel"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["state"] == "CANCELLED"

def test_repeat_intent():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "repeat"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["state"] == "REVIEW"
    assert "12" in res["reply_text"]

def test_unknown_intent_with_product_id_ignored():
    basket = []
    # product_id présent mais intent inconnu -> ne doit pas ajouter au panier
    parsed = {"intent": "unknown", "product_id": "coffee", "quantity": 1}
    res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None)
    assert res["state"] == "CLARIFY"
    assert len(res["basket"]) == 0

def test_confirm_outside_review():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    parsed = {"intent": "confirm"}
    res = next_step(parsed, basket, "REQUEST", SAMPLE_MENU, None) # État REQUEST au lieu de REVIEW
    assert res["error"] == "Cannot confirm outside of REVIEW state"

def test_confirm_empty_basket():
    basket = []
    parsed = {"intent": "confirm"}
    res = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert res["error"] == "Cannot confirm empty basket"