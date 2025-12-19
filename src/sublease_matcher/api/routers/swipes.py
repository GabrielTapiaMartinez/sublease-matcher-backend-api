from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Union

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from ..adapters.memory_repos import InMemorySwipeRepo
from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..dependencies.auth import get_current_user_id
from ..interfaces.errors import NotFoundError
from ..interfaces.types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict

router = APIRouter(prefix="/swipe", tags=["swipe"])
public_router = APIRouter(tags=["swipe"])




class SwipeIn(BaseModel):
    targetId: str
    decision: Literal["like", "pass"]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "targetId": "listing-1",
                    "decision": "like",
                }
            ]
        }
    )


class Roommate(BaseModel):
    id: str | None = None
    name: str | None = None
    major: str | None = None
    interests: list[str] = []
    bio: str | None = None
    photo_url: str | None = None
    sleepingHabits: str | None = None
    gender: str | None = None
    pronouns: str | None = None


class ListingQueueItem(BaseModel):
    id: str
    title: str | None = None
    city: str | None = None
    state: str | None = None
    pricePerMonth: Decimal | None = None
    status: Literal["DRAFT", "PUBLISHED", "UNLISTED"] | None = None
    availableFrom: str | None = None
    availableTo: str | None = None
    bio: str | None = None
    interests: list[str] = []
    photos: list[str] = []
    roommates: list[Roommate] = []


class SeekerQueueItem(BaseModel):
    id: str
    name: str | None = None
    bio: str | None = None
    budgetMin: Decimal | None = None
    budgetMax: Decimal | None = None
    city: str | None = None
    available_from: str | None = None
    available_to: str | None = None
    major: str | None = None
    interests: list[str] = []
    photos: list[str] = []


class SwipeOut(BaseModel):
    id: str
    user_id: str
    target_id: str
    decision: Literal["like", "pass"]
    created_at: datetime


class UndoResponse(BaseModel):
    restored: SwipeOut | None = None


class MatchOut(BaseModel):
    id: str
    seeker_id: str
    listing_id: str
    status: Literal["PENDING", "MUTUAL"]
    score: float | None = None
    matched_at: datetime | None = None
    target_profile: Union[ListingQueueItem, SeekerQueueItem, None] = None


def _has_like(swipes: InMemorySwipeRepo, *, user_id: str, target_id: str) -> bool:
    swipe = swipes.get_swipe(user_id, target_id)
    return swipe is not None and swipe.get("decision") == "like"


def _to_listing_queue_item(listing: ListingDict) -> ListingQueueItem:
    available_from = listing.get("available_from")
    available_to = listing.get("available_to")
    return ListingQueueItem(
        id=listing.get("id", ""),
        title=listing.get("title"),
        city=listing.get("city"),
        state=listing.get("state"),
        pricePerMonth=listing.get("price_per_month"),
        status=listing.get("status"),
        availableFrom=str(available_from) if available_from else None,
        availableTo=str(available_to) if available_to else None,
        bio=listing.get("bio"),
        interests=listing.get("interests", []),
        photos=listing.get("photos", []),
        roommates=[
            Roommate(
                id=r.get("id"),
                name=r.get("name"),
                major=r.get("major"),
                interests=r.get("interests", []),
                bio=r.get("bio"),
                photo_url=r.get("photo_url"),
                sleepingHabits=r.get("sleepingHabits"),
                gender=r.get("gender"),
                pronouns=r.get("pronouns"),
            )
            for r in listing.get("roommates", [])
        ]
    )


def _to_seeker_queue_item(seeker: SeekerDict) -> SeekerQueueItem:
    available_from = seeker.get("available_from")
    available_to = seeker.get("available_to")
    return SeekerQueueItem(
        id=seeker.get("id", ""),
        name=seeker.get("name"),
        bio=seeker.get("bio"),
        budgetMin=seeker.get("budget_min"),
        budgetMax=seeker.get("budget_max"),
        city=seeker.get("city"),
        available_from=str(available_from) if available_from else None,
        available_to=str(available_to) if available_to else None,
        major=seeker.get("major"),
        interests=seeker.get("interests", []),
        photos=seeker.get("photos", []),
    )


def _to_swipe_out(swipe: SwipeDict) -> SwipeOut:
    decision = swipe["decision"]
    return SwipeOut(
        id=swipe["id"],
        user_id=swipe["user_id"],
        target_id=swipe["target_id"],
        decision=decision,
        created_at=swipe["created_at"],
    )


def _to_match_out(match: MatchDict, target_profile: Union[ListingQueueItem, SeekerQueueItem, None] = None) -> MatchOut:
    status = match["status"]
    return MatchOut(
        id=match["id"],
        seeker_id=match["seeker_id"],
        listing_id=match["listing_id"],
        status=status,
        score=match.get("score"),
        matched_at=match.get("matched_at"),
        target_profile=target_profile,
    )


@router.get("/queue/seeker", response_model=list[ListingQueueItem])
def seeker_queue(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> list[ListingQueueItem]:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        # Auto-create profile if missing so the user can start swiping immediately
        seeker = uow.seekers.upsert({"user_id": user_id})
    listing_queue = uow.listings.queue_for_seeker(seeker["id"])
    return [_to_listing_queue_item(item) for item in listing_queue]


@router.get("/queue/host", response_model=list[SeekerQueueItem])
def host_queue(
    user_id: str = Depends(get_current_user_id),
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> list[SeekerQueueItem]:
    host = uow.hosts.get_by_user(user_id)
    if host is None or not host.get("id"):
        # Auto-create profile if missing
        host = uow.hosts.upsert({"user_id": user_id})
    seeker_queue = [
        seeker for seeker in uow.seekers.queue_for_host(host["id"]) if not seeker.get("hidden")
    ]
    return [_to_seeker_queue_item(item) for item in seeker_queue]


def _handle_mutual_like_for_listing(
    *,
    uow: InMemoryUnitOfWork,
    seeker: SeekerDict,
    listing: ListingDict,
) -> None:
    host = uow.hosts.get(listing.get("host_id", ""))
    if host is None:
        return
    host_user_id = host.get("user_id")
    seeker_id = seeker.get("id")
    listing_id = listing.get("id")
    if not host_user_id or not seeker_id or not listing_id:
        return
    if _has_like(uow.swipes, user_id=host_user_id, target_id=seeker_id):
        uow.matches.upsert(seeker_id, listing_id, status="MUTUAL", score=0.5)


def _handle_mutual_like_for_seeker(
    *,
    uow: InMemoryUnitOfWork,
    host: HostDict | None,
    listing: ListingDict | None,
    seeker: SeekerDict | None,
) -> None:
    if host is None or listing is None or seeker is None:
        return
    host_user_id = host.get("user_id")
    listing_id = listing.get("id")
    seeker_user_id = seeker.get("user_id")
    seeker_id = seeker.get("id")
    if not host_user_id or not listing_id or not seeker_user_id or not seeker_id:
        return
    if _has_like(uow.swipes, user_id=seeker_user_id, target_id=listing_id):
        uow.matches.upsert(seeker_id, listing_id, status="MUTUAL", score=0.5)


@router.post("/swipes", response_model=SwipeOut)
def record_swipe(
    payload: SwipeIn,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SwipeOut:
    swipe = uow.swipes.record_swipe(user_id, payload.targetId, payload.decision)

    if swipe["decision"] == "like":
        if payload.targetId.startswith("listing-"):
            seeker = uow.seekers.get_by_user(user_id)
            listing = uow.listings.get(payload.targetId)
            if seeker is None or listing is None:
                raise NotFoundError("Seeker or listing not found for swipe")
            if seeker is not None and listing is not None:
                _handle_mutual_like_for_listing(uow=uow, seeker=seeker, listing=listing)
        elif payload.targetId.startswith("seeker-"):
            host = uow.hosts.get_by_user(user_id)
            listing = uow.listings.get_by_host(host["id"]) if host and host.get("id") else None
            seeker = uow.seekers.get(payload.targetId)
            
            # Host and Seeker MUST exist, but Listing is optional corresponding to a new host
            if host is None or seeker is None:
                raise NotFoundError("Host or seeker not found for swipe")
                
            # Only try to match if a listing actually exists
            if host is not None and listing is not None and seeker is not None:
                _handle_mutual_like_for_seeker(
                    uow=uow,
                    host=host,
                    listing=listing,
                    seeker=seeker,
                )

    return _to_swipe_out(swipe)


@router.post("/swipes/undo", response_model=UndoResponse)
def undo_swipe(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> UndoResponse:
    restored = uow.swipes.undo_last(user_id)
    return UndoResponse(restored=_to_swipe_out(restored) if restored else None)


def _compute_matches(user_id: str, uow: InMemoryUnitOfWork) -> List[MatchOut]:
    seeker = uow.seekers.get_by_user(user_id)
    matches: List[MatchDict] = []
    
    # Check if user is a seeker
    if seeker and seeker.get("id"):
        matches.extend(uow.matches.list_for_seeker(seeker["id"]))

    # Check if user is a host
    host = uow.hosts.get_by_user(user_id)
    if host and host.get("id"):
        listing = uow.listings.get_by_host(host["id"])
        # Only return matches for the current listing? Or all host matches?
        # Use existing logic: list_for_host returns matches for all listings of that host (implied by host_id)
        host_matches = uow.matches.list_for_host(host["id"])
        matches.extend(host_matches)
    
    # If no matches found but profiles exist, return empty list instead of error
    # The original error "No seeker or host context found" implies the user has NO profile at all.
    # We should return empty list if profiles exist but no matches.
    # If NO profile exists, empty list is also probably better than error for "my matches".
    
    results: List[MatchOut] = []
    
    for match in matches:
        target_profile = None
        if seeker and seeker.get("id"):
            # User is Seeker, target is Listing
            listing = uow.listings.get(match["listing_id"])
            if listing:
                target_profile = _to_listing_queue_item(listing)
        elif host and host.get("id"):
            # User is Host, target is Seeker
            match_seeker = uow.seekers.get(match["seeker_id"])
            if match_seeker:
                target_profile = _to_seeker_queue_item(match_seeker)
        
        results.append(_to_match_out(match, target_profile))

    return results


@router.get("/matches/me", response_model=list[MatchOut])
def my_matches(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> list[MatchOut]:
    return _compute_matches(user_id, uow)


@public_router.get("/matches", response_model=list[MatchOut])
def matches_alias(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> list[MatchOut]:
    return _compute_matches(user_id, uow)
