from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..interfaces.errors import ConflictError, NotFoundError
from .dto import HostListingDTO

router = APIRouter(prefix="/hosts/me", tags=["listings"])
public_router = APIRouter(prefix="/listings", tags=["listings"])


def get_current_user_id(request: Request) -> str:
    return request.headers.get("X-Debug-User-Id") or "user-10"


def _clamp_non_negative(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if value >= Decimal("0") else Decimal("0")


def _merge_dicts(base: Dict[str, Any], updates: Dict[str, Any], *, allow_none: bool) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if value is None and key in {"id"}:
            continue
        if value is None and not allow_none:
            continue
        merged[key] = value
    return merged


@router.get("/listing", response_model=HostListingDTO)
def read_listing(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    host = uow.hosts.get_by_user(user_id)
    listing = uow.listings.get_by_host(host["id"]) if host else None
    return HostListingDTO.from_parts(host, listing)


@router.put("/listing", response_model=HostListingDTO)
def upsert_listing(
    listing_payload: HostListingDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    fields_set = listing_payload.model_fields_set
    price = _clamp_non_negative(listing_payload.pricePerMonth) if "pricePerMonth" in fields_set else None
    dto = listing_payload.model_copy(update={"pricePerMonth": price})

    existing_host = uow.hosts.get_by_user(user_id)
    host_updates = dto.to_host_dict(user_id)
    if host_updates.get("id") is None and existing_host is not None:
        host_updates["id"] = existing_host.get("id")
    elif host_updates.get("id") is None:
        host_updates.pop("id", None)

    if "bio" not in fields_set:
        host_updates.pop("bio", None)
    if "contactEmail" not in fields_set:
        host_updates.pop("contact_email", None)
    host_payload = _merge_dicts(existing_host or {}, host_updates, allow_none=False)
    host_payload["user_id"] = user_id
    host = uow.hosts.upsert(host_payload)

    existing_listing = uow.listings.get_by_host(host["id"])
    listing_updates = dto.to_listing_dict(host["id"])
    field_map = {
        "title": "title",
        "pricePerMonth": "price_per_month",
        "city": "city",
        "state": "state",
        "availableFrom": "available_from",
        "availableTo": "available_to",
        "status": "status",
        "roommates": "roommates",
    }
    for field_name, dict_key in field_map.items():
        if field_name not in fields_set and dict_key != "status":
            listing_updates.pop(dict_key, None)
    if "status" not in fields_set:
        listing_updates.pop("status", None)
    if "pricePerMonth" in fields_set:
        listing_updates["price_per_month"] = price
    if existing_listing:
        listing_updates["id"] = existing_listing.get("id")
        listing_payload_data = _merge_dicts(existing_listing, listing_updates, allow_none=True)
    else:
        if listing_updates.get("status") is None:
            listing_updates["status"] = "DRAFT"
        listing_payload_data = listing_updates
    listing_payload_data["host_id"] = host["id"]

    listing = uow.listings.upsert(listing_payload_data)
    return HostListingDTO.from_parts(host, listing)


class PublishPayload(BaseModel):
    status: Literal["PUBLISHED", "UNLISTED"]


class PublishResponse(BaseModel):
    id: str
    status: Literal["PUBLISHED", "UNLISTED"]


@public_router.get("/mine", response_model=HostListingDTO)
def read_my_listing(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HostListingDTO:
    return read_listing(uow=uow, user_id=user_id)


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


@public_router.patch("/{listing_id}/publish", response_model=PublishResponse)
def publish_listing(
    listing_id: str,
    payload: PublishPayload,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> PublishResponse:
    listing = uow.listings.get(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found")
    host = uow.hosts.get(listing.get("host_id", ""))
    if host is None or not host.get("id"):
        raise NotFoundError("Host not found for listing")
    current_host = uow.hosts.get_by_user(user_id)
    if current_host is None or current_host.get("id") != host.get("id"):
        raise ConflictError("Listing does not belong to the current host")
    listing["status"] = payload.status
    updated = uow.listings.upsert(listing)
    return PublishResponse(id=updated["id"], status=payload.status)
