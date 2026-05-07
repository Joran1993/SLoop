from __future__ import annotations

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan_tier: str          # starter | pro | enterprise
    redirect_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    subscription_id: str | None = None


class PortalResponse(BaseModel):
    portal_url: str


class WebhookEvent(BaseModel):
    id: str                 # Mollie payment/subscription ID
