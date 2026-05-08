"""Leads endpoints."""
from __future__ import annotations

import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from slowapi import Limiter

from ..middleware.auth import AuthContext, require_auth, require_pro
from ..middleware.rate_limit import get_org_id_for_ratelimit
from ..models.leads import LeadDetail, LeadSummary, PaginatedLeads
from ..services.supabase import get_service_client

router = APIRouter(prefix="/leads", tags=["leads"])
limiter = Limiter(key_func=get_org_id_for_ratelimit)

_PAGE_SIZE_DEFAULT = 25
_PAGE_SIZE_MAX = 100

# Kolommen die altijd opgehaald worden
_LEAD_COLS = (
    "id,address_full,gemeente,provincie,bouwjaar,oppervlakte_m2,gebruiksdoelen,"
    "energielabel,asbest_risico_score,score_total,eigenaar_type,datum_publicatie,"
    "koop_url,created_at"
)
_LEAD_DETAIL_COLS = _LEAD_COLS + (
    ",postcode,score_breakdown,materiaal_volume_estimate,"
    "tender_window_estimate_weeks,pand_id,sloopmelding_id"
)


@router.get("", response_model=PaginatedLeads)
async def list_leads(
    auth: Annotated[AuthContext, Depends(require_auth)],
    page: int = Query(1, ge=1),
    page_size: int = Query(_PAGE_SIZE_DEFAULT, ge=1, le=_PAGE_SIZE_MAX),
    provincie: list[str] | None = Query(None),
    gemeente: list[str] | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    gebruiksdoel: list[str] | None = Query(None),
    bouwjaar_min: int | None = Query(None),
    bouwjaar_max: int | None = Query(None),
    oppervlakte_min: int | None = Query(None),
    oppervlakte_max: int | None = Query(None),
    datum_van: str | None = Query(None),
    datum_tot: str | None = Query(None),
    sort_by: str = Query("score_total"),
    sort_dir: str = Query("desc"),
):
    _validate_sort(sort_by, sort_dir)
    sb = get_service_client()

    query = sb.table("sloop_leads").select(_LEAD_COLS, count="exact")

    # Starter: max 1 provincie
    if auth.plan_tier == "starter":
        if not provincie:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Starter-abonnement vereist een provincie-filter (max 1)",
            )
        if len(provincie) > 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Starter-abonnement: max 1 provincie tegelijk",
            )

    if provincie:
        query = query.in_("provincie", provincie)
    if gemeente:
        query = query.in_("gemeente", gemeente)
    if min_score is not None:
        query = query.gte("score_total", min_score)
    if gebruiksdoel:
        query = query.overlaps("gebruiksdoelen", gebruiksdoel)
    if bouwjaar_min is not None:
        query = query.gte("bouwjaar", bouwjaar_min)
    if bouwjaar_max is not None:
        query = query.lte("bouwjaar", bouwjaar_max)
    if oppervlakte_min is not None:
        query = query.gte("oppervlakte_m2", oppervlakte_min)
    if oppervlakte_max is not None:
        query = query.lte("oppervlakte_m2", oppervlakte_max)
    if datum_van:
        query = query.gte("datum_publicatie", datum_van)
    if datum_tot:
        query = query.lte("datum_publicatie", datum_tot)

    offset = (page - 1) * page_size
    ascending = sort_dir.lower() == "asc"
    result = query.order(sort_by, desc=not ascending).range(offset, offset + page_size - 1).execute()

    total = result.count or 0
    items = [LeadSummary(**row) for row in (result.data or [])]

    # Markeer als gezien
    _mark_viewed(sb, auth.org_id, [str(i.id) for i in items])

    return PaginatedLeads(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/export")
async def export_leads(
    auth: Annotated[AuthContext, Depends(require_pro)],
    provincie: list[str] | None = Query(None),
    gemeente: str | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    with_sloopvergunning: bool | None = Query(None),
    with_signals: bool | None = Query(None),
    eigenaar_type: str | None = Query(None),
    gebruiksdoel: str | None = Query(None),
    datum_van: str | None = Query(None),
    format: str = Query("csv"),
):
    """Exporteer leads als CSV. Alleen Pro+."""
    sb = get_service_client()
    query = sb.table("sloop_leads_api").select(
        "adres,gemeente,provincie,bouwjaar,oppervlakte_m2,"
        "gebruiksdoel,eigenaar_type,eigenaar_naam,energielabel,"
        "score_asbest,score_totaal,"
        "publicatiedatum,source_url,"
        "has_sloopvergunning,signal_count"
    ).order("has_sloopvergunning", desc=True).order("score_totaal", desc=True)

    if provincie:
        query = query.in_("provincie", provincie)
    if gemeente:
        query = query.ilike("gemeente", f"%{gemeente}%")
    if min_score is not None:
        query = query.gte("score_totaal", min_score)
    if with_sloopvergunning:
        query = query.eq("has_sloopvergunning", True)
    if with_signals:
        query = query.gt("signal_count", 0)
    if eigenaar_type:
        query = query.eq("eigenaar_type", eigenaar_type)
    if gebruiksdoel:
        query = query.contains("gebruiksdoel", [gebruiksdoel])
    if datum_van:
        query = query.gte("publicatiedatum", datum_van)

    result = query.limit(5000).execute()
    rows = result.data or []

    # Audit log
    sb.table("lead_exports").insert({
        "organization_id": auth.org_id,
        "format": format,
        "filter_used": {
            "provincie": provincie, "gemeente": gemeente, "min_score": min_score,
            "with_sloopvergunning": with_sloopvergunning, "with_signals": with_signals,
        },
        "lead_count": len(rows),
    }).execute()

    if format == "csv":
        return _as_csv(rows)

    return rows


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    sb = get_service_client()
    result = sb.table("sloop_leads").select(_LEAD_DETAIL_COLS).eq("id", str(lead_id)).single().execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead niet gevonden")

    _mark_viewed(sb, auth.org_id, [str(lead_id)])
    return LeadDetail(**result.data)


@router.post("/{lead_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def mark_viewed(
    lead_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    sb = get_service_client()
    _mark_viewed(sb, auth.org_id, [str(lead_id)])


# ── helpers ───────────────────────────────────────────────────────────────────

def _mark_viewed(sb, org_id: str, lead_ids: list[str]) -> None:
    if not lead_ids:
        return
    rows = [{"organization_id": org_id, "lead_id": lid} for lid in lead_ids]
    sb.table("lead_views").upsert(rows, on_conflict="organization_id,lead_id", ignore_duplicates=True).execute()


def _validate_sort(sort_by: str, sort_dir: str) -> None:
    allowed_cols = {"score_total", "datum_publicatie", "oppervlakte_m2", "bouwjaar", "asbest_risico_score", "gemeente"}
    if sort_by not in allowed_cols:
        raise HTTPException(status_code=400, detail=f"Ongeldige sorteerkolom. Kies uit: {allowed_cols}")
    if sort_dir not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort_dir moet 'asc' of 'desc' zijn")


def _as_csv(rows: list[dict]) -> Response:
    cols = [
        "adres", "gemeente", "provincie", "bouwjaar", "oppervlakte_m2",
        "gebruiksdoel", "eigenaar_type", "eigenaar_naam", "energielabel", "score_asbest",
        "score_totaal", "publicatiedatum", "source_url",
        "has_sloopvergunning", "signal_count",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        row = dict(row)
        if isinstance(row.get("gebruiksdoel"), list):
            row["gebruiksdoel"] = "|".join(row["gebruiksdoel"])
        writer.writerow(row)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sloopradar_leads.csv"},
    )
