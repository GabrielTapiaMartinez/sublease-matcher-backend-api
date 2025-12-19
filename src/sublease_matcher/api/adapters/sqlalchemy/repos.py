from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...interfaces.errors import NotFoundError
from ...interfaces.repos import HostRepo, ListingRepo, MatchRepo, SeekerRepo, SwipeRepo
from ...interfaces.types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict
from . import models


def _csv_from_list(values: Sequence[str] | None) -> str:
    return ",".join(value for value in (values or []) if value)


def _list_from_csv(csv_value: str | None) -> list[str]:
    if not csv_value:
        return []
    return [item for item in csv_value.split(",") if item]


class SqlAlchemyUserRepo:
    """Utility repo to ensure FK rows exist for user-facing profiles."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_user(self, user_id: str, *, role: str | None = None) -> models.User:
        user = self.session.get(models.User, user_id)
        if user is None:
            user = models.User(
                id=user_id,
                email=f"{user_id}@example.edu",
            )
            self.session.add(user)
        if role:
            user.current_role = role.upper()
        return user


class SqlAlchemySeekerRepo(SeekerRepo):
    def __init__(self, session: Session, users: SqlAlchemyUserRepo) -> None:
        self.session = session
        self._users = users

    def _to_dict(self, seeker: models.SeekerProfile) -> SeekerDict:
        # Best effort to get name from user relation if loaded/available
        name = "Anonymous"
        if seeker.user:
            name = f"{seeker.user.first_name} {seeker.user.last_name or ''}".strip()
        
        photos = [p.url for p in sorted(seeker.photos, key=lambda x: x.position)] if seeker.photos else []

        return {
            "id": seeker.id,
            "user_id": seeker.user_id,
            "name": name,
            "bio": seeker.bio,
            "available_from": seeker.available_from,
            "available_to": seeker.available_to,
            "budget_min": seeker.budget_min,
            "budget_max": seeker.budget_max,
            "city": seeker.city,
            "interests_csv": seeker.interests_csv or "",
            "interests": _list_from_csv(seeker.interests_csv),
            "contact_email": seeker.contact_email,
            "major": seeker.major,
            "hidden": not bool(seeker.visible),
            "photos": photos,
        }

    def get(self, seeker_id: str) -> SeekerDict | None:
        seeker = self.session.get(models.SeekerProfile, seeker_id)
        return self._to_dict(seeker) if seeker else None

    def get_by_user(self, user_id: str) -> SeekerDict | None:
        stmt = select(models.SeekerProfile).where(models.SeekerProfile.user_id == user_id)
        seeker = self.session.scalars(stmt).first()
        return self._to_dict(seeker) if seeker else None

    def upsert(self, seeker: SeekerDict) -> SeekerDict:
        seeker_id = seeker.get("id") or f"seeker-{uuid4()}"
        db_obj = self.session.get(models.SeekerProfile, seeker_id)
        incoming_user_id = seeker.get("user_id")
        if db_obj is None:
            if not incoming_user_id:
                raise ValueError("user_id is required for seeker profile")
            self._users.ensure_user(incoming_user_id, role="SEEKER")
            db_obj = models.SeekerProfile(id=seeker_id, user_id=incoming_user_id)
            self.session.add(db_obj)
        elif incoming_user_id and incoming_user_id != db_obj.user_id:
            self._users.ensure_user(incoming_user_id, role="SEEKER")
            db_obj.user_id = incoming_user_id
        for field in (
            "bio",
            "available_from",
            "available_to",
            "budget_min",
            "budget_max",
            "city",
            "contact_email",
            "major",
        ):
            if field in seeker:
                setattr(db_obj, field, seeker.get(field))
        if "interests_csv" in seeker:
            db_obj.interests_csv = seeker.get("interests_csv") or ""
        if "photos" in seeker:
            # Clear existing and re-add
            # Note: For production, you might want more smart diffing, but this is fine for now
            db_obj.photos.clear()
            for idx, url in enumerate(seeker.get("photos") or []):
                if url: # Skip empty strings
                    db_obj.photos.append(models.SeekerPhoto(id=str(uuid4()), url=str(url), position=idx))
        if "hidden" in seeker:
            db_obj.visible = not bool(seeker.get("hidden"))
        if db_obj.visible is None:
            db_obj.visible = True
        self.session.flush()
        # Refresh to ensure relationships are accessible if needed immediately
        # self.session.refresh(db_obj) 
        return self._to_dict(db_obj)

    def queue_for_host(self, host_id: str) -> Sequence[SeekerDict]:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(models.SeekerProfile)
            .join(models.User, models.SeekerProfile.user_id == models.User.id)
            .where(
                models.SeekerProfile.visible == True,  # noqa: E712
                models.User.show_in_swipe == True,
            )
            .options(selectinload(models.SeekerProfile.user), selectinload(models.SeekerProfile.photos))
        )
        seekers = self.session.scalars(stmt).all()
        return [self._to_dict(seeker) for seeker in seekers]


class SqlAlchemyHostRepo(HostRepo):
    def __init__(self, session: Session, users: SqlAlchemyUserRepo) -> None:
        self.session = session
        self._users = users

    def _to_dict(self, host: models.HostProfile) -> HostDict:
        return {
            "id": host.id,
            "user_id": host.user_id,
            "bio": host.bio,
            "house_rules": host.house_rules,
            "contact_email": host.contact_email,
        }

    def get(self, host_id: str) -> HostDict | None:
        host = self.session.get(models.HostProfile, host_id)
        return self._to_dict(host) if host else None

    def get_by_user(self, user_id: str) -> HostDict | None:
        stmt = select(models.HostProfile).where(models.HostProfile.user_id == user_id)
        host = self.session.scalars(stmt).first()
        return self._to_dict(host) if host else None

    def upsert(self, host: HostDict) -> HostDict:
        host_id = host.get("id") or f"host-{uuid4()}"
        db_obj = self.session.get(models.HostProfile, host_id)
        incoming_user_id = host.get("user_id")
        if db_obj is None:
            if not incoming_user_id:
                raise ValueError("user_id is required for host profile")
            self._users.ensure_user(incoming_user_id, role="HOST")
            db_obj = models.HostProfile(id=host_id, user_id=incoming_user_id)
            self.session.add(db_obj)
        elif incoming_user_id and incoming_user_id != db_obj.user_id:
            self._users.ensure_user(incoming_user_id, role="HOST")
            db_obj.user_id = incoming_user_id
        for field in ("bio", "house_rules", "contact_email"):
            if field in host:
                setattr(db_obj, field, host.get(field))
        self.session.flush()
        return self._to_dict(db_obj)


class SqlAlchemyListingRepo(ListingRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_dict(self, listing: models.Listing) -> ListingDict:
        status_value = cast(Literal["DRAFT", "PUBLISHED", "UNLISTED"], listing.status)
        
        photos = [p.url for p in sorted(listing.photos, key=lambda x: x.position)] if listing.photos else []
        
        data: ListingDict = {
            "id": listing.id,
            "host_id": listing.host_id,
            "title": listing.title,
            "price_per_month": listing.price_per_month,
            "city": listing.city,
            "state": listing.state,
            "available_from": listing.available_from,
            "available_to": listing.available_to,
            "status": status_value,
            "bio": listing.host.bio if listing.host else None,
            "photos": photos,
        }
        data["roommates"] = [
            {
                "id": roommate.id,
                "name": roommate.name,
                "sleepingHabits": roommate.sleeping_habits,
                "interests": _list_from_csv(roommate.interests_csv),
                "interests_csv": roommate.interests_csv,
                "photo_url": roommate.photo_url,
                "pronouns": roommate.pronouns,
                "gender": roommate.gender,
                "studyHabits": roommate.study_habits,
                "cleanliness": roommate.cleanliness,
                "bio": roommate.bio,
                "major": roommate.major,
            }
            for roommate in listing.roommates
        ]
        return data

    def get(self, listing_id: str) -> ListingDict | None:
        listing = self.session.get(models.Listing, listing_id)
        return self._to_dict(listing) if listing else None

    def get_by_host(self, host_id: str) -> ListingDict | None:
        stmt = select(models.Listing).where(models.Listing.host_id == host_id)
        listing = self.session.scalars(stmt).first()
        return self._to_dict(listing) if listing else None

    def upsert(self, listing: ListingDict) -> ListingDict:
        listing_id = listing.get("id")
        db_obj = self.session.get(models.Listing, listing_id) if listing_id else None
        if db_obj is None and listing.get("host_id"):
            stmt = select(models.Listing).where(models.Listing.host_id == listing["host_id"])
            db_obj = self.session.scalars(stmt).first()
        if db_obj is None:
            if "host_id" not in listing:
                raise ValueError("host_id is required for listings")
            listing_id = listing_id or f"listing-{uuid4()}"
            db_obj = models.Listing(id=listing_id, host_id=listing["host_id"])
            self.session.add(db_obj)
        db_obj.host_id = listing["host_id"]
        for field in (
            "title",
            "price_per_month",
            "city",
            "state",
            "available_from",
            "available_to",
            "status",
        ):
            if field in listing:
                setattr(db_obj, field, listing.get(field))
        if "roommates" in listing:
            db_obj.roommates.clear()
            for roommate in listing.get("roommates") or []:
                interests_value = roommate.get("interests")
                if isinstance(interests_value, list):
                    interests_csv = _csv_from_list(interests_value)
                else:
                    interests_csv = roommate.get("interests_csv") or ""
                db_obj.roommates.append(
                    models.ListingRoommate(
                        id=roommate.get("id") or str(uuid4()),
                        name=roommate.get("name"),
                        sleeping_habits=roommate.get("sleepingHabits")
                        or roommate.get("sleeping_habits"),
                        interests_csv=interests_csv,
                        photo_url=roommate.get("photo_url"),
                        pronouns=roommate.get("pronouns"),
                        gender=roommate.get("gender"),
                        study_habits=roommate.get("studyHabits") or roommate.get("study_habits"),
                        cleanliness=roommate.get("cleanliness"),
                        bio=roommate.get("bio"),
                        major=roommate.get("major"),
                    )
                )
        if "photos" in listing:
            db_obj.photos.clear()
            for idx, url in enumerate(listing.get("photos") or []):
                if url:
                    db_obj.photos.append(
                        models.ListingPhoto(
                            id=str(uuid4()),
                            url=str(url),
                            position=idx
                        )
                    )
        self.session.flush()
        return self._to_dict(db_obj)

    def search(
        self,
        city: str | None = None,
        max_price: Decimal | None = None,
    ) -> Sequence[ListingDict]:
        stmt = select(models.Listing)
        if city:
            stmt = stmt.where(models.Listing.city == city)
        if max_price is not None:
            stmt = stmt.where(
                sa.and_(
                    models.Listing.price_per_month.is_not(None),
                    models.Listing.price_per_month <= max_price,
                )
            )
        listings = self.session.scalars(stmt).all()
        return [self._to_dict(listing) for listing in listings]

    def queue_for_seeker(self, seeker_id: str) -> Sequence[ListingDict]:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(models.Listing)
            .join(models.HostProfile, models.Listing.host_id == models.HostProfile.id)
            .join(models.User, models.HostProfile.user_id == models.User.id)
            .where(
                models.User.show_in_swipe == True
            )
            .options(selectinload(models.Listing.photos))
        )
        listings = self.session.scalars(stmt).all()
        return [self._to_dict(listing) for listing in listings]


class SqlAlchemyMatchRepo(MatchRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_dict(self, match: models.Match) -> MatchDict:
        status_value = cast(Literal["PENDING", "MUTUAL"], match.status)
        return {
            "id": match.id,
            "seeker_id": match.seeker_id,
            "listing_id": match.listing_id,
            "status": status_value,
            "score": float(match.score) if isinstance(match.score, Decimal) else match.score,
            "matched_at": match.matched_at,
        }

    def list_for_seeker(self, seeker_id: str) -> Sequence[MatchDict]:
        stmt = select(models.Match).where(models.Match.seeker_id == seeker_id)
        matches = self.session.scalars(stmt).all()
        return [self._to_dict(match) for match in matches]

    def list_for_host(self, host_id: str) -> Sequence[MatchDict]:
        stmt = (
            select(models.Match)
            .join(models.Listing, models.Match.listing_id == models.Listing.id)
            .where(models.Listing.host_id == host_id)
        )
        matches = self.session.scalars(stmt).all()
        return [self._to_dict(match) for match in matches]

    def upsert(
        self,
        seeker_id: str,
        listing_id: str,
        status: str,
        score: float | None,
    ) -> MatchDict:
        # Look up by unique constraint (seeker_id, listing_id) instead of constructing a composite ID
        stmt = select(models.Match).where(
            models.Match.seeker_id == seeker_id,
            models.Match.listing_id == listing_id
        )
        db_obj = self.session.scalars(stmt).first()
        
        normalized_status_value = status.upper()
        if normalized_status_value not in {"PENDING", "MUTUAL"}:
            raise ValueError("status must be PENDING or MUTUAL")
        normalized_status = cast(Literal["PENDING", "MUTUAL"], normalized_status_value)
        
        if db_obj is None:
            # For new objects, use a UUID for the ID to avoid length limits
            db_obj = models.Match(
                id=str(uuid4()),
                seeker_id=seeker_id,
                listing_id=listing_id,
                status=normalized_status,
                matched_at=datetime.utcnow() if normalized_status == "MUTUAL" else None
            )
            self.session.add(db_obj)
        else:
            # For updates, we assign the string directly.
            db_obj.status = normalized_status
            if normalized_status == "MUTUAL" and not db_obj.matched_at:
                db_obj.matched_at = datetime.utcnow()
                
        if score is None:
            db_obj.score = None
        else:
            db_obj.score = Decimal(str(score))
        
        self.session.flush()
        return self._to_dict(db_obj)


class SqlAlchemySwipeRepo(SwipeRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _seeker_for_user(self, user_id: str) -> models.SeekerProfile | None:
        stmt = select(models.SeekerProfile).where(models.SeekerProfile.user_id == user_id)
        return self.session.scalars(stmt).first()

    def _host_for_user(self, user_id: str) -> models.HostProfile | None:
        stmt = select(models.HostProfile).where(models.HostProfile.user_id == user_id)
        return self.session.scalars(stmt).first()

    def _format_swipe(
        self,
        *,
        swipe_id: str,
        user_id: str,
        target_id: str,
        decision: str,
        created_at: datetime,
    ) -> SwipeDict:
        return {
            "id": swipe_id,
            "user_id": user_id,
            "target_id": target_id,
            "decision": "like" if decision.upper() == "LIKE" else "pass",
            "created_at": created_at,
        }

    @property
    def _data(self) -> dict[str, SwipeDict]:
        data: dict[str, SwipeDict] = {}
        seeker_stmt = select(models.SeekerSwipe, models.SeekerProfile.user_id).join(
            models.SeekerProfile, models.SeekerSwipe.seeker_id == models.SeekerProfile.id
        )
        for swipe, user_id in self.session.execute(seeker_stmt):
            data[swipe.id] = self._format_swipe(
                swipe_id=swipe.id,
                user_id=user_id,
                target_id=swipe.listing_id,
                decision=swipe.decision,
                created_at=swipe.created_at or datetime.utcnow(),
            )
        host_stmt = select(models.HostSwipe, models.HostProfile.user_id).join(
            models.HostProfile, models.HostSwipe.host_id == models.HostProfile.id
        )
        for swipe, user_id in self.session.execute(host_stmt):
            data[swipe.id] = self._format_swipe(
                swipe_id=swipe.id,
                user_id=user_id,
                target_id=swipe.seeker_id,
                decision=swipe.decision,
                created_at=swipe.created_at or datetime.utcnow(),
            )
        return data

    def record_swipe(self, swiper_id: str, target_id: str, decision: str) -> SwipeDict:
        normalized = "LIKE" if decision.lower() == "like" else "PASS"
        now = datetime.utcnow()
        if target_id.startswith("listing-"):
            seeker = self._seeker_for_user(swiper_id)
            listing = self.session.get(models.Listing, target_id)
            if seeker is None or listing is None:
                raise NotFoundError("Seeker or listing not found for swipe")
            
            # Check for existing swipe
            stmt = select(models.SeekerSwipe).where(
                models.SeekerSwipe.seeker_id == seeker.id,
                models.SeekerSwipe.listing_id == listing.id
            )
            swipe = self.session.scalars(stmt).first()

            if swipe:
                swipe.decision = normalized
                swipe.created_at = now
            else:
                swipe = models.SeekerSwipe(
                    id=str(uuid4()),
                    seeker_id=seeker.id,
                    listing_id=listing.id,
                    decision=normalized,
                    created_at=now,
                )
                self.session.add(swipe)
            
            self.session.flush()
            return self._format_swipe(
                swipe_id=swipe.id,
                user_id=swiper_id,
                target_id=listing.id,
                decision=normalized,
                created_at=swipe.created_at or now,
            )
        elif target_id.startswith("seeker-"):
            host = self._host_for_user(swiper_id)
            seeker = self.session.get(models.SeekerProfile, target_id)
            if host is None or seeker is None:
                raise NotFoundError("Host or seeker not found for swipe")
            
            # Check for existing swipe
            stmt = select(models.HostSwipe).where(
                models.HostSwipe.host_id == host.id,
                models.HostSwipe.seeker_id == seeker.id
            )
            host_swipe = self.session.scalars(stmt).first()

            if host_swipe:
                host_swipe.decision = normalized
                host_swipe.created_at = now
            else:
                host_swipe = models.HostSwipe(
                    id=str(uuid4()),
                    host_id=host.id,
                    seeker_id=seeker.id,
                    decision=normalized,
                    created_at=now,
                )
                self.session.add(host_swipe)

            self.session.flush()
            return self._format_swipe(
                swipe_id=host_swipe.id,
                user_id=swiper_id,
                target_id=seeker.id,
                decision=normalized,
                created_at=host_swipe.created_at or now,
            )
        raise ValueError("target_id must reference a listing or seeker")

    def get_swipe(self, user_id: str, target_id: str) -> SwipeDict | None:
        if target_id.startswith("listing-"):
            seeker = self._seeker_for_user(user_id)
            if not seeker:
                return None
            stmt = select(models.SeekerSwipe).where(
                models.SeekerSwipe.seeker_id == seeker.id,
                models.SeekerSwipe.listing_id == target_id # target_id is listing id
            )
            swipe = self.session.scalars(stmt).first()
            if not swipe:
                return None
            return self._format_swipe(
                swipe_id=swipe.id,
                user_id=user_id,
                target_id=target_id,
                decision=swipe.decision,
                created_at=swipe.created_at or datetime.utcnow(),
            )
        elif target_id.startswith("seeker-"):
            host = self._host_for_user(user_id)
            if not host:
                return None
            stmt = select(models.HostSwipe).where(
                models.HostSwipe.host_id == host.id,
                models.HostSwipe.seeker_id == target_id # target_id is seeker id
            )
            swipe = self.session.scalars(stmt).first()
            if not swipe:
                return None
            return self._format_swipe(
                swipe_id=swipe.id,
                user_id=user_id,
                target_id=target_id,
                decision=swipe.decision,
                created_at=swipe.created_at or datetime.utcnow(),
            )
        return None

    def undo_last(self, user_id: str) -> SwipeDict | None:
        seeker = self._seeker_for_user(user_id)
        if seeker:
            stmt = (
                select(models.SeekerSwipe)
                .where(models.SeekerSwipe.seeker_id == seeker.id)
                .order_by(models.SeekerSwipe.created_at.desc())
                .limit(1)
            )
            swipe = self.session.scalars(stmt).first()
            if swipe is None:
                return None
            data = self._format_swipe(
                swipe_id=swipe.id,
                user_id=user_id,
                target_id=swipe.listing_id,
                decision=swipe.decision,
                created_at=swipe.created_at or datetime.utcnow(),
            )
            self.session.delete(swipe)
            self.session.flush()
            return data
        host = self._host_for_user(user_id)
        if host:
            host_stmt = (
                select(models.HostSwipe)
                .where(models.HostSwipe.host_id == host.id)
                .order_by(models.HostSwipe.created_at.desc())
                .limit(1)
            )
            host_swipe = self.session.scalars(host_stmt).first()
            if host_swipe is None:
                return None
            data = self._format_swipe(
                swipe_id=host_swipe.id,
                user_id=user_id,
                target_id=host_swipe.seeker_id,
                decision=host_swipe.decision,
                created_at=host_swipe.created_at or datetime.utcnow(),
            )
            self.session.delete(host_swipe)
            self.session.flush()
            return data
        return None
