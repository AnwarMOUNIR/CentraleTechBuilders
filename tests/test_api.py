import pytest

from api.logic import next_step
from api.privacy import redact

SAMPLE_MENU = [
    {
        "id": "coffee",
        "name": "Coffee",
        "base_price_mad": 12,
        "modifiers": [
            {"id": "large", "label": "Large", "delta_mad": 6},
            {"id": "no_sugar", "label": "No sugar", "delta_mad": 0}
        ]
    }
]


def test_privacy_redacts_full_phone_number_and_english_address():
    text = "Call me at +212612345678 or visit Street 123 Main Road."
    assert redact(text) == "Call me at [REDACTED] or visit [REDACTED_ADDRESS]."
    assert redact("+212612345678") == "[REDACTED]"


def test_add_item_logic():
    parsed = {
        "intent": "add",
        "product_id": "coffee",
        "quantity": 1,
        "modifier_ids": ["large", "no_sugar"]
    }
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "REVIEW"
    assert result["total_mad"] == 18
    assert len(result["basket"]) == 1


@pytest.mark.parametrize("quantity", [0, -1, True, "two", 100])
def test_invalid_quantities_return_clarification(quantity):
    parsed = {"intent": "add", "product_id": "coffee", "quantity": quantity, "modifier_ids": []}
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["error"] == "Invalid quantity"


def test_null_quantity_requests_clarification_with_complete_pending():
    parsed = {"intent": "add", "product_id": "coffee", "quantity": None, "modifier_ids": []}
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["question"] == "What quantity would you like?"
    assert result["pending"] == {
        "product_id": "coffee",
        "quantity": None,
        "modifier_ids": [],
        "missing_field": "quantity"
    }


def test_unknown_product_returns_clarification():
    parsed = {"intent": "add", "product_id": "tacos", "quantity": 1, "modifier_ids": []}
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["error"] == "Unknown product_id"


def test_unknown_modifier_returns_clarification_without_adding_item():
    parsed = {"intent": "add", "product_id": "coffee", "quantity": 1, "modifier_ids": ["bad_mod"]}
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["error"] == "Unknown modifier_id"
    assert result["basket"] == []


def test_cancel_intent():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    result = next_step({"intent": "cancel"}, basket, "REVIEW", SAMPLE_MENU, None)
    assert result["state"] == "CANCELLED"
    assert result["pending"] is None


def test_repeat_intent():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    result = next_step({"intent": "repeat"}, basket, "REVIEW", SAMPLE_MENU, None)
    assert result["state"] == "REVIEW"
    assert "12" in result["reply_text"]


def test_unknown_intent_does_not_add_product():
    parsed = {"intent": "unknown", "product_id": "coffee", "quantity": 1}
    result = next_step(parsed, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["basket"] == []


def test_model_failure_returns_clarification():
    result = next_step(None, [], "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "CLARIFY"
    assert result["error"] == "Unclear intent"


def test_confirmation_outside_review_is_rejected():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    result = next_step({"intent": "confirm"}, basket, "REQUEST", SAMPLE_MENU, None)
    assert result["state"] == "REQUEST"
    assert result["error"] == "Cannot confirm outside of REVIEW state"


def test_empty_basket_confirmation_is_rejected():
    result = next_step({"intent": "confirm"}, [], "REVIEW", SAMPLE_MENU, None)
    assert result["state"] == "REVIEW"
    assert result["error"] == "Cannot confirm empty basket"


def test_successful_confirmation_non_empty_basket():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    result = next_step({"intent": "confirm"}, basket, "REVIEW", SAMPLE_MENU, None)
    assert result["state"] == "CONFIRMED"
    assert result["total_mad"] == 12


def test_valid_pending_clarification():
    pending = {"product_id": "coffee", "quantity": 1, "modifier_ids": [], "missing_field": "modifier"}
    result = next_step({"intent": "add", "modifier_ids": ["large"]}, [], "CLARIFY", SAMPLE_MENU, pending)
    assert result["state"] == "REVIEW"
    assert result["basket"][0]["modifier_ids"] == ["large"]


@pytest.mark.parametrize(
    ("parsed", "error"),
    [
        ({"intent": "add", "modifier_ids": ["invalid_mod"]}, "Unknown modifier_id"),
        ({"intent": "unknown"}, "Unclear pending answer"),
    ],
)
def test_invalid_pending_answers_remain_in_clarify(parsed, error):
    pending = {"product_id": "coffee", "quantity": 1, "modifier_ids": [], "missing_field": "modifier"}
    result = next_step(parsed, [], "CLARIFY", SAMPLE_MENU, pending)
    assert result["state"] == "CLARIFY"
    assert result["error"] == error
    assert result["basket"] == []
    assert result["pending"] == pending


def test_pending_response_has_all_contract_fields():
    result = next_step({"intent": "unknown"}, [], "CLARIFY", SAMPLE_MENU, {"product_id": "coffee"})
    assert result["pending"] == {
        "product_id": "coffee",
        "quantity": None,
        "modifier_ids": [],
        "missing_field": None
    }


def test_quantity_and_modifier_correction_does_not_mutate_input_basket():
    basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": [], "line_total_mad": 12}]
    original_basket = [dict(line) for line in basket]
    parsed = {"intent": "change", "quantity": 2, "modifier_ids": ["large"]}
    result = next_step(parsed, basket, "REVIEW", SAMPLE_MENU, None)
    assert result["state"] == "REVIEW"
    assert result["basket"][0]["quantity"] == 2
    assert result["basket"][0]["modifier_ids"] == ["large"]
    assert result["basket"][0]["line_total_mad"] == 36
    assert basket == original_basket