"""Supabase JWT authenticatie middleware.

Verifieert de Bearer token via de Supabase JWKS-endpoint.
Injecteert user_id, org_id en plan_tier in de request state.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from ..config import settings

log = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)


@dataclass
class AuthContext:
    user_id: str
    org_id: str
    plan_tier: str          # starter | pro | enterprise
    plan_status: str        # trialing | active | past_due | canceled
    role: str               # owner | admin | member
    email: str | None = None


async def require_auth(request: Request) -> AuthContext:
    """
    FastAPI dependency: verifieert JWT en retourneert AuthContext.
    Gebruik als: auth: AuthContext = Depends(require_auth)
    """
    credentials: HTTPAuthorizationCredentials = await _bearer(request)
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        log.debug("JWT decode mislukt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ongeldige of verlopen token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub ontbreekt in token")

    # Haal org-info op via Supabase service-role client
    from ..services.supabase import get_service_client
    sb = get_service_client()

    member_res = (
        sb.table("org_members")
        .select("organization_id, role, organizations(plan_tier, plan_status)")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not member_res.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Geen organisatie gevonden voor deze gebruiker",
        )

    member = member_res.data[0]
    org = member.get("organizations", {}) or {}

    plan_status = org.get("plan_status", "canceled")
    if plan_status not in ("trialing", "active"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Abonnement niet actief (status: {plan_status})",
        )

    return AuthContext(
        user_id=user_id,
        org_id=member["organization_id"],
        plan_tier=org.get("plan_tier", "starter"),
        plan_status=plan_status,
        role=member.get("role", "member"),
        email=payload.get("email"),
    )


async def require_pro(request: Request) -> AuthContext:
    """Vereist Pro of Enterprise plan."""
    ctx = await require_auth(request)
    if ctx.plan_tier not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deze functie vereist een Pro- of Enterprise-abonnement",
        )
    return ctx


async def require_enterprise(request: Request) -> AuthContext:
    """Vereist Enterprise plan."""
    ctx = await require_auth(request)
    if ctx.plan_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deze functie vereist een Enterprise-abonnement",
        )
    return ctx
