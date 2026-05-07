"""Mollie billing endpoints.

Checkout:  POST /billing/checkout  → Mollie subscription aanmaken
Webhook:   POST /billing/webhook   → Mollie status-updates verwerken
Portal:    POST /billing/portal    → customer-portal-link teruggeven
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import settings
from ..middleware.auth import AuthContext, require_auth
from ..models.billing import CheckoutRequest, CheckoutResponse, PortalResponse
from ..services.supabase import get_service_client

log = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

_PLAN_PRICES = {
    "starter":    "pln_starter_395",    # Mollie plan IDs (aanmaken in Mollie dashboard)
    "pro":        "pln_pro_895",
    "enterprise": "pln_enterprise_1495",
}


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Maak een Mollie subscription-checkout aan."""
    if not settings.mollie_api_key:
        raise HTTPException(status_code=503, detail="Betalingen nog niet geconfigureerd")

    plan_id = _PLAN_PRICES.get(body.plan_tier)
    if not plan_id:
        raise HTTPException(status_code=400, detail=f"Onbekend plan: {body.plan_tier}")

    try:
        checkout_url, subscription_id = _create_mollie_checkout(
            plan_id=plan_id,
            org_id=auth.org_id,
            redirect_url=body.redirect_url,
        )
    except Exception as exc:
        log.error("Mollie checkout aanmaken mislukt: %s", exc)
        raise HTTPException(status_code=502, detail="Betaallink aanmaken mislukt") from exc

    return CheckoutResponse(checkout_url=checkout_url, subscription_id=subscription_id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def mollie_webhook(request: Request):
    """
    Mollie webhook handler.
    Mollie stuurt een POST met `id` (payment/subscription ID).
    Wij verifieren en updaten de org-status.
    """
    body = await request.body()
    _verify_mollie_webhook(request, body)

    form = await request.form()
    payment_id = form.get("id")
    if not payment_id:
        return {"ok": True}

    try:
        _process_mollie_event(str(payment_id))
    except Exception as exc:
        log.error("Mollie webhook verwerking mislukt voor %s: %s", payment_id, exc)

    return {"ok": True}


@router.post("/portal", response_model=PortalResponse)
async def billing_portal(auth: Annotated[AuthContext, Depends(require_auth)]):
    """Geef Mollie customer-portal link terug."""
    sb = get_service_client()
    org = sb.table("organizations").select("mollie_customer_id").eq("id", auth.org_id).single().execute()
    customer_id = (org.data or {}).get("mollie_customer_id")

    if not customer_id or not settings.mollie_api_key:
        raise HTTPException(status_code=404, detail="Geen actief Mollie-account gevonden")

    portal_url = f"https://www.mollie.com/dashboard/customers/{customer_id}"
    return PortalResponse(portal_url=portal_url)


# ── Mollie helpers ────────────────────────────────────────────────────────────

def _create_mollie_checkout(plan_id: str, org_id: str, redirect_url: str) -> tuple[str, str | None]:
    """
    Maak een Mollie first-payment aan voor een nieuw abonnement.
    Retourneert (checkout_url, subscription_id).
    Implementatie: gebruik mollie-api-python client.
    """
    import httpx

    headers = {"Authorization": f"Bearer {settings.mollie_api_key}"}

    # Stap 1: Maak customer aan (of hergebruik bestaande)
    sb = get_service_client()
    org_res = sb.table("organizations").select("mollie_customer_id, billing_email, naam").eq("id", org_id).single().execute()
    org = org_res.data or {}
    customer_id = org.get("mollie_customer_id")

    if not customer_id:
        with httpx.Client() as client:
            res = client.post(
                "https://api.mollie.com/v2/customers",
                headers=headers,
                json={"name": org.get("naam", ""), "email": org.get("billing_email", "")},
            )
            res.raise_for_status()
            customer_id = res.json()["id"]
            sb.table("organizations").update({"mollie_customer_id": customer_id}).eq("id", org_id).execute()

    # Stap 2: Maak first-payment aan (iDEAL/SEPA flow)
    with httpx.Client() as client:
        res = client.post(
            "https://api.mollie.com/v2/payments",
            headers=headers,
            json={
                "amount": {"currency": "EUR", "value": "0.01"},  # verificatiebetaling
                "description": f"Sloopradar {plan_id} — eerste betaling",
                "redirectUrl": redirect_url,
                "webhookUrl": f"{settings.app_base_url}/api/billing/webhook",
                "customerId": customer_id,
                "sequenceType": "first",
                "metadata": {"org_id": org_id, "plan_id": plan_id},
            },
        )
        res.raise_for_status()
        payment = res.json()
        checkout_url = payment["_links"]["checkout"]["href"]

    return checkout_url, None


def _verify_mollie_webhook(request: Request, body: bytes) -> None:
    """Controleer Mollie webhook handtekening (als webhook-secret geconfigureerd is)."""
    if not settings.mollie_webhook_secret:
        return
    sig = request.headers.get("Mollie-Signature", "")
    expected = hmac.new(
        settings.mollie_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Ongeldige webhook handtekening")


def _process_mollie_event(payment_id: str) -> None:
    """Verwerk een Mollie betaal-event: update org-status."""
    import httpx
    headers = {"Authorization": f"Bearer {settings.mollie_api_key}"}

    with httpx.Client() as client:
        res = client.get(f"https://api.mollie.com/v2/payments/{payment_id}", headers=headers)
        if res.status_code == 404:
            return
        res.raise_for_status()
        payment = res.json()

    mollie_status = payment.get("status")
    metadata = payment.get("metadata", {})
    org_id = metadata.get("org_id")
    plan_id = metadata.get("plan_id")

    if not org_id:
        return

    sb = get_service_client()

    if mollie_status == "paid":
        # Zet abonnement actief en sla plan op
        plan_tier = next((k for k, v in _PLAN_PRICES.items() if v == plan_id), None)
        updates: dict = {"plan_status": "active"}
        if plan_tier:
            updates["plan_tier"] = plan_tier
        sb.table("organizations").update(updates).eq("id", org_id).execute()
        log.info("Org %s geactiveerd op plan %s", org_id, plan_tier)

    elif mollie_status in ("failed", "canceled", "expired"):
        sb.table("organizations").update({"plan_status": "past_due"}).eq("id", org_id).execute()
        log.warning("Betaling %s mislukt voor org %s: %s", payment_id, org_id, mollie_status)
