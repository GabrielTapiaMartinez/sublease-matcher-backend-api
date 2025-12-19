from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DRAFT: Final = "DRAFT"
PUBLISHED: Final = "PUBLISHED"
UNLISTED: Final = "UNLISTED"
ListingStatus = Literal["DRAFT", "PUBLISHED", "UNLISTED"]


class SeekerProfileDTO(BaseModel):
    id: str | None = None
    userId: str | None = None
    bio: str | None = None
    available_from: date | None = None
    available_to: date | None = None
    budgetMin: Decimal | None = None
    budgetMax: Decimal | None = None
    city: str | None = None
    interests: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    contactEmail: str | None = None
    major: str | None = None
    hidden: bool | None = None

    model_config = ConfigDict(
        from_attributes=False,
        json_schema_extra={
            "examples": [
                {
                    "id": "seeker-1",
                    "userId": "user-1",
                    "bio": "Sophomore looking for quiet place",
                    "available_from": "2026-01-01",
                    "available_to": "2026-05-31",
                    "budgetMin": "400",
                    "budgetMax": "700",
                    "city": "Eau Claire",
                    "interests": ["coding", "swimming", "reading"],
                    "contactEmail": "s1@example.edu",
                }
            ]
        },
    )



    def to_dict(self) -> dict[str, Any]:
        interests_csv = ",".join(self.interests)
        data: dict[str, Any] = {
            "id": self.id,
            "user_id": self.userId,
            "bio": self.bio,
            "available_from": self.available_from,
            "available_to": self.available_to,
            "budget_min": self.budgetMin,
            "budget_max": self.budgetMax,
            "city": self.city,
            "interests_csv": interests_csv if interests_csv else "",
            "photos": self.photos,
            "contact_email": self.contactEmail,
            "major": self.major,
        }
        if self.hidden is not None:
            data["hidden"] = self.hidden
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SeekerProfileDTO:
        interests_raw = data.get("interests_csv") or ""
        interests = [item for item in interests_raw.split(",") if item]
        return cls(
            id=data.get("id"),
            userId=data.get("user_id"),
            bio=data.get("bio"),
            available_from=data.get("available_from"),
            available_to=data.get("available_to"),
            budgetMin=data.get("budget_min"),
            budgetMax=data.get("budget_max"),
            city=data.get("city"),
            interests=interests,
            photos=data.get("photos", []),
            contactEmail=data.get("contact_email"),
            major=data.get("major"),
            hidden=data.get("hidden"),
        )


class RoommateDTO(BaseModel):
    id: str | None = None
    name: str | None = None
    pronouns: str | None = None
    sleepingHabits: str | None = None
    studyHabits: str | None = None
    cleanliness: str | None = None
    interests: list[str] = Field(default_factory=list)
    bio: str | None = None
    major: str | None = None
    photo_url: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "roommate-1",
                    "name": "Alex",
                    "pronouns": "they/them",
                    "sleepingHabits": "early sleeper",
                    "studyHabits": "library focused",
                    "cleanliness": "tidy",
                    "interests": ["cooking", "hiking"],
                    "bio": "Graduate assistant who enjoys morning runs.",
                }
            ]
        }
    )


class HostListingDTO(BaseModel):
    id: str | None = None
    hostId: str | None = None
    title: str | None = None
    pricePerMonth: Decimal | None = None
    city: str | None = None
    state: str | None = None
    availableFrom: date | None = None
    availableTo: date | None = None
    status: ListingStatus | None = None
    contactEmail: str | None = None
    bio: str | None = None
    photos: list[str] = Field(default_factory=list)
    roommates: list[RoommateDTO] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=False,
        json_schema_extra={
            "examples": [
                {
                    "id": "listing-1",
                    "host_Id": "host-1",
                    "title": "Room near Water St",
                    "pricePerMonth": "650",
                    "city": "Eau Claire",
                    "state": "WI",
                    "availableFrom": "2025-08-15",
                    "availableTo": None,
                    "status": "PUBLISHED",
                    "contactEmail": "h1@example.edu",
                    "bio": "2BR apartment close to campus",
                    "roommates": [
                        {
                            "id": "roommate-1",
                            "name": "Alex",
                            "pronouns": "they/them",
                            "sleepingHabits": "early sleeper",
                            "studyHabits": "library focused",
                            "cleanliness": "tidy",
                            "interests": ["cooking", "hiking"],
                            "bio": "Graduate assistant who enjoys morning runs.",
                        }
                    ],
                }
            ]
        },
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "host_id": self.hostId,
            "title": self.title,
            "price_per_month": self.pricePerMonth,
            "city": self.city,
            "state": self.state,
            "available_from": self.availableFrom,
            "available_to": self.availableTo,
            "status": self.status,
            "contact_email": self.contactEmail,
            "bio": self.bio,
        }

    def to_host_dict(self, user_id: str) -> dict[str, Any]:
        return {
            "id": self.hostId,
            "user_id": user_id,
            "bio": self.bio,
            "contact_email": self.contactEmail,
        }

    def to_listing_dict(self, host_id: str) -> dict[str, Any]:
        return {
            "id": self.id,
            "host_id": host_id,
            "title": self.title,
            "price_per_month": self.pricePerMonth,
            "city": self.city,
            "state": self.state,
            "available_from": self.availableFrom,
            "available_to": self.availableTo,
            "status": self.status,
            "photos": self.photos,
            "roommates": [roommate.model_dump(exclude_none=True) for roommate in self.roommates],
        }

    # RoommatePublicDTO can stay as is

    @classmethod
    def from_parts(
        cls,
        host: Mapping[str, Any] | None,
        listing: Mapping[str, Any] | None,
    ) -> HostListingDTO:
        roommates_data = (listing or {}).get("roommates") or []
        roommates = [
            RoommateDTO(**roommate) if isinstance(roommate, Mapping) else RoommateDTO()
            for roommate in roommates_data
        ]
        return cls(
            id=(listing or {}).get("id"),
            hostId=(host or {}).get("id"),
            title=(listing or {}).get("title"),
            pricePerMonth=(listing or {}).get("price_per_month"),
            city=(listing or {}).get("city"),
            state=(listing or {}).get("state"),
            availableFrom=(listing or {}).get("available_from"),
            availableTo=(listing or {}).get("available_to"),
            status=(listing or {}).get("status"),
            contactEmail=(host or {}).get("contact_email"),
            bio=(host or {}).get("bio"),
            photos=(listing or {}).get("photos") or [],
            roommates=roommates,
        )


# RoommatePublicDTO and HostListingDTO stay as they are unless you also need to update their fields.


if not TYPE_CHECKING:
    SeekerProfileDTO.model_rebuild()
    RoommateDTO.model_rebuild()
    HostListingDTO.model_rebuild()
