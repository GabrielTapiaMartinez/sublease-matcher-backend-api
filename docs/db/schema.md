# Database Schema

```
users
 ├── seeker_profiles ──┬── seeker_photos
 │                     └── seeker_swipes ─┐
 └── host_profiles ──┬── listings ─┬── listing_photos
                     │            └── listing_roommates
                     └── host_swipes ─┘

listings ── matches ── seeker_profiles
```

## Tables
- `users`
  - Columns: `id` (PK uuid), `email` (text, unique), `first_name` (text), `last_name` (text), `current_role` (`role_t` enum), `email_notifications_enabled` (bool), `show_in_swipe` (bool)
  - Constraints: primary key on `id`, unique on `email`
- `seeker_profiles`
  - Columns: `id` (PK uuid), `user_id` (FK → `users.id`, unique), `visible` (bool), `bio` (text), `term` (`term_t` enum), `term_year` (int), `budget_min` (`numeric(10,2)`), `budget_max` (`numeric(10,2)`), `city` (text), `interests_csv` (text), `contact_email` (text), `need_from` (date), `need_to` (date, nullable, `CHECK need_to IS NULL OR need_to >= need_from`)
  - Constraints: unique (`user_id`)
- `seeker_photos`
  - Columns: `id` (PK uuid), `seeker_id` (FK → `seeker_profiles.id`), `position` (int), `url` (text)
- `host_profiles`
  - Columns: `id` (PK uuid), `user_id` (FK → `users.id`, unique), `visible` (bool), `bio` (text), `house_rules` (text), `contact_email` (text)
  - Constraints: unique (`user_id`)
- `listings`
  - Columns: `id` (PK uuid), `host_id` (FK → `host_profiles.id`, unique), `title` (text), `price_per_month` (`numeric(10,2)` with `CHECK price_per_month >= 0`), `city` (text), `state` (text), `available_from` (date), `available_to` (date, nullable, `CHECK available_to IS NULL OR available_to >= available_from`), `status` (`listing_status_t` enum)
- `listing_photos`
  - Columns: `id` (PK uuid), `listing_id` (FK → `listings.id`), `position` (int), `url` (text)
- `listing_roommates`
  - Columns: `id` (PK uuid), `listing_id` (FK → `listings.id`), `name` (text), `sleeping_habits` (text), `interests_csv` (text), `photo_url` (text), `pronouns` (text), `gender` (text), `study_habits` (text), `cleanliness` (text), `bio` (text)
- `seeker_swipes`
  - Columns: `id` (PK uuid), `seeker_id` (FK → `seeker_profiles.id`), `listing_id` (FK → `listings.id`), `decision` (`decision_t` enum), `created_at` (timestamptz)
  - Constraints: unique (`seeker_id`,`listing_id`)
- `host_swipes`
  - Columns: `id` (PK uuid), `host_id` (FK → `host_profiles.id`), `seeker_id` (FK → `seeker_profiles.id`), `decision` (`decision_t` enum), `created_at` (timestamptz)
  - Constraints: unique (`host_id`,`seeker_id`)
- `matches`
  - Columns: `id` (PK uuid), `seeker_id` (FK → `seeker_profiles.id`), `listing_id` (FK → `listings.id`), `status` (`match_status_t` enum), `score` (`numeric(3,2)`), `matched_at` (timestamptz)
  - Constraints: unique (`seeker_id`,`listing_id`)

## Enums
- `decision_t`: `LIKE`, `PASS`
- `listing_status_t`: `DRAFT`, `PUBLISHED`, `UNLISTED`
- `match_status_t`: `PENDING`, `MUTUAL`
- `role_t`: `SEEKER`, `HOST`
- `term_t`: `Fall`, `Spring`, `Summer`

All enums live in the `public` schema; use `\dT+` inside `psql` to list them.

> Note: IDs like `user-1` and `listing-1` are deterministic for dev seeding, and photo URLs remain relative (`/static/mock/seekers|listings|roommates/...`). Production can move to UUID primary keys and real media storage later while keeping the simple dev seeds.
