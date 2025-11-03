from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..adapters.memory_uow import InMemoryUnitOfWork
from ..dependencies.uow import get_uow
from ..interfaces.errors import NotFoundError, ValidationError
from .dto import SeekerProfileDTO

router = APIRouter(prefix="/seekers/me", tags=["seekers"])
profiles_router = APIRouter(prefix="/profiles", tags=["seekers"])


def get_current_user_id(request: Request) -> str:
    return request.headers.get("X-Debug-User-Id") or "user-1"


def _clamp_non_negative(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if value >= Decimal("0") else Decimal("0")


def _read_profile(uow: InMemoryUnitOfWork, user_id: str) -> SeekerProfileDTO:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None:
        return SeekerProfileDTO(userId=user_id, hidden=False)
    return SeekerProfileDTO.from_dict(seeker)


def _upsert_profile(profile: SeekerProfileDTO, uow: InMemoryUnitOfWork, user_id: str) -> SeekerProfileDTO:
    fields_set = profile.model_fields_set
    if "termYear" in fields_set and profile.termYear is not None and profile.termYear < 2024:
        raise ValidationError("termYear must be >= 2024")

    existing = uow.seekers.get_by_user(user_id) or {}
    payload = dict(existing)

    payload["user_id"] = user_id
    if "id" in fields_set and profile.id is not None:
        payload["id"] = profile.id

    if "bio" in fields_set:
        payload["bio"] = profile.bio
    if "term" in fields_set:
        payload["term"] = profile.term
    if "termYear" in fields_set:
        payload["term_year"] = profile.termYear

    if "budgetMin" in fields_set:
        payload["budget_min"] = _clamp_non_negative(profile.budgetMin)
    if "budgetMax" in fields_set:
        payload["budget_max"] = _clamp_non_negative(profile.budgetMax)
    if "city" in fields_set:
        payload["city"] = profile.city
    if "interests" in fields_set:
        payload["interests_csv"] = ",".join(profile.interests)
    if "contactEmail" in fields_set:
        payload["contact_email"] = profile.contactEmail
    if "hidden" in fields_set and profile.hidden is not None:
        payload["hidden"] = profile.hidden

    saved = uow.seekers.upsert(payload)
    return SeekerProfileDTO.from_dict(saved)


def _toggle_hidden(hidden: bool, uow: InMemoryUnitOfWork, user_id: str) -> bool:
    seeker = uow.seekers.get_by_user(user_id)
    if seeker is None or not seeker.get("id"):
        raise NotFoundError("Seeker profile not found")
    seeker["hidden"] = hidden
    uow.seekers.upsert(seeker)
    return hidden


@router.get("/profile", response_model=SeekerProfileDTO)
def read_profile(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _read_profile(uow, user_id)


@router.put("/profile", response_model=SeekerProfileDTO)
def upsert_profile(
    profile: SeekerProfileDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _upsert_profile(profile, uow, user_id)


class HideToggle(BaseModel):
    hidden: bool


class HideResponse(BaseModel):
    hidden: bool


@profiles_router.get("/me", response_model=SeekerProfileDTO)
def read_profile_alias(
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _read_profile(uow, user_id)


@profiles_router.put("/me", response_model=SeekerProfileDTO)
def upsert_profile_alias(
    profile: SeekerProfileDTO,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> SeekerProfileDTO:
    return _upsert_profile(profile, uow, user_id)


@profiles_router.patch("/hide", response_model=HideResponse)
def toggle_profile_hidden(
    payload: HideToggle,
    uow: InMemoryUnitOfWork = Depends(get_uow),
    user_id: str = Depends(get_current_user_id),
) -> HideResponse:
    hidden = _toggle_hidden(payload.hidden, uow, user_id)
    return HideResponse(hidden=hidden)
