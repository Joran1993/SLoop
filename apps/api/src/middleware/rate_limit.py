"""Per-org rate limiting op basis van plan tier.

Starter:    100 req/uur
Pro:       1000 req/uur
Enterprise: 10000 req/uur

Gebruikt slowapi met org_id als key (niet IP-adres),
zodat het per klant-abonnement werkt.
"""
from __future__ import annotations

from fastapi import Request

_LIMITS = {
    "starter": "100/hour",
    "pro": "1000/hour",
    "enterprise": "10000/hour",
}


def get_org_id_for_ratelimit(request: Request) -> str:
    """
    Rate-limit key: org_id uit request state (gezet door auth middleware).
    Valt terug op IP als auth nog niet gelopen is.
    """
    ctx = getattr(request.state, "auth_context", None)
    if ctx:
        return f"org:{ctx.org_id}"
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


def tier_limit(request: Request) -> str:
    """Geef het rate-limit-string voor de huidige org-tier."""
    ctx = getattr(request.state, "auth_context", None)
    tier = ctx.plan_tier if ctx else "starter"
    return _LIMITS.get(tier, _LIMITS["starter"])
