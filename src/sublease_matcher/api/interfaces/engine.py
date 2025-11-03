from __future__ import annotations

from typing import Any, Mapping, Protocol


class MatchEngine(Protocol):
    def score(self, seeker_preferences: Mapping[str, Any], listing: Mapping[str, Any]) -> float: ...
