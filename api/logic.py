from typing import Dict, List, Optional, Any

def _normalize_pending(pending: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if pending is None:
        return None
    return {
        "product_id": pending.get("product_id"),
        "quantity": pending.get("quantity"),
        "modifier_ids": pending.get("modifier_ids") or [],
        "missing_field": pending.get("missing_field"),
    }


def next_step(
    parsed: Optional[Dict[str, Any]], 
    basket: List[Dict[str, Any]], 
    state: str, 
    menu: List[Dict[str, Any]], 
    pending: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if not parsed:
        parsed = {"intent": "unknown"}

    intent = parsed.get("intent", "unknown")
    product_id = parsed.get("product_id")
    quantity = parsed.get("quantity", 1)
    modifier_ids = parsed.get("modifier_ids", []) or []
    pending = _normalize_pending(pending)

    new_basket = [dict(item) for item in basket]
    menu_dict = {item["id"]: item for item in menu}

    if quantity is not None:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0 or quantity > 99:
            return {
                "state": "CLARIFY",
                "reply_text": "Invalid quantity. Please enter a number from 1 to 99.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "What quantity would you like?",
                "pending": pending,
                "error": "Invalid quantity"
            }

    # Resolve only when the requested field has a concrete, valid answer.
    if pending and intent not in ["cancel", "repeat", "confirm"]:
        p_product_id = pending.get("product_id")
        p_quantity = pending.get("quantity")
        p_modifier_ids = list(pending.get("modifier_ids", []))
        missing_field = pending.get("missing_field")
        answer_quantity = parsed.get("quantity")
        answer_product_id = parsed.get("product_id")
        answer_modifiers = parsed.get("modifier_ids")
        quantity_requested = missing_field in {"quantity", "qty"}
        product_requested = missing_field in {"product", "product_id"}
        modifiers_requested = missing_field in {
            "modifier", "modifiers", "modifier_id", "modifier_ids", "size"
        }

        if intent != "unknown" and (quantity_requested or product_requested or modifiers_requested):
            resolved_product_id = answer_product_id if product_requested else p_product_id
            resolved_quantity = answer_quantity if quantity_requested else p_quantity
            if modifiers_requested and not answer_modifiers:
                return {
                    "state": "CLARIFY",
                    "reply_text": "I did not understand your choice. Please specify an option.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": "Which option would you like?",
                    "pending": pending,
                    "error": "Unclear pending answer"
                }

            product = menu_dict.get(resolved_product_id)
            if product is None:
                return {
                    "state": "CLARIFY",
                    "reply_text": "Unknown product. Please choose an item from the menu.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": "Which menu item would you like?",
                    "pending": pending,
                    "error": "Unknown product_id"
                }

            if resolved_quantity is None:
                return {
                    "state": "CLARIFY",
                    "reply_text": "Please specify a quantity.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": "What quantity would you like?",
                    "pending": pending,
                    "error": "Unclear pending answer"
                }
            if (
                not isinstance(resolved_quantity, int)
                or isinstance(resolved_quantity, bool)
                or resolved_quantity <= 0
                or resolved_quantity > 99
            ):
                return {
                    "state": "CLARIFY",
                    "reply_text": "Invalid quantity. Please enter a number from 1 to 99.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": "What quantity would you like?",
                    "pending": pending,
                    "error": "Invalid quantity"
                }

            mod_dict = {item["id"]: item for item in product.get("modifiers", [])}
            for mid in p_modifier_ids + (answer_modifiers or []):
                if mid not in mod_dict:
                    return {
                        "state": "CLARIFY",
                        "reply_text": f"Unknown option '{mid}'. Please try again.",
                        "basket": new_basket,
                        "total_mad": sum(item["line_total_mad"] for item in new_basket),
                        "question": f"Which menu option did you mean instead of '{mid}'?",
                        "pending": pending,
                        "error": "Unknown modifier_id"
                    }

            combined_mods = list(dict.fromkeys(p_modifier_ids + (answer_modifiers or [])))
            base_price = product["base_price_mad"]
            mod_delta = sum(mod_dict[mid]["delta_mad"] for mid in combined_mods)
            line_total = resolved_quantity * (base_price + mod_delta)
            new_basket.append({
                "product_id": resolved_product_id,
                "quantity": resolved_quantity,
                "modifier_ids": combined_mods,
                "line_total_mad": line_total
            })
            total_mad = sum(item["line_total_mad"] for item in new_basket)
            return {
                "state": "REVIEW",
                "reply_text": f"Added {resolved_quantity} {product['name']}. The total is {total_mad} dirhams. Confirm, change, or cancel?",
                "basket": new_basket,
                "total_mad": total_mad,
                "question": None,
                "pending": None,
                "error": None
            }

        if intent == "unknown" or not (quantity_requested or product_requested or modifiers_requested):
            return {
                "state": "CLARIFY",
                "reply_text": "I did not understand your answer. Please specify the requested choice.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Could you clarify your choice?",
                "pending": pending,
                "error": "Unclear pending answer"
            }

    if intent == "cancel":
        return {
            "state": "CANCELLED",
            "reply_text": "Order cancelled.",
            "basket": new_basket,
            "total_mad": sum(item["line_total_mad"] for item in new_basket),
            "question": None,
            "pending": None,
            "error": None
        }

    if intent == "repeat":
        total = sum(item["line_total_mad"] for item in new_basket)
        return {
            "state": state,
            "reply_text": f"Your basket total is {total} dirhams.",
            "basket": new_basket,
            "total_mad": total,
            "question": None,
            "pending": pending,
            "error": None
        }

    if intent == "confirm":
        if state != "REVIEW":
            return {
                "state": state,
                "reply_text": "There is nothing to confirm.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": None,
                "pending": pending,
                "error": "Cannot confirm outside of REVIEW state"
            }
        if not new_basket:
            return {
                "state": state,
                "reply_text": "Your basket is empty.",
                "basket": new_basket,
                "total_mad": 0,
                "question": None,
                "pending": pending,
                "error": "Cannot confirm empty basket"
            }
        total = sum(item["line_total_mad"] for item in new_basket)
        return {
            "state": "CONFIRMED",
            "reply_text": "Order confirmed!",
            "basket": new_basket,
            "total_mad": total,
            "question": None,
            "pending": None,
            "error": None
        }

    # Apply the requested correction and return to REVIEW.
    if intent == "change":
        if not new_basket:
            return {
                "state": "CLARIFY",
                "reply_text": "Your basket is empty. Which item would you like to change?",
                "basket": new_basket,
                "total_mad": 0,
                "question": "Which item would you like to change?",
                "pending": None,
                "error": "Cannot change empty basket"
            }

        last_item = new_basket[-1]
        p_id = parsed.get("product_id") or last_item["product_id"]
        qty = parsed.get("quantity") if parsed.get("quantity") is not None else last_item["quantity"]
        mods = parsed.get("modifier_ids") if parsed.get("modifier_ids") is not None else last_item["modifier_ids"]
        prod = menu_dict.get(p_id)
        if prod is None:
            return {
                "state": "CLARIFY",
                "reply_text": "Unknown product. Please choose an item from the menu.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Which menu item would you like?",
                "pending": None,
                "error": "Unknown product_id"
            }

        mod_dict = {item["id"]: item for item in prod.get("modifiers", [])}
        for mid in mods:
            if mid not in mod_dict:
                return {
                    "state": "CLARIFY",
                    "reply_text": f"Unknown option '{mid}'. Please try again.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": f"Which menu option did you mean instead of '{mid}'?",
                    "pending": None,
                    "error": "Unknown modifier_id"
                }

        base_price = prod["base_price_mad"]
        mod_delta = sum(mod_dict[mid]["delta_mad"] for mid in mods)
        new_basket[-1] = {
            "product_id": p_id,
            "quantity": qty,
            "modifier_ids": list(dict.fromkeys(mods)),
            "line_total_mad": qty * (base_price + mod_delta)
        }
        total_mad = sum(item["line_total_mad"] for item in new_basket)
        return {
            "state": "REVIEW",
            "reply_text": "Your change has been applied.",
            "basket": new_basket,
            "total_mad": total_mad,
            "question": None,
            "pending": None,
            "error": None
        }

    if intent == "add" and product_id:
        if product_id not in menu_dict:
            return {
                "state": "CLARIFY",
                "reply_text": "Unknown product.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Which menu item would you like?",
                "pending": None,
                "error": "Unknown product_id"
            }

        product = menu_dict[product_id]
        mod_dict = {m["id"]: m for m in product.get("modifiers", [])}

        for mid in modifier_ids:
            if mid not in mod_dict:
                return {
                    "state": "CLARIFY",
                    "reply_text": f"Unknown option '{mid}'. Please choose an available menu option.",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": f"Which menu option would you like?",
                    "pending": None,
                    "error": "Unknown modifier_id"
                }

        if quantity is None:
            missing_quantity = {
                "product_id": product_id,
                "quantity": None,
                "modifier_ids": modifier_ids,
                "missing_field": "quantity",
            }
            return {
                "state": "CLARIFY",
                "reply_text": f"How many {product['name']} would you like?",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "What quantity would you like?",
                "pending": missing_quantity,
                "error": None,
            }

        base_price = product["base_price_mad"]
        mod_delta = sum(mod_dict[mid]["delta_mad"] for mid in modifier_ids if mid in mod_dict)
        line_total = quantity * (base_price + mod_delta)

        new_item = {
            "product_id": product_id,
            "quantity": quantity,
            "modifier_ids": modifier_ids,
            "line_total_mad": line_total
        }
        new_basket.append(new_item)
        total_mad = sum(item["line_total_mad"] for item in new_basket)

        return {
            "state": "REVIEW",
            "reply_text": "Item added successfully.",
            "basket": new_basket,
            "total_mad": total_mad,
            "question": None,
            "pending": None,
            "error": None
        }

    return {
        "state": "CLARIFY",
        "reply_text": "I did not understand the request.",
        "basket": new_basket,
        "total_mad": sum(item["line_total_mad"] for item in new_basket),
        "question": "Could you clarify what you would like to do?",
        "pending": pending,
        "error": "Unclear intent"
    }