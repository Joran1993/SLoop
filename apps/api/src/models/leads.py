from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    asbest_risico: int
    omvang: int
    bereikbaarheid: int
    circulair: int
    weights: dict[str, float]


class LeadSummary(BaseModel):
    id: UUID
    address_full: str | None
    gemeente: str
    provincie: str | None
    bouwjaar: int | None
    oppervlakte_m2: int | None
    gebruiksdoelen: list[str]
    energielabel: str | None
    asbest_risico_score: int
    score_total: int
    eigenaar_type: str
    datum_publicatie: date | None
    koop_url: str | None
    created_at: datetime


class LeadDetail(LeadSummary):
    postcode: str | None
    score_breakdown: ScoreBreakdown | None
    materiaal_volume_estimate: dict[str, Any] | None
    tender_window_estimate_weeks: int
    pand_id: str | None
    sloopmelding_id: UUID


class LeadFilters(BaseModel):
    provincie: list[str] | None = None
    gemeente: list[str] | None = None
    min_score: int | None = Field(None, ge=0, le=100)
    gebruiksdoelen: list[str] | None = None
    bouwjaar_min: int | None = Field(None, ge=1800, le=2100)
    bouwjaar_max: int | None = Field(None, ge=1800, le=2100)
    oppervlakte_min: int | None = Field(None, ge=0)
    oppervlakte_max: int | None = Field(None, ge=0)
    datum_van: date | None = None
    datum_tot: date | None = None


class PaginatedLeads(BaseModel):
    items: list[LeadSummary]
    total: int
    page: int
    page_size: int
    has_more: bool
