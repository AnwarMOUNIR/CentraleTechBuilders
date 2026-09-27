import re

def redact(text: str) -> str:
    """Masks potential phone numbers or sensitive strings from input text."""
    if not text:
        return ""
    # Improved pattern that handles leading '+' symbols cleanly
    phone_pattern = r'(?:\+)?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'
    redacted = re.sub(phone_pattern, "[REDACTED]", text)
    return redacted