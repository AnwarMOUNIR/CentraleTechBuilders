"""AI interpreter adapting user requests to a structured intent dictionary."""
import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

async def interpret(
    text: str, 
    menu: List[Dict[str, Any]], 
    basket: List[Dict[str, Any]], 
    state: str, 
    pending: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Extracts structured intent from text. Fails safely to unknown intent."""
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _fallback_unknown()

    try:
        client = genai.Client(api_key=api_key)
    except Exception:
        return _fallback_unknown()
        
    prompt = f"""
    You are an AI order assistant extracting ordering intents from user text.
    
    Context:
    - Current state: {state}
    - Current basket: {json.dumps(basket)}
    - Pending question: {json.dumps(pending)}
    - Menu: {json.dumps(menu)}
    
    User text: "{text}"
    
    Return a valid JSON object matching this schema:
    {{
        "intent": "add" | "change" | "confirm" | "cancel" | "repeat" | "unknown",
        "product_id": "string ID or null",
        "quantity": integer or null,
        "modifier_ids": ["string ID", ...],
        "missing_field": "string or null"
    }}
    """
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        
        if not response.text:
            return _fallback_unknown()
            
        parsed = json.loads(response.text)
        
        return {
            "intent": parsed.get("intent", "unknown"),
            "product_id": parsed.get("product_id"),
            "quantity": parsed.get("quantity"),
            "modifier_ids": parsed.get("modifier_ids", []),
            "missing_field": parsed.get("missing_field")
        }
        
    except Exception:
        return _fallback_unknown()

def _fallback_unknown() -> Dict[str, Any]:
    """Standardized failure response."""
    return {
        "intent": "unknown",
        "product_id": None,
        "quantity": None,
        "modifier_ids": [],
        "missing_field": None
    }