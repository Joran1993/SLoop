from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrgInfo(BaseModel):
    id: UUID
    naam: str
    kvk_nummer: str | None
    billing_email: str
    plan_tier: str
    plan_status: str
    trial_ends_at: datetime | None
    current_period_end: datetime | None


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    role: str
    organization: OrgInfo
    leads_viewed_this_month: int = 0
    exports_this_month: int = 0
