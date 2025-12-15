from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, List, Union

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from ..adapters.memory_repos import InMemorySwipeRepo
from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..interfaces.errors import NotFoundError
from ..interfaces.types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict

router = APIRouter(prefix="/swipe", tags=["swipe"])
public_router = APIRouter(tags=["swipe"])

# --- HELPERS ---
def get_user_id(request: Request) -> str:
    return request.headers.get("X-Debug-User-Id") or "user-1"

def get_host_user_id(request: Request) -> str:
    return request.headers.get("X-Debug-User-Id") or "user-10"

def _has_like(swipes: InMemorySwipeRepo, *, user_id: str, target_id: str) -> bool:
    store: dict[str, SwipeDict] = swipes._data
    return any(
        swipe.get("user_id") == user_id
        and swipe.get("target_id") == target_id
        and swipe.get("decision") == "like"
        for swipe in store.values()
    )

# --- MODELS ---

class SwipeIn(BaseModel):
    targetId: str
    decision: Literal["like", "pass"]
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"targetId": "listing-1", "decision": "like"}]}
    )

class ListingQueueItem(BaseModel):
    id: str
    title: str | None = None
    city: str | None = None
    state: str | None = None
    pricePerMonth: Decimal | None = None
    status: Literal["DRAFT", "PUBLISHED", "UNLISTED"] | None = None
    availableFrom: str | None = None
    availableTo: str | None = None
    photos: List[str] = [] 

class SeekerQueueItem(BaseModel):
    id: str
    name: str | None = "Student" # Placeholder until SeekerProfile stores name
    age: int | None = None
    bio: str | None = None
    budgetMin: Decimal | None = None
    budgetMax: Decimal | None = None
    city: str | None = None
    available_from: str | None = None
    available_to: str | None = None
    photos: List[str] = []

# This allows the field to hold either a Listing or a Seeker profile
TargetProfile = Union[ListingQueueItem, SeekerQueueItem]

class MatchOut(BaseModel):
    id: str
    seeker_id: str
    listing_id: str
    status: Literal["PENDING", "MUTUAL"]
    score: float | None = None
    matched_at: datetime | None = None
    target_profile: TargetProfile | None = None
    contact_email: str | None = None  # <--- Contact info
    contact_phone: str | None = None


class SwipeOut(BaseModel):
    id: str
    user_id: str
    target_id: str
    decision: Literal["like", "pass"]
    created_at: datetime


class UndoResponse(BaseModel):
    restored: SwipeOut | None = None


# --- CONVERTERS ---

def _to_listing_queue_item(listing: ListingDict) -> ListingQueueItem:
    available_from = listing.get("available_from")
    available_to = listing.get("available_to")
    # Retrieve photos if available, else default
    photos = listing.get("photos", []) 
    if not photos:
        photos = ["/House1.jpg"]

    return ListingQueueItem(
        id=listing.get("id", ""),
        title=listing.get("title"),
        city=listing.get("city"),
        state=listing.get("state"),
        pricePerMonth=listing.get("price_per_month"),
        status=listing.get("status"),
        availableFrom=str(available_from) if available_from else None,
        availableTo=str(available_to) if available_to else None,
        photos=photos
    )


def _to_seeker_queue_item(seeker: SeekerDict, name: str | None = None) -> SeekerQueueItem:
    available_from = seeker.get("available_from")
    available_to = seeker.get("available_to")
    # Retrieve photos if available, else default
    photos = seeker.get("photos", [])
    if not photos:
        photos = ["/profile-1.jpg"]

    return SeekerQueueItem(
        id=seeker.get("id", ""),
        name=name or "Student",
        age=seeker.get("age"),
        bio=seeker.get("bio"),
        budgetMin=seeker.get("budget_min"),
        budgetMax=seeker.get("budget_max"),
        city=seeker.get("city"),
        available_from=str(available_from) if available_from else None,
        available_to=str(available_to) if available_to else None,
        photos=photos
    )


def _to_match_out(match: MatchDict) -> MatchOut:
    status = match["status"]
    return MatchOut(
        id=match["id"],
        seeker_id=match["seeker_id"],
        listing_id=match["listing_id"],
        status=status,
        score=match.get("score"),
        matched_at=match.get("matched_at"),
        target_profile=None,
        contact_email=None,
        contact_phone=None
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


# --- ROUTES ---

@router.get("/queue/seeker", response_model=list[ListingQueueItem])
def seeker_queue(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_user_id),
) -> list[ListingQueueItem]:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        raise NotFoundError("Seeker profile not found")
    listing_queue = uow.listings.queue_for_seeker(seeker["id"])
    return [_to_listing_queue_item(item) for item in listing_queue]


@router.get("/queue/host", response_model=list[SeekerQueueItem])
def host_queue(
    user_id: str = Depends(get_host_user_id),
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> list[SeekerQueueItem]:
    host = uow.hosts.get_by_user(user_id)
    if host is None or not host.get("id"):
        raise NotFoundError("Host profile not found")
    seeker_queue = [
        seeker for seeker in uow.seekers.queue_for_host(host["id"]) if not seeker.get("hidden")
    ]
    return [_to_seeker_queue_item(item) for item in seeker_queue]


@router.post("/swipes", response_model=SwipeOut)
def record_swipe(
    payload: SwipeIn,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_user_id),
) -> SwipeOut:
    swipe = uow.swipes.record_swipe(user_id, payload.targetId, payload.decision)

    if swipe["decision"] == "like":
        if payload.targetId.startswith("listing-"):
            seeker = uow.seekers.get_by_user(user_id)
            listing = uow.listings.get(payload.targetId)
            if seeker and listing:
                 host = uow.hosts.get(listing.get("host_id", ""))
                 if host: 
                     host_uid = host.get("user_id", "")
                     seeker_id = seeker.get("id", "")
                     if _has_like(uow.swipes, user_id=host_uid, target_id=seeker_id):
                         uow.matches.upsert(seeker_id, listing["id"], status="MUTUAL", score=0.5)
                         
        elif payload.targetId.startswith("seeker-"):
            host = uow.hosts.get_by_user(user_id)
            seeker = uow.seekers.get(payload.targetId)
            if host and seeker:
                listing = uow.listings.get_by_host(host["id"])
                if listing:
                    seeker_uid = seeker.get("user_id", "")
                    if _has_like(uow.swipes, user_id=seeker_uid, target_id=listing["id"]):
                        uow.matches.upsert(seeker["id"], listing["id"], status="MUTUAL", score=0.5)

    return _to_swipe_out(swipe)


@router.post("/swipes/undo", response_model=UndoResponse)
def undo_swipe(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_user_id),
) -> UndoResponse:
    restored = uow.swipes.undo_last(user_id)
    return UndoResponse(restored=_to_swipe_out(restored) if restored else None)


def _compute_matches(request: Request, uow: InMemoryUnitOfWork) -> List[MatchOut]:
    header_user = request.headers.get("X-Debug-User-Id")
    candidate_users: List[str] = []
    if header_user:
        candidate_users.append(header_user)
    else:
        # Fallback for generic dev access
        candidate_users.extend(["user-1", "user-10"])

    results = []

    for user_id in candidate_users:
        # 1. Check if User is a Seeker
        seeker = uow.seekers.get_by_user(user_id)
        if seeker and seeker.get("id"):
            matches = uow.matches.list_for_seeker(seeker["id"])
            for m in matches:
                out = _to_match_out(m)
                # Hydrate with Listing Info
                listing = uow.listings.get(m["listing_id"])
                if listing:
                    out.target_profile = _to_listing_queue_item(listing)
                    
                    # Fetch Host Contact Info
                    host = uow.hosts.get(listing.get("host_id", ""))
                    if host:
                        out.contact_email = host.get("contact_email")
                        out.contact_phone = host.get("contact_phone")

                results.append(out)
            return results

        # 2. Check if User is a Host
        host = uow.hosts.get_by_user(user_id)
        if host and host.get("id"):
            matches = uow.matches.list_for_host(host["id"])
            # In a real DB, repo would filter for us. 
            # In memory, we iterate.
            for m in matches:
                # Filter: Ensure this match is for one of my listings
                listing = uow.listings.get(m["listing_id"])
                if not listing or listing.get("host_id") != host["id"]:
                    continue

                out = _to_match_out(m)
                # Hydrate with Seeker Info
                # Hydrate with Seeker Info
                s_profile = uow.seekers.get(m["seeker_id"])
                if s_profile:
                    s_name = s_profile.get("name") or "Student"
                    out.target_profile = _to_seeker_queue_item(s_profile, name=s_name)
                    out.contact_email = s_profile.get("contact_email")
                    out.contact_phone = s_profile.get("contact_phone")

                results.append(out)
            return results

    raise NotFoundError("No seeker or host context found for user")

@router.get("/matches/me", response_model=list[MatchOut])
def my_matches(
    request: Request,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> list[MatchOut]:
    return _compute_matches(request, uow)

@public_router.get("/matches", response_model=list[MatchOut])
def matches_alias(
    request: Request,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> list[MatchOut]:
    return _compute_matches(request, uow)