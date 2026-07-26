import re
import uuid
from typing import Any, Optional


def is_valid_uuid(val: Any) -> bool:
    """
    Checks if a given string or object is a valid UUID v4 format.
    """
    if isinstance(val, uuid.UUID):
        return True
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def is_valid_email(email: str) -> bool:
    """
    Validates email format using standard regex pattern.
    """
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def sanitize_string(text: Optional[str]) -> Optional[str]:
    """
    Strips leading and trailing whitespace from string input.
    """
    if text is None:
        return None
    return text.strip()
