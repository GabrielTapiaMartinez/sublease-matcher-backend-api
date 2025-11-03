from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Problem(BaseModel):
    type: str | None = None
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None

    model_config = ConfigDict(from_attributes=True)


def problem(status: int, title: str, detail: str | None = None) -> Problem:
    return Problem(type=None, title=title, status=status, detail=detail, instance=None)
