from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from ..adapters.memory_repos import InMemorySwipeRepo
from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..interfaces.errors import NotFoundError
from ..interfaces.types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict

router = APIRouter(prefix="/swipe", tags=["swipe"])
public_router = APIRouter(tags=["swipe"])


def get_user_id(request: Request) -> str:
    return request.headers.get("user_id") or "user-1"


def get_host_user_id(request: Request) -> str:
    return request.headers.get("user_id") or "user-10"


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


class ListingQueueItem(BaseModel):
    id: str
    title: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pricePerMonth: Optional[Decimal] = None
    status: Optional[Literal["DRAFT", "PUBLISHED", "UNLISTED"]] = None


class SeekerQueueItem(BaseModel):
    id: str
    bio: Optional[str] = None
    term: Optional[str] = None
    termYear: Optional[int] = None
    budgetMin: Optional[Decimal] = None
    budgetMax: Optional[Decimal] = None
    city: Optional[str] = None


class SwipeOut(BaseModel):
    id: str
    user_id: str
    target_id: str
    decision: Literal["like", "pass"]
    created_at: datetime


class UndoResponse(BaseModel):
    restored: Optional[SwipeOut] = None


class MatchOut(BaseModel):
    id: str
    seeker_id: str
    listing_id: str
    status: Literal["PENDING", "MUTUAL"]
    score: Optional[float] = None
    matched_at: Optional[datetime] = None


def _has_like(swipes: InMemorySwipeRepo, *, user_id: str, target_id: str) -> bool:
    store: Dict[str, SwipeDict] = swipes._data
    return any(
        swipe.get("user_id") == user_id
        and swipe.get("target_id") == target_id
        and swipe.get("decision") == "like"
        for swipe in store.values()
    )


def _to_listing_queue_item(listing: ListingDict) -> ListingQueueItem:
    return ListingQueueItem(
        id=listing.get("id", ""),
        title=listing.get("title"),
        city=listing.get("city"),
        state=listing.get("state"),
        pricePerMonth=listing.get("price_per_month"),
        status=listing.get("status"),
    )


def _to_seeker_queue_item(seeker: SeekerDict) -> SeekerQueueItem:
    return SeekerQueueItem(
        id=seeker.get("id", ""),
        bio=seeker.get("bio"),
        term=seeker.get("term"),
        termYear=seeker.get("term_year"),
        budgetMin=seeker.get("budget_min"),
        budgetMax=seeker.get("budget_max"),
        city=seeker.get("city"),
    )


def _to_swipe_out(swipe: SwipeDict) -> SwipeOut:
    decision = cast(Literal["like", "pass"], swipe["decision"])
    return SwipeOut(
        id=swipe["id"],
        user_id=swipe["user_id"],
        target_id=swipe["target_id"],
        decision=decision,
        created_at=swipe["created_at"],
    )


def _to_match_out(match: MatchDict) -> MatchOut:
    status = cast(Literal["PENDING", "MUTUAL"], match["status"])
    return MatchOut(
        id=match["id"],
        seeker_id=match["seeker_id"],
        listing_id=match["listing_id"],
        status=status,
        score=match.get("score"),
        matched_at=match.get("matched_at"),
    )


@router.get("/queue/seeker", response_model=List[ListingQueueItem])
def seeker_queue(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_user_id),
) -> List[ListingQueueItem]:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        raise NotFoundError("Seeker profile not found")
    listing_queue = uow.listings.queue_for_seeker(seeker["id"])
    return [_to_listing_queue_item(item) for item in listing_queue]


@router.get("/queue/host", response_model=List[SeekerQueueItem])
def host_queue(
    user_id: str = Depends(get_host_user_id),
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> List[SeekerQueueItem]:
    host = uow.hosts.get_by_user(user_id)
    if host is None or not host.get("id"):
        raise NotFoundError("Host profile not found")
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
    user_id: str = Depends(get_user_id),
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
            if host is None or listing is None or seeker is None:
                raise NotFoundError("Host, listing, or seeker not found for swipe")
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
    user_id: str = Depends(get_user_id),
) -> UndoResponse:
    restored = uow.swipes.undo_last(user_id)
    return UndoResponse(restored=_to_swipe_out(restored) if restored else None)


def _compute_matches(request: Request, uow: InMemoryUnitOfWork) -> List[MatchOut]:
    header_user = request.headers.get("user_id")
    candidate_users: List[str] = []
    if header_user:
        candidate_users.append(header_user)
    else:
        candidate_users.extend(["user-1", "user-10"])

    for user_id in candidate_users:
        seeker = uow.seekers.get_by_user(user_id)
        if seeker and seeker.get("id"):
            matches = uow.matches.list_for_seeker(seeker["id"])
            return [_to_match_out(match) for match in matches]

        host = uow.hosts.get_by_user(user_id)
        if host and host.get("id"):
            listing = uow.listings.get_by_host(host["id"])
            matches = uow.matches.list_for_host(host["id"])
            if listing and listing.get("id"):
                matches = [
                    match for match in matches if match.get("listing_id") == listing["id"]
                ]
            return [_to_match_out(match) for match in matches]
    raise NotFoundError("No seeker or host context found for user")


@router.get("/matches/me", response_model=List[MatchOut])
def my_matches(
    request: Request,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> List[MatchOut]:
    return _compute_matches(request, uow)


@public_router.get("/matches", response_model=List[MatchOut])
def matches_alias(
    request: Request,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> List[MatchOut]:
    return _compute_matches(request, uow)
