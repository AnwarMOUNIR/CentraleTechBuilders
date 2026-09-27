import re
from typing import Optional

def redact(text: Optional[str]) -> str:
    """
    Fully redact phone numbers, including the leading plus sign, and
    sensitive address phrases before sending text to the model.
    """
    if not text:
        return ""
    
    # Capture the full phone number, including its optional leading plus sign.
    phone_pattern = r'\+?\d{1,4}(?:[-.\s]?\d){7,}\b'
    redacted = re.sub(phone_pattern, "[REDACTED]", text)
    
    address_pattern = r'\b(?:street|st\.|avenue|ave\.|boulevard|blvd\.|road|rd\.|neighborhood)\s+[a-zA-Z0-9\s,.-]{3,}\b'
    redacted = re.sub(address_pattern, "[REDACTED_ADDRESS]", redacted, flags=re.IGNORECASE)
    
    return redacted