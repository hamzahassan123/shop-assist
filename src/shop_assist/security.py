import re


_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CREDIT_CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)


def sanitize_pii(text: str) -> str:
    """Replace common email, credit-card, and phone-number patterns."""
    sanitized = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    sanitized = _CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", sanitized)
    return _PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
