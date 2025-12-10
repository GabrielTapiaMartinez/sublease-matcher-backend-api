from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from ..adapters.sqlalchemy import models
from ..dependencies.auth import get_current_user
from ..dependencies.uow import get_uow
from ..interfaces.uow import UnitOfWork

router = APIRouter(prefix="/users", tags=["users"])

# --- Schemas ---
class UserDTO(BaseModel):
    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    show_in_swipe: bool
    email_notifications_enabled: bool

    model_config = ConfigDict(from_attributes=True)

class UserUpdateDTO(BaseModel):
    show_in_swipe: bool | None = None
    email_notifications_enabled: bool | None = None


# --- Routes ---
@router.get("/me", response_model=UserDTO)
def get_me(
    current_user: models.User = Depends(get_current_user),
):
    return current_user

@router.patch("/me", response_model=UserDTO)
def update_me(
    payload: UserUpdateDTO,
    current_user: models.User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    if payload.show_in_swipe is not None:
        current_user.show_in_swipe = payload.show_in_swipe
    
    if payload.email_notifications_enabled is not None:
        current_user.email_notifications_enabled = payload.email_notifications_enabled
        
    uow.commit() # Save changes
    
    # Refresh logic not strictly needed if ORM object updated in place, 
    # but good practice if other fields computed potentially.
    return current_user
