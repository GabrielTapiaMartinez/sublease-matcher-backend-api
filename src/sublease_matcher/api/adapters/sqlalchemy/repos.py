from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from ...interfaces.repos import HostRepo, ListingRepo, MatchRepo, SeekerRepo, SwipeRepo
from ...interfaces.types import (
    HostDict,
    ListingDict,
    MatchDict,
    RoommateDict,
    SeekerDict,
    SwipeDict,
)
from .models import (
    HostProfile,
    HostSwipe,
    Listing,
    ListingRoommate,
    Match,
    SeekerProfile,
    SeekerSwipe,
    User,
)


def _default_email(user_id: str) -> str:
    return f"{user_id}@example.local"


def _ensure_user(session: Session, user_id: str, *, email: str | None, role: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email or _default_email(user_id),
            first_name=None,
            last_name=None,
            current_role=role,
            email_notifications_enabled=True,
            show_in_swipe=True,
        )
        session.add(user)
    else:
        if email and user.email != email:
            user.email = email
        if role and user.current_role != role:
            user.current_role = role
    return user


def _csv_to_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(",") if item]


def _list_to_csv(values: list[str] | None) -> str:
    if not values:
        return ""
    return ",".join(item for item in values if item)


def _roommate_from_dict(listing_id: str, roommate: RoommateDict) -> ListingRoommate:
    return ListingRoommate(
        id=roommate.get("id") or str(uuid4()),
        listing_id=listing_id,
        name=roommate.get("name"),
        sleeping_habits=roommate.get("sleepingHabits"),
        interests_csv=_list_to_csv(roommate.get("interests")),
        photo_url=None,
        pronouns=roommate.get("pronouns"),
        gender=None,
        study_habits=roommate.get("studyHabits"),
        cleanliness=roommate.get("cleanliness"),
        bio=roommate.get("bio"),
    )


def _roommate_to_dict(roommate: ListingRoommate) -> RoommateDict:
    return RoommateDict(
        id=roommate.id,
        name=roommate.name,
        pronouns=roommate.pronouns,
        sleepingHabits=roommate.sleeping_habits,
        studyHabits=roommate.study_habits,
        cleanliness=roommate.cleanliness,
        interests=_csv_to_list(roommate.interests_csv),
        bio=roommate.bio,
    )


class SqlAlchemySeekerRepo(SeekerRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_dict(self, profile: SeekerProfile) -> SeekerDict:
        data: SeekerDict = {
            "id": profile.id,
            "user_id": profile.user_id,
            "bio": profile.bio,
            "term": profile.term,
            "term_year": profile.term_year,
            "budget_min": profile.budget_min,
            "budget_max": profile.budget_max,
            "city": profile.city,
            "interests_csv": profile.interests_csv or "",
            "contact_email": profile.contact_email,
            "hidden": not profile.visible,
        }
        return data

    def get(self, seeker_id: str) -> SeekerDict | None:
        profile = self.session.get(SeekerProfile, seeker_id)
        if profile is None:
            return None
        return self._to_dict(profile)

    def get_by_user(self, user_id: str) -> SeekerDict | None:
        profile = self.session.scalar(
            select(SeekerProfile).where(SeekerProfile.user_id == user_id)
        )
        if profile is None:
            return None
        return self._to_dict(profile)

    def upsert(self, seeker: SeekerDict) -> SeekerDict:
        user_id = seeker.get("user_id")
        if not user_id:
            raise ValueError("user_id is required to upsert seeker profiles")
        profile = None
        seeker_id = seeker.get("id")
        if seeker_id:
            profile = self.session.get(SeekerProfile, seeker_id)
        if profile is None:
            profile = self.session.scalar(
                select(SeekerProfile).where(SeekerProfile.user_id == user_id)
            )
        if profile is None:
            profile = SeekerProfile(
                id=seeker_id or str(uuid4()),
                user_id=user_id,
                visible=not seeker.get("hidden", False),
            )
            self.session.add(profile)

        _ensure_user(self.session, user_id, email=seeker.get("contact_email"), role="SEEKER")

        if "bio" in seeker:
            profile.bio = seeker.get("bio")
        if "term" in seeker:
            profile.term = seeker.get("term")
        if "term_year" in seeker:
            profile.term_year = seeker.get("term_year")
        if "budget_min" in seeker:
            profile.budget_min = seeker.get("budget_min")
        if "budget_max" in seeker:
            profile.budget_max = seeker.get("budget_max")
        if "city" in seeker:
            profile.city = seeker.get("city")
        if "interests_csv" in seeker:
            profile.interests_csv = seeker.get("interests_csv") or ""
        if "contact_email" in seeker:
            profile.contact_email = seeker.get("contact_email")
        if "hidden" in seeker:
            hidden = bool(seeker.get("hidden"))
            profile.visible = not hidden

        return self._to_dict(profile)

    def queue_for_host(self, host_id: str) -> Sequence[SeekerDict]:
        del host_id  # host_id filtering belongs in higher layers
        rows = self.session.scalars(select(SeekerProfile)).all()
        return [self._to_dict(row) for row in rows]

    @property
    def _data(self) -> dict[str, SeekerDict]:
        rows = self.session.scalars(select(SeekerProfile)).all()
        return {row.id: self._to_dict(row) for row in rows}


class SqlAlchemyHostRepo(HostRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_dict(self, host: HostProfile) -> HostDict:
        return HostDict(
            id=host.id,
            user_id=host.user_id,
            bio=host.bio,
            house_rules=host.house_rules,
            contact_email=host.contact_email,
        )

    def get(self, host_id: str) -> HostDict | None:
        host = self.session.get(HostProfile, host_id)
        if host is None:
            return None
        return self._to_dict(host)

    def get_by_user(self, user_id: str) -> HostDict | None:
        host = self.session.scalar(select(HostProfile).where(HostProfile.user_id == user_id))
        if host is None:
            return None
        return self._to_dict(host)

    def upsert(self, host: HostDict) -> HostDict:
        user_id = host.get("user_id")
        if not user_id:
            raise ValueError("user_id is required to upsert host profiles")
        profile = None
        host_id = host.get("id")
        if host_id:
            profile = self.session.get(HostProfile, host_id)
        if profile is None:
            profile = self.session.scalar(select(HostProfile).where(HostProfile.user_id == user_id))
        if profile is None:
            profile = HostProfile(
                id=host_id or str(uuid4()),
                user_id=user_id,
                visible=True,
            )
            self.session.add(profile)

        _ensure_user(self.session, user_id, email=host.get("contact_email"), role="HOST")

        if "bio" in host:
            profile.bio = host.get("bio")
        if "house_rules" in host:
            profile.house_rules = host.get("house_rules")
        if "contact_email" in host:
            profile.contact_email = host.get("contact_email")

        return self._to_dict(profile)

    @property
    def _data(self) -> dict[str, HostDict]:
        rows = self.session.scalars(select(HostProfile)).all()
        return {row.id: self._to_dict(row) for row in rows}


class SqlAlchemyListingRepo(ListingRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _select_listing(self) -> Select[tuple[Listing]]:
        return select(Listing).options(joinedload(Listing.roommates))

    def _to_dict(self, listing: Listing) -> ListingDict:
        roommates = [_roommate_to_dict(roommate) for roommate in listing.roommates]
        data: ListingDict = ListingDict(
            id=listing.id,
            host_id=listing.host_id,
            title=listing.title,
            price_per_month=listing.price_per_month,
            city=listing.city,
            state=listing.state,
            available_from=listing.available_from,
            available_to=listing.available_to,
            status=listing.status,
            roommates=roommates,
        )
        return data

    def _get_listing(self, listing_id: str) -> Listing | None:
        return self.session.scalar(self._select_listing().where(Listing.id == listing_id))

    def get(self, listing_id: str) -> ListingDict | None:
        listing = self._get_listing(listing_id)
        if listing is None:
            return None
        return self._to_dict(listing)

    def get_by_host(self, host_id: str) -> ListingDict | None:
        listing = self.session.scalar(self._select_listing().where(Listing.host_id == host_id))
        if listing is None:
            return None
        return self._to_dict(listing)

    def upsert(self, listing: ListingDict) -> ListingDict:
        listing_id = listing.get("id")
        host_id = listing.get("host_id")
        if not host_id:
            raise ValueError("host_id is required to upsert listings")

        row = None
        if listing_id:
            row = self._get_listing(listing_id)
        if row is None:
            row = self.session.scalar(self._select_listing().where(Listing.host_id == host_id))
        if row is None:
            row = Listing(
                id=listing_id or str(uuid4()),
                host_id=host_id,
                status=listing.get("status") or "DRAFT",
            )
            self.session.add(row)

        if "title" in listing:
            row.title = listing.get("title")
        if "price_per_month" in listing:
            row.price_per_month = listing.get("price_per_month")
        if "city" in listing:
            row.city = listing.get("city")
        if "state" in listing:
            row.state = listing.get("state")
        if "available_from" in listing:
            row.available_from = listing.get("available_from")
        if "available_to" in listing:
            row.available_to = listing.get("available_to")
        if "status" in listing and listing.get("status") is not None:
            row.status = listing.get("status") or row.status
        if "roommates" in listing and listing["roommates"] is not None:
            row.roommates.clear()
            for roommate_payload in listing["roommates"]:
                row.roommates.append(_roommate_from_dict(row.id, roommate_payload))

        return self._to_dict(row)

    def search(
        self,
        city: str | None = None,
        max_price: Decimal | None = None,
    ) -> Sequence[ListingDict]:
        stmt = self._select_listing()
        if city:
            stmt = stmt.where(Listing.city == city)
        if max_price is not None:
            stmt = stmt.where(Listing.price_per_month <= max_price)
        rows = self.session.scalars(stmt).all()
        return [self._to_dict(row) for row in rows]

    def queue_for_seeker(self, seeker_id: str) -> Sequence[ListingDict]:
        del seeker_id  # queue logic handled at router layer
        stmt = self._select_listing().where(Listing.status == "PUBLISHED")
        rows = self.session.scalars(stmt).all()
        return [self._to_dict(row) for row in rows]

    @property
    def _data(self) -> dict[str, ListingDict]:
        rows = self.session.scalars(self._select_listing()).all()
        return {row.id: self._to_dict(row) for row in rows}


class SqlAlchemyMatchRepo(MatchRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_dict(self, match: Match) -> MatchDict:
        data: MatchDict = MatchDict(
            id=match.id,
            seeker_id=match.seeker_id,
            listing_id=match.listing_id,
            status=match.status,
            score=match.score if match.score is not None else None,
            matched_at=match.matched_at,
        )
        return data

    def list_for_seeker(self, seeker_id: str) -> Sequence[MatchDict]:
        rows = self.session.scalars(select(Match).where(Match.seeker_id == seeker_id)).all()
        return [self._to_dict(row) for row in rows]

    def list_for_host(self, host_id: str) -> Sequence[MatchDict]:
        del host_id  # filtering handled by routers for now
        rows = self.session.scalars(select(Match)).all()
        return [self._to_dict(row) for row in rows]

    def upsert(
        self,
        seeker_id: str,
        listing_id: str,
        status: str,
        score: float | None,
    ) -> MatchDict:
        match_id = f"{seeker_id}:{listing_id}"
        match = self.session.get(Match, match_id)
        if match is None:
            match = Match(
                id=match_id,
                seeker_id=seeker_id,
                listing_id=listing_id,
                status=status,
                score=Decimal(str(score)) if score is not None else None,
            )
            self.session.add(match)
        else:
            match.status = status
            match.score = Decimal(str(score)) if score is not None else None
        return self._to_dict(match)

    @property
    def _data(self) -> dict[str, MatchDict]:
        rows = self.session.scalars(select(Match)).all()
        return {row.id: self._to_dict(row) for row in rows}


class SqlAlchemySwipeRepo(SwipeRepo):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._pending_swipes: list[SwipeDict] = []
        self._pending_stack: dict[str, list[SwipeDict]] = {}

    def record_swipe(self, swiper_id: str, target_id: str, decision: str) -> SwipeDict:
        normalized = "like" if decision == "like" else "pass"
        swipe: SwipeDict = {
            "id": str(uuid4()),
            "user_id": swiper_id,
            "target_id": target_id,
            "decision": normalized,
            "created_at": datetime.now(UTC),
        }
        self._pending_swipes.append(swipe)
        self._pending_stack.setdefault(swiper_id, []).append(swipe)
        return swipe

    def undo_last(self, user_id: str) -> SwipeDict | None:
        stack = self._pending_stack.get(user_id)
        if stack:
            last = stack.pop()
            self._pending_swipes = [swipe for swipe in self._pending_swipes if swipe["id"] != last["id"]]
            return last

        seeker_profile = self.session.scalar(
            select(SeekerProfile).where(SeekerProfile.user_id == user_id)
        )
        if seeker_profile:
            swipe = self._pop_latest_seeker_swipe(seeker_profile)
            if swipe:
                return swipe

        host_profile = self.session.scalar(select(HostProfile).where(HostProfile.user_id == user_id))
        if host_profile:
            swipe = self._pop_latest_host_swipe(host_profile)
            if swipe:
                return swipe

        return None

    def _pop_latest_seeker_swipe(self, seeker: SeekerProfile) -> SwipeDict | None:
        swipe = self.session.scalar(
            select(SeekerSwipe)
            .where(SeekerSwipe.seeker_id == seeker.id)
            .order_by(SeekerSwipe.created_at.desc())
        )
        if swipe is None:
            return None
        result = {
            "id": swipe.id,
            "user_id": seeker.user_id,
            "target_id": swipe.listing_id,
            "decision": "like" if swipe.decision == "LIKE" else "pass",
            "created_at": swipe.created_at or datetime.now(UTC),
        }
        self.session.delete(swipe)
        return result

    def _pop_latest_host_swipe(self, host: HostProfile) -> SwipeDict | None:
        swipe = self.session.scalar(
            select(HostSwipe)
            .where(HostSwipe.host_id == host.id)
            .order_by(HostSwipe.created_at.desc())
        )
        if swipe is None:
            return None
        result = {
            "id": swipe.id,
            "user_id": host.user_id,
            "target_id": swipe.seeker_id,
            "decision": "like" if swipe.decision == "LIKE" else "pass",
            "created_at": swipe.created_at or datetime.now(UTC),
        }
        self.session.delete(swipe)
        return result

    def flush_pending(self) -> None:
        for swipe in self._pending_swipes:
            target_listing = self.session.get(Listing, swipe["target_id"])
            if target_listing is not None:
                self._apply_seeker_swipe(swipe, target_listing)
                continue

            target_seeker = self.session.get(SeekerProfile, swipe["target_id"])
            if target_seeker is not None:
                self._apply_host_swipe(swipe, target_seeker)
                continue

            raise RuntimeError(f"Unknown swipe target: {swipe['target_id']}")
        self._pending_swipes.clear()
        self._pending_stack.clear()

    def reset_pending(self) -> None:
        self._pending_swipes.clear()
        self._pending_stack.clear()

    def _apply_seeker_swipe(self, swipe: SwipeDict, listing: Listing) -> None:
        seeker_profile = self.session.scalar(
            select(SeekerProfile).where(SeekerProfile.user_id == swipe["user_id"])
        )
        if seeker_profile is None:
            raise RuntimeError(f"Seeker profile missing for user {swipe['user_id']}")

        existing = self.session.scalar(
            select(SeekerSwipe).where(
                SeekerSwipe.seeker_id == seeker_profile.id,
                SeekerSwipe.listing_id == listing.id,
            )
        )
        decision = "LIKE" if swipe["decision"] == "like" else "PASS"
        if existing:
            existing.decision = decision
            existing.created_at = swipe["created_at"]
        else:
            row = SeekerSwipe(
                id=swipe["id"],
                seeker_id=seeker_profile.id,
                listing_id=listing.id,
                decision=decision,
                created_at=swipe["created_at"],
            )
            self.session.add(row)

    def _apply_host_swipe(self, swipe: SwipeDict, target_seeker: SeekerProfile) -> None:
        host_profile = self.session.scalar(
            select(HostProfile).where(HostProfile.user_id == swipe["user_id"])
        )
        if host_profile is None:
            raise RuntimeError(f"Host profile missing for user {swipe['user_id']}")

        existing = self.session.scalar(
            select(HostSwipe).where(
                HostSwipe.host_id == host_profile.id,
                HostSwipe.seeker_id == target_seeker.id,
            )
        )
        decision = "LIKE" if swipe["decision"] == "like" else "PASS"
        if existing:
            existing.decision = decision
            existing.created_at = swipe["created_at"]
        else:
            row = HostSwipe(
                id=swipe["id"],
                host_id=host_profile.id,
                seeker_id=target_seeker.id,
                decision=decision,
                created_at=swipe["created_at"],
            )
            self.session.add(row)

    def _fetch_seeker_swipes(self) -> dict[str, SwipeDict]:
        rows = self.session.execute(
            select(SeekerSwipe, SeekerProfile.user_id).join(
                SeekerProfile, SeekerSwipe.seeker_id == SeekerProfile.id
            )
        )
        result: dict[str, SwipeDict] = {}
        for swipe, user_id in rows:
            result[swipe.id] = {
                "id": swipe.id,
                "user_id": user_id,
                "target_id": swipe.listing_id,
                "decision": "like" if swipe.decision == "LIKE" else "pass",
                "created_at": swipe.created_at or datetime.now(UTC),
            }
        return result

    def _fetch_host_swipes(self) -> dict[str, SwipeDict]:
        rows = self.session.execute(
            select(HostSwipe, HostProfile.user_id).join(
                HostProfile, HostSwipe.host_id == HostProfile.id
            )
        )
        result: dict[str, SwipeDict] = {}
        for swipe, user_id in rows:
            result[swipe.id] = {
                "id": swipe.id,
                "user_id": user_id,
                "target_id": swipe.seeker_id,
                "decision": "like" if swipe.decision == "LIKE" else "pass",
                "created_at": swipe.created_at or datetime.now(UTC),
            }
        return result

    @property
    def _data(self) -> dict[str, SwipeDict]:
        data = self._fetch_seeker_swipes()
        data.update(self._fetch_host_swipes())
        for swipe in self._pending_swipes:
            data[swipe["id"]] = swipe
        return data
