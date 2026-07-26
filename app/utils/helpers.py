from datetime import datetime, timezone


def get_current_utc_time() -> datetime:
    """
    Returns current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)
