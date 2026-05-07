"""GET /me endpoint."""
from __future__ import annotations

from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..middleware.auth import AuthContext, require_auth
from ..models.me import MeResponse, OrgInfo
from ..services.supabase import get_service_client

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def get_me(auth: Annotated[AuthContext, Depends(require_auth)]):
    sb = get_service_client()

    org_result = (
        sb.table("organizations")
        .select("id,naam,kvk_nummer,billing_email,plan_tier,plan_status,trial_ends_at,current_period_end")
        .eq("id", auth.org_id)
        .single()
        .execute()
    )
    org_data = org_result.data or {}

    # Views deze maand
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    views_res = (
        sb.table("lead_views")
        .select("id", count="exact")
        .eq("organization_id", auth.org_id)
        .gte("viewed_at", month_start)
        .execute()
    )
    exports_res = (
        sb.table("lead_exports")
        .select("id", count="exact")
        .eq("organization_id", auth.org_id)
        .gte("exported_at", month_start)
        .execute()
    )

    return MeResponse(
        user_id=auth.user_id,
        email=auth.email,
        role=auth.role,
        organization=OrgInfo(**org_data),
        leads_viewed_this_month=views_res.count or 0,
        exports_this_month=exports_res.count or 0,
    )
