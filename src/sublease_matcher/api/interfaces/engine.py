from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class MatchEngine(Protocol):
    def score(self, seeker_preferences: Mapping[str, Any], listing: Mapping[str, Any]) -> float: ...
