"""Mock AI interpreter for offline tests and local development."""
from typing import Any, Dict, List, Optional

async def interpret(
    text: str, 
    menu: List[Dict[str, Any]], 
    basket: List[Dict[str, Any]], 
    state: str, 
    pending: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Returns predictable dicts for offline tests based on keywords."""
    normalized = text.casefold().strip()

    if "café" in normalized or "coffee" in normalized:
        return {
            "intent": "add",
            "product_id": "coffee",
            "quantity": 1,
            "modifier_ids": ["large", "no_sugar"] if "grand" in normalized else [],
            "missing_field": None
        }
    
    if "change" in normalized or "modifier" in normalized:
        return {
            "intent": "change",
            "product_id": None,
            "quantity": None,
            "modifier_ids": [],
            "missing_field": None
        }
    
    if "confirm" in normalized or "oui" in normalized:
        return {
            "intent": "confirm",
            "product_id": None,
            "quantity": None,
            "modifier_ids": [],
            "missing_field": None
        }
        
    if "annul" in normalized or "cancel" in normalized:
        return {
            "intent": "cancel",
            "product_id": None,
            "quantity": None,
            "modifier_ids": [],
            "missing_field": None
        }

    return {
        "intent": "unknown",
        "product_id": None,
        "quantity": None,
        "modifier_ids": [],
        "missing_field": None
    }