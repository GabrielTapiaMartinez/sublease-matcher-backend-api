from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..interfaces.uow import UnitOfWork
from ..dependencies.uow import get_uow
from ..interfaces.errors import NotFoundError, ValidationError
from .dto import SeekerProfileDTO
from sublease_matcher.core.errors import Validation
from sublease_matcher.core.domain.value_objects import Money, validate_availability_dates, validate_email
from ..dependencies.auth import get_current_user_id

router = APIRouter(prefix="/seekers/me", tags=["seekers"])
profiles_router = APIRouter(prefix="/profiles", tags=["seekers"])

def _reset_inmemory_uow(uow: UnitOfWork):
    if hasattr(uow.seekers, "clear"):
        uow.seekers.clear()
    elif hasattr(uow, "clear"):
        uow.clear()

def safe_profile_from_dict(d: dict) -> SeekerProfileDTO:
    min_ = d.get("budget_min")
    max_ = d.get("budget_max")
    if min_ is not None and max_ is not None:
        try:
            min_val = Decimal(str(min_))
            max_val = Decimal(str(max_))
            if min_val < 0 or max_val < 0 or min_val > max_val:
                d.pop("budget_min", None)
                d.pop("budget_max", None)
        except Exception:
            d.pop("budget_min", None)
            d.pop("budget_max", None)
    return SeekerProfileDTO.from_dict(d)


def _clamp_non_negative(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if value >= Decimal("0") else Decimal("0")

def _read_profile(uow: UnitOfWork, user_id: str) -> SeekerProfileDTO:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None:
        raise NotFoundError("Seeker profile not found")
    return safe_profile_from_dict(seeker)

def _upsert_profile(
    profile: SeekerProfileDTO, uow: UnitOfWork, user_id: str
) -> SeekerProfileDTO:
    fields_set = profile.model_fields_set

    # Date range validation
    has_from = "available_from" in fields_set and profile.available_from is not None
    has_to = "available_to" in fields_set and profile.available_to is not None
    if has_from and has_to:
        try:
            validate_availability_dates(profile.available_from, profile.available_to)
        except ValueError as e:
            raise ValidationError(str(e)) from e

    # Budget validation
    if ("budgetMin" in fields_set and profile.budgetMin is not None) and \
       ("budgetMax" in fields_set and profile.budgetMax is not None):
        try:
            min_money = Money(profile.budgetMin)
            max_money = Money(profile.budgetMax)
            if min_money.amount > max_money.amount:
                raise ValidationError("budget_min cannot exceed budget_max.")
        except ValueError as e:
            raise ValidationError(str(e)) from e

    # Make sure we persist/update the same profile ID for the user
    existing = uow.seekers.get_by_user(user_id) or {}
    payload = dict(existing)  # Start from the existing payload if exists

    payload["user_id"] = user_id
    # Use the existing ID if present, otherwise any provided
    if "id" in fields_set and profile.id is not None:
        payload["id"] = profile.id
    elif "id" in existing:
        payload["id"] = existing["id"]

    if "bio" in fields_set:
        payload["bio"] = profile.bio
    if "available_from" in fields_set:
        payload["available_from"] = profile.available_from
    if "available_to" in fields_set:
        payload["available_to"] = profile.available_to
    if "budgetMin" in fields_set:
        payload["budget_min"] = profile.budgetMin
    if "budgetMax" in fields_set:
        payload["budget_max"] = profile.budgetMax
    if "city" in fields_set:
        payload["city"] = profile.city
    if "interests" in fields_set:
        payload["interests_csv"] = ",".join(profile.interests)
    if "photos" in fields_set:
        payload["photos"] = profile.photos
    if "major" in fields_set:
        payload["major"] = profile.major
    if "contactEmail" in fields_set:
        payload["contact_email"] = profile.contactEmail
    if "hidden" in fields_set and profile.hidden is not None:
        payload["hidden"] = profile.hidden

    saved = uow.seekers.upsert(payload)
    return safe_profile_from_dict(saved)

def _toggle_hidden(hidden: bool, uow: UnitOfWork, user_id: str) -> bool:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        raise NotFoundError("Seeker profile not found")
    seeker["hidden"] = hidden
    uow.seekers.upsert(seeker)
    return hidden

@router.get("/profile", response_model=SeekerProfileDTO)
def read_profile(
    uow: UnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _read_profile(uow, user_id)

@router.put("/profile", response_model=SeekerProfileDTO)
def upsert_profile(
    profile: SeekerProfileDTO,
    uow: UnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _upsert_profile(profile, uow, user_id)

class HideToggle(BaseModel):
    hidden: bool

class HideResponse(BaseModel):
    hidden: bool

@profiles_router.get("/me", response_model=SeekerProfileDTO)
def read_profile_alias(
    uow: UnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _read_profile(uow, user_id)

@profiles_router.put("/me", response_model=SeekerProfileDTO)
def upsert_profile_alias(
    profile: SeekerProfileDTO,
    uow: UnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _upsert_profile(profile, uow, user_id)

@profiles_router.patch("/hide", response_model=HideResponse)
def toggle_profile_hidden(
    payload: HideToggle,
    uow: UnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HideResponse:
    hidden = _toggle_hidden(payload.hidden, uow, user_id)
    return HideResponse(hidden=hidden)
