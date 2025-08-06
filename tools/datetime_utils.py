"""DateTime utilities for the application.

Centralizes timezone-related functionality to avoid code duplication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

import pytz

# Warsaw timezone – centralized definition
WARSAW_TZ: Final = pytz.timezone("Europe/Warsaw")


def now_warsaw() -> datetime:
    """Return current naive datetime in Europe/Warsaw timezone."""
    return datetime.now(timezone.utc).astimezone(WARSAW_TZ).replace(tzinfo=None)
