from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from decimal import Decimal
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, Request

from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..dependencies.auth import get_current_user_id
from ..interfaces.errors import ConflictError, NotFoundError, ValidationError
from ..interfaces.types import HostDict, ListingDict
from .dto import HostListingDTO
from sublease_matcher.core.errors import Validation
from sublease_matcher.core.domain.listing import Listing
from sublease_matcher.core.domain.enums import ListingStatus
from sublease_matcher.core.domain.value_objects import Money
from sublease_matcher.core.domain.roommate import RoommateProfile
from sublease_matcher.core.domain.ids import ListingId, HostId, RoommateId

router = APIRouter(prefix="/hosts/me", tags=["listings"])
public_router = APIRouter(prefix="/listings", tags=["listings"])




def _clamp_non_negative(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if value >= Decimal("0") else Decimal("0")


def _merge_dicts(
    base: Mapping[str, Any] | None,
    updates: Mapping[str, Any],
    *,
    allow_none: bool,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base or {})
    for key, value in updates.items():
        if value is None and key in {"id"}:
            continue
        if value is None and not allow_none:
            continue
        merged[key] = value
    return merged


def _require_host_listing(
    uow: InMemoryUnitOfWork,
    user_id: str,
) -> tuple[HostDict, ListingDict]:
    host = uow.hosts.get_by_user(user_id)
    if host is None:
        raise NotFoundError("Listing not found for current host")
    listing = uow.listings.get_by_host(host["id"])
    if listing is None:
        raise NotFoundError("Listing not found for current host")
    return host, listing


def _ensure_listing_owner(
    uow: InMemoryUnitOfWork,
    listing: ListingDict,
    user_id: str,
) -> HostDict:
    host = uow.hosts.get(listing.get("host_id", ""))
    if host is None:
        raise NotFoundError("Host not found for listing")
    current_host = uow.hosts.get_by_user(user_id)
    if current_host is None or current_host.get("id") != host.get("id"):
        raise NotFoundError("Listing not found")
    return host





def _persist_listing_from_dto(
    dto: HostListingDTO,
    *,
    uow: InMemoryUnitOfWork,
    user_id: str,
    existing_host: HostDict | None,
    existing_listing: ListingDict | None,
    allow_create_host: bool,
) -> HostListingDTO:
    fields_set = set(dto.model_fields_set)
    dto_copy = dto

    host_record = existing_host or uow.hosts.get_by_user(user_id)
    if host_record is None and not allow_create_host:
        raise NotFoundError("Host profile not found for current user")

    host_updates = dto_copy.to_host_dict(user_id)
    if host_record and not host_updates.get("id"):
        host_updates["id"] = host_record.get("id")
    if "bio" not in fields_set:
        host_updates.pop("bio", None)
    if "contactEmail" not in fields_set:
        host_updates.pop("contact_email", None)
    if not host_record and not host_updates.get("id"):
        host_updates.pop("id", None)

    host_payload = _merge_dicts(host_record, host_updates, allow_none=False)
    host_payload["user_id"] = user_id
    host = uow.hosts.upsert(cast(HostDict, host_payload))

    listing_updates = dto_copy.to_listing_dict(host["id"])
    field_map = {
        "title": "title",
        "pricePerMonth": "price_per_month",
        "city": "city",
        "state": "state",
        "availableFrom": "available_from",
        "availableTo": "available_to",
        "status": "status",
        "photos": "photos",
        "roommates": "roommates",
    }
    for field_name, dict_key in field_map.items():
        if field_name not in fields_set:
            if dict_key == "status" and not existing_listing:
                continue
            listing_updates.pop(dict_key, None)

    base_listing: Mapping[str, Any] | None = existing_listing
    if not existing_listing and listing_updates.get("status") is None:
        listing_updates["status"] = "DRAFT"
    if existing_listing:
        listing_updates["id"] = existing_listing.get("id")

    listing_payload = _merge_dicts(base_listing, listing_updates, allow_none=True)
    listing_payload["host_id"] = host["id"]
    listing_payload["price_per_month"] = listing_payload.get("price_per_month")
    state_value = listing_payload.get("state")
    if isinstance(state_value, str):
        listing_payload["state"] = state_value.upper()

    # Validate via Core Entity
    try:
        # Map roommates
        roommates_data = listing_payload.get("roommates", [])
        roommates = []
        for r in roommates_data:
            roommates.append(RoommateProfile(
                id=RoommateId(r.get("id") or "temp-id"),
                name=r.get("name") or "Unknown",
                sleeping_habits=r.get("sleepingHabits"),
                gender=None,
                pronouns=r.get("pronouns"),
                interests=tuple(r.get("interests", [])),
                major_minor=None
            ))

        # Map Money
        price_val = listing_payload.get("price_per_month")
        price = Money(Decimal(str(price_val))) if price_val is not None else None

        Listing(
            id=ListingId(listing_payload.get("id") or "temp-id"),
            host_id=HostId(listing_payload.get("host_id") or "temp-host-id"),
            title=listing_payload.get("title") or "",
            price_per_month=price,
            city=listing_payload.get("city") or "",
            state=listing_payload.get("state") or "",
            available_from=listing_payload.get("available_from"),
            available_to=listing_payload.get("available_to"),
            status=ListingStatus(listing_payload.get("status") or "DRAFT"),
            contact_email=listing_payload.get("contact_email"),
            bio=listing_payload.get("bio"),
            roommates=tuple(roommates),
            roommates_count=len(roommates)
        )
    except Validation as e:
        raise ValidationError(str(e)) from e
    except ValueError as e:
        # Catch value errors from Money, Enums etc
        raise ValidationError(str(e)) from e

    try:
        listing = uow.listings.upsert(cast(ListingDict, listing_payload))
        return HostListingDTO.from_parts(host, listing)
    except Validation as e:
        raise ValidationError(str(e)) from e


@router.get("/listing", response_model=HostListingDTO)
def read_listing(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    host, listing = _require_host_listing(uow, user_id)
    return HostListingDTO.from_parts(host, listing)


@router.put("/listing", response_model=HostListingDTO)
def upsert_listing(
    listing_payload: HostListingDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    existing_host = uow.hosts.get_by_user(user_id)
    existing_listing = uow.listings.get_by_host(existing_host["id"]) if existing_host else None
    return _persist_listing_from_dto(
        listing_payload,
        uow=uow,
        user_id=user_id,
        existing_host=existing_host,
        existing_listing=existing_listing,
        allow_create_host=True,
    )


@public_router.post("", response_model=HostListingDTO)
def create_listing(
    listing_payload: HostListingDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    existing_host = uow.hosts.get_by_user(user_id)
    existing_listing = uow.listings.get_by_host(existing_host["id"]) if existing_host else None
    if existing_listing is not None:
        raise ConflictError("Host already has a listing; use PUT /hosts/me/listing to update it.")
    return _persist_listing_from_dto(
        listing_payload,
        uow=uow,
        user_id=user_id,
        existing_host=existing_host,
        existing_listing=None,
        allow_create_host=True,
    )


@public_router.put("/{listing_id}", response_model=HostListingDTO)
def update_listing_by_id(
    listing_id: str,
    listing_payload: HostListingDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    listing = uow.listings.get(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found")
    host = _ensure_listing_owner(uow, listing, user_id)
    return _persist_listing_from_dto(
        listing_payload,
        uow=uow,
        user_id=user_id,
        existing_host=host,
        existing_listing=listing,
        allow_create_host=False,
    )


@public_router.get("/mine", response_model=list[HostListingDTO])
def read_my_listings(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> list[HostListingDTO]:
    host = uow.hosts.get_by_user(user_id)
    if host is None:
        return []
    listing = uow.listings.get_by_host(host["id"])
    if listing is None:
        return []
    return [HostListingDTO.from_parts(host, listing)]


@public_router.get("/{listing_id}", response_model=HostListingDTO)
def read_listing_by_id(
    listing_id: str,
    uow: InMemoryUnitOfWork = Depends(get_uow),
) -> HostListingDTO:
    listing = uow.listings.get(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found")
    host = uow.hosts.get(listing.get("host_id", ""))
    if host is None:
        raise NotFoundError("Host not found for listing")
    return HostListingDTO.from_parts(host, listing)


@public_router.patch("/{listing_id}/publish", response_model=HostListingDTO)
def toggle_listing_publication(
    listing_id: str,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    listing = uow.listings.get(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found")
    host = _ensure_listing_owner(uow, listing, user_id)
    if listing.get("status") == "PUBLISHED":
        next_status: Literal["PUBLISHED", "UNLISTED"] = "UNLISTED"
    else:
        next_status = "PUBLISHED"
    listing["status"] = next_status

    # Validate via Core Entity
    try:
        # Map roommates
        roommates_data = listing.get("roommates", [])
        roommates = []
        for r in roommates_data:
            roommates.append(RoommateProfile(
                id=RoommateId(r.get("id") or "temp-id"),
                name=r.get("name") or "Unknown",
                sleeping_habits=r.get("sleepingHabits"),
                gender=None,
                pronouns=r.get("pronouns"),
                interests=tuple(r.get("interests", [])),
                major_minor=None
            ))

        # Map Money
        price_val = listing.get("price_per_month")
        price = Money(Decimal(str(price_val))) if price_val is not None else None

        Listing(
            id=ListingId(listing.get("id") or "temp-id"),
            host_id=HostId(listing.get("host_id") or "temp-host-id"),
            title=listing.get("title") or "",
            price_per_month=price,
            city=listing.get("city") or "",
            state=listing.get("state") or "",
            available_from=listing.get("available_from"),
            available_to=listing.get("available_to"),
            status=ListingStatus(listing.get("status") or "DRAFT"),
            contact_email=listing.get("contact_email"),
            bio=listing.get("bio"),
            roommates=tuple(roommates),
            roommates_count=len(roommates)
        )
    except Validation as e:
        raise ValidationError(str(e)) from e
    except ValueError as e:
        raise ValidationError(str(e)) from e

    try:
        updated_listing = uow.listings.upsert(listing)
        return HostListingDTO.from_parts(host, updated_listing)
    except Validation as e:
        raise ValidationError(str(e)) from e
