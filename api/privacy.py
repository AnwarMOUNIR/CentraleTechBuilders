import re
from typing import Optional

def redact(text: Optional[str]) -> str:
    """
    Masque les numéros de téléphone et les expressions d'adresses sensibles 
    avant l'appel au modèle d'IA.
    """
    if not text:
        return ""
    
    # Masquage des numéros de téléphone
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'
    redacted = re.sub(phone_pattern, "[REDACTED]", text)
    
    # Masquage d'adresses sensibles (ex: rue, avenue, boulevard suivis de chiffres/mots)
    address_pattern = r'\b(?:rue|avenue|boulevard|bvd|av\.|quartier)\s+[a-zA-Z0-9\s,.-]{3,}\b'
    redacted = re.sub(address_pattern, "[REDACTED_ADDRESS]", redacted, flags=re.IGNORECASE)
    
    return redacted