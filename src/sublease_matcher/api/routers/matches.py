"""
Matches router - dedicated endpoints for match operations.

Provides:
- GET /matches - Alias to /swipe/matches/me
- GET /matches/recommendations - Recommendation queue for seekers
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..dependencies.auth import get_current_user_id
from ..interfaces.errors import NotFoundError
from ..interfaces.types import ListingDict, MatchDict
from .swipes import (
    ListingQueueItem,
    MatchOut,
    _compute_matches,
    _to_listing_queue_item,
    _to_match_out,
)

router = APIRouter(prefix="/matches", tags=["matches"])


class RecommendationItem(BaseModel):
    """A recommendation with listing preview data."""

    listing: ListingQueueItem
    score: float | None = None
    reason: str | None = None


@router.get("", response_model=list[MatchOut])
def matches_surface(
    request: Request,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> list[MatchOut]:
    """
    Get mutual matches for the user.
    
    Alias to /swipe/matches/me for compatibility.
    """
    return _compute_matches(request, uow)


@router.get("/recommendations", response_model=list[RecommendationItem])
def get_recommendations(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
    limit: int = 20,
) -> list[RecommendationItem]:
    """
    Get personalized listing recommendations for a seeker.
    
    This mirrors the seeker queue preview but with additional metadata:
    - Listings are ranked by compatibility score
    - Excludes already-swiped listings
    - Includes score and optional reason for the recommendation
    
    Query Parameters:
    - limit: Maximum number of recommendations to return (default: 20)
    """
    # Get the seeker profile for the current user
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        raise NotFoundError("Seeker profile not found")
    
    # Get the listing queue (already filtered and scored)
    listing_queue = uow.listings.queue_for_seeker(seeker["id"])
    
    # Convert to recommendations with score information
    recommendations: list[RecommendationItem] = []
    
    for listing in listing_queue[:limit]:
        # Calculate score for this listing
        score = _calculate_recommendation_score(seeker, listing)
        
        # Generate reason text
        reason = _generate_recommendation_reason(seeker, listing, score)
        
        recommendations.append(
            RecommendationItem(
                listing=_to_listing_queue_item(listing),
                score=score,
                reason=reason,
            )
        )
    
    return recommendations


def _calculate_recommendation_score(
    seeker: dict, 
    listing: ListingDict
) -> float:
    """
    Calculate a recommendation score between 0.0 and 1.0.
    
    Scoring factors:
    - City match: 0.5 points
    - Budget fit: 0.5 points (with decay for prices over budget)
    """
    score = 0.0
    
    # City match (0.5 points)
    seeker_city = (seeker.get("city") or "").strip().lower()
    listing_city = (listing.get("city") or "").strip().lower()
    
    if seeker_city and listing_city and seeker_city == listing_city:
        score += 0.5
    
    # Budget fit (0.5 points max)
    budget_max = seeker.get("budget_max")
    price = listing.get("price_per_month")
    
    if budget_max and price:
        if price <= budget_max:
            # Perfect fit
            score += 0.5
        else:
            # Decay: lose 0.1 points per $100 over budget
            overage = float(price - budget_max)
            penalty = (overage / 100.0) * 0.1
            budget_score = max(0.0, 0.5 - penalty)
            score += budget_score
    elif not price or not budget_max:
        # If missing data, be optimistic
        score += 0.5
    
    return round(score, 2)


def _generate_recommendation_reason(
    seeker: dict,
    listing: ListingDict,
    score: float,
) -> str:
    """Generate a human-readable reason for the recommendation."""
    reasons: list[str] = []
    
    # City match
    seeker_city = (seeker.get("city") or "").strip().lower()
    listing_city = (listing.get("city") or "").strip().lower()
    
    if seeker_city and listing_city and seeker_city == listing_city:
        reasons.append(f"in {listing.get('city')}")
    
    # Budget fit
    budget_max = seeker.get("budget_max")
    price = listing.get("price_per_month")
    
    if budget_max and price:
        if price <= budget_max:
            reasons.append("within budget")
        else:
            overage = float(price - budget_max)
            reasons.append(f"${overage:.0f} over budget")
    
    # Availability overlap (simplified check)
    seeker_from = seeker.get("available_from")
    seeker_to = seeker.get("available_to")
    listing_from = listing.get("available_from")
    listing_to = listing.get("available_to")
    
    if all([seeker_from, listing_from]):
        reasons.append("available dates align")
    
    if not reasons:
        return "matches your search"
    
    return ", ".join(reasons)