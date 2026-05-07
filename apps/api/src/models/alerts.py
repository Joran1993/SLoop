from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertFilterSchema(BaseModel):
    provincies: list[str] | None = None
    gemeenten: list[str] | None = None
    min_oppervlakte: int | None = None
    min_score: int | None = None
    gebruiksdoelen: list[str] | None = None


class AlertCreate(BaseModel):
    name: str
    filter: AlertFilterSchema = AlertFilterSchema()
    frequency: str = "daily"   # realtime | daily | weekly


class AlertUpdate(BaseModel):
    name: str | None = None
    filter: AlertFilterSchema | None = None
    frequency: str | None = None
    active: bool | None = None


class AlertResponse(BaseModel):
    id: UUID
    name: str
    filter: dict
    frequency: str
    active: bool
    last_sent_at: datetime | None
    created_at: datetime
