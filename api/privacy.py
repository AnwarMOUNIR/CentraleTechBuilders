import re
from typing import Optional

def redact(text: Optional[str]) -> str:
    """
    Masque complètement les numéros de téléphone (y compris le signe '+')
    et les expressions d'adresses sensibles avant l'appel au modèle.
    """
    if not text:
        return ""
    
    # Pattern strict pour capturer le '+' et le numéro entier sans laisser de résidu
    phone_pattern = r'\+?\d{1,4}(?:[-.\s]?\d){7,}\b'
    redacted = re.sub(phone_pattern, "[REDACTED]", text)
    
    address_pattern = r'\b(?:rue|avenue|boulevard|bvd|av\.|quartier)\s+[a-zA-Z0-9\s,.-]{3,}\b'
    redacted = re.sub(address_pattern, "[REDACTED_ADDRESS]", redacted, flags=re.IGNORECASE)
    
    return redacted