from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..interfaces.engine import MatchEngine


class SimpleMatchEngine(MatchEngine):
    def score(self, seeker_preferences: Mapping[str, Any], listing: Mapping[str, Any]) -> float:
        if seeker_preferences.get("city") and seeker_preferences.get("city") == listing.get("city"):
            return 0.8
        return 0.5
