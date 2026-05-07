"""Alerts CRUD endpoints."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ..middleware.auth import AuthContext, require_auth
from ..models.alerts import AlertCreate, AlertResponse, AlertUpdate
from ..services.supabase import get_service_client

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(auth: Annotated[AuthContext, Depends(require_auth)]):
    sb = get_service_client()
    result = (
        sb.table("alert_subscriptions")
        .select("*")
        .eq("organization_id", auth.org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [AlertResponse(**row) for row in (result.data or [])]


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    _check_alert_limit(auth)
    sb = get_service_client()
    row = {
        "organization_id": auth.org_id,
        "user_id": auth.user_id,
        "name": body.name,
        "filter": body.filter.model_dump(exclude_none=True),
        "frequency": body.frequency,
        "active": True,
    }
    result = sb.table("alert_subscriptions").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Alert aanmaken mislukt")
    return AlertResponse(**result.data[0])


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    body: AlertUpdate,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    sb = get_service_client()
    _assert_owns_alert(sb, alert_id, auth.org_id)

    updates = body.model_dump(exclude_none=True)
    if "filter" in updates and hasattr(updates["filter"], "model_dump"):
        updates["filter"] = updates["filter"].model_dump(exclude_none=True)

    result = (
        sb.table("alert_subscriptions")
        .update(updates)
        .eq("id", str(alert_id))
        .execute()
    )
    return AlertResponse(**result.data[0])


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    sb = get_service_client()
    _assert_owns_alert(sb, alert_id, auth.org_id)
    sb.table("alert_subscriptions").delete().eq("id", str(alert_id)).execute()


# ── helpers ───────────────────────────────────────────────────────────────────

_ALERT_LIMITS = {"starter": 1, "pro": 10, "enterprise": 50}


def _check_alert_limit(auth: AuthContext) -> None:
    sb = get_service_client()
    result = (
        sb.table("alert_subscriptions")
        .select("id", count="exact")
        .eq("organization_id", auth.org_id)
        .execute()
    )
    count = result.count or 0
    limit = _ALERT_LIMITS.get(auth.plan_tier, 1)
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{auth.plan_tier.capitalize()}-abonnement: max {limit} alert(s). Upgrade voor meer.",
        )


def _assert_owns_alert(sb, alert_id: UUID, org_id: str) -> None:
    result = (
        sb.table("alert_subscriptions")
        .select("id")
        .eq("id", str(alert_id))
        .eq("organization_id", org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert niet gevonden")
