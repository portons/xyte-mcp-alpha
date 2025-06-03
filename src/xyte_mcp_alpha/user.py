from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict

class UserPreferences(BaseModel):
    """Simple user preferences model."""

    preferred_devices: list[str] = Field(default_factory=list)
    default_room: str | None = None

# Example in-memory store mapping user tokens to preferences
# This is for **demo purposes only** and is not persisted.
USER_PREFERENCES: Dict[str, UserPreferences] = {
    "demo-token": UserPreferences(preferred_devices=["device1"], default_room="101"),
}


def get_preferences(user_token: str) -> UserPreferences:
    """Return preferences for the given user token or empty preferences."""
    return USER_PREFERENCES.get(user_token, UserPreferences())

