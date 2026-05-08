"""Alert notificaties — verzendt dagelijkse/wekelijkse email alerts naar gebruikers."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from supabase import Client, create_client

from ..config import settings

log = logging.getLogger(__name__)

APP_URL = "https://sloopradar.nl"


def run() -> dict:
    if not settings.resend_api_key:
        log.warning("RESEND_API_KEY niet ingesteld — alerts overgeslagen.")
        return {"skipped": True}

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    now = datetime.now(timezone.utc)

    subscriptions = _get_due_subscriptions(supabase, now)
    log.info("Alerts: %d subscriptions te verwerken", len(subscriptions))

    stats = {"processed": 0, "sent": 0, "skipped_no_leads": 0, "errors": 0}

    for sub in subscriptions:
        try:
            _process_subscription(supabase, sub, now, stats)
        except Exception as exc:
            log.exception("Fout bij verwerken alert %s: %s", sub["id"], exc)
            stats["errors"] += 1

    log.info("Alerts klaar: %s", stats)
    return stats


def _get_due_subscriptions(supabase: Client, now: datetime) -> list[dict]:
    result = (
        supabase.table("alert_subscriptions")
        .select("id,user_id,name,filter,frequency,last_sent_at")
        .eq("active", True)
        .execute()
    )
    subscriptions = result.data or []

    due = []
    for sub in subscriptions:
        last_sent = sub.get("last_sent_at")
        freq = sub.get("frequency", "daily")
        if _is_due(last_sent, freq, now):
            due.append(sub)
    return due


def _is_due(last_sent_at: str | None, frequency: str, now: datetime) -> bool:
    if last_sent_at is None:
        return True
    last = datetime.fromisoformat(last_sent_at.replace("Z", "+00:00"))
    if frequency == "weekly":
        return (now - last) >= timedelta(days=7)
    return (now - last) >= timedelta(days=1)


def _process_subscription(supabase: Client, sub: dict, now: datetime, stats: dict) -> None:
    sub_id = sub["id"]
    user_id = sub["user_id"]
    alert_filter = sub.get("filter") or {}
    last_sent_at = sub.get("last_sent_at")

    since = _since_date(last_sent_at, sub.get("frequency", "daily"))
    leads = _query_matching_leads(supabase, alert_filter, since)

    stats["processed"] += 1

    if not leads:
        log.debug("Alert %s: geen nieuwe leads", sub_id)
        stats["skipped_no_leads"] += 1
        return

    user_email = _get_user_email(supabase, user_id)
    if not user_email:
        log.warning("Alert %s: kan gebruikersemail niet ophalen voor user %s", sub_id, user_id)
        return

    html = _build_email_html(sub["name"], leads, since)
    subject = f"Sloopradar: {len(leads)} nieuwe lead{'s' if len(leads) != 1 else ''} voor '{sub['name']}'"

    try:
        _send_email(user_email, subject, html)
    except Exception as exc:
        log.error("E-mail versturen mislukt voor alert %s: %s", sub_id, exc)
        _record_delivery(supabase, sub_id, leads, "failed", str(exc))
        raise

    _record_delivery(supabase, sub_id, leads, "sent")
    supabase.table("alert_subscriptions").update(
        {"last_sent_at": now.isoformat()}
    ).eq("id", sub_id).execute()

    log.info("Alert %s: %d leads verstuurd naar %s", sub_id, len(leads), user_email)
    stats["sent"] += 1


def _since_date(last_sent_at: str | None, frequency: str) -> datetime:
    if last_sent_at:
        return datetime.fromisoformat(last_sent_at.replace("Z", "+00:00"))
    days = 7 if frequency == "weekly" else 1
    return datetime.now(timezone.utc) - timedelta(days=days)


def _query_matching_leads(supabase: Client, alert_filter: dict, since: datetime) -> list[dict]:
    only_vergunning = alert_filter.get("only_with_vergunning")

    if only_vergunning:
        # For vergunning alerts: find leads where sloopvergunning was detected since last alert.
        # The publicatiedatum of the original sloopmelding may be old; we use signal_time instead.
        pand_ids_result = (
            supabase.table("pipeline_signals")
            .select("bag_pand_id")
            .in_("signal_type", ["sloopvergunning_verleend", "verleende_sloopvergunning"])
            .gte("signal_time", since.isoformat())
            .not_.is_("bag_pand_id", "null")
            .execute()
        )
        recent_pand_ids = list({r["bag_pand_id"] for r in (pand_ids_result.data or [])})
        if not recent_pand_ids:
            return []
        q = (
            supabase.table("sloop_leads_api")
            .select(
                "id, adres, gemeente, provincie, score_totaal, oppervlakte_m2, "
                "bouwjaar, energielabel, publicatiedatum, source_url, eigenaar_type, "
                "has_sloopvergunning, signal_count, bag_pand_id"
            )
            .in_("bag_pand_id", recent_pand_ids)
            .eq("has_sloopvergunning", True)
            .order("score_totaal", desc=True)
            .limit(50)
        )
    else:
        q = (
            supabase.table("sloop_leads_api")
            .select(
                "id, adres, gemeente, provincie, score_totaal, oppervlakte_m2, "
                "bouwjaar, energielabel, publicatiedatum, source_url, eigenaar_type, "
                "has_sloopvergunning, signal_count, bag_pand_id"
            )
            .gte("publicatiedatum", since.date().isoformat())
            .order("has_sloopvergunning", desc=True)
            .order("score_totaal", desc=True)
            .limit(50)
        )

    if alert_filter.get("provincies"):
        q = q.in_("provincie", alert_filter["provincies"])
    if alert_filter.get("min_score") is not None:
        q = q.gte("score_totaal", alert_filter["min_score"])
    if alert_filter.get("min_oppervlakte") is not None:
        q = q.gte("oppervlakte_m2", alert_filter["min_oppervlakte"])
    if alert_filter.get("gebruiksdoelen"):
        q = q.overlaps("gebruiksdoel", alert_filter["gebruiksdoelen"])

    result = q.execute()
    return result.data or []


def _get_user_email(supabase: Client, user_id: str) -> str | None:
    try:
        response = supabase.auth.admin.get_user_by_id(user_id)
        return response.user.email if response.user else None
    except Exception as exc:
        log.warning("Kan email niet ophalen voor user %s: %s", user_id, exc)
        return None


def _send_email(to_email: str, subject: str, html: str) -> None:
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    resp.raise_for_status()


def _record_delivery(
    supabase: Client,
    sub_id: str,
    leads: list[dict],
    status: str,
    error: str | None = None,
) -> None:
    lead_ids = [str(lead["id"]) for lead in leads]
    row: dict[str, Any] = {
        "alert_subscription_id": sub_id,
        "lead_ids": lead_ids,
        "channel": "email",
        "status": status,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        row["error_message"] = error[:500]
    supabase.table("alert_deliveries").insert(row).execute()


def _build_email_html(alert_name: str, leads: list[dict], since: datetime) -> str:
    since_label = since.strftime("%-d %B %Y")
    dashboard_url = f"{APP_URL}/dashboard"

    rows = ""
    for lead in leads:
        score = lead.get("score_totaal")
        score_str = str(round(score)) if score is not None else "—"
        score_color = "#10b981" if (score or 0) >= 70 else "#f59e0b" if (score or 0) >= 40 else "#ef4444"

        datum = lead.get("publicatiedatum")
        datum_str = (
            datetime.fromisoformat(datum).strftime("%-d %b %Y") if datum else "—"
        )

        opp = lead.get("oppervlakte_m2")
        opp_str = f"{int(opp):,}".replace(",", ".") + " m²" if opp else "—"

        adres = lead.get("adres") or "Onbekend"
        gemeente = lead.get("gemeente") or ""
        has_vergunning = lead.get("has_sloopvergunning") or False
        signal_count = lead.get("signal_count") or 0

        lead_id = lead.get("id")
        lead_url = f"{APP_URL}/leads/{lead_id}" if lead_id else None
        source_url = lead.get("source_url")
        adres_cell = (
            f'<a href="{lead_url}" style="color:#6366f1;text-decoration:none;">{adres}</a>'
            if lead_url
            else adres
        )
        badges = ""
        if has_vergunning:
            badges += ' <span style="background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:99px;font-size:10px;font-weight:600;">Vergunning</span>'
        if signal_count > 0:
            badges += f' <span style="background:#e0e7ff;color:#4f46e5;padding:1px 6px;border-radius:99px;font-size:10px;">● {signal_count}</span>'

        rows += f"""
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:10px 12px;font-size:13px;">{adres_cell}{badges}<br>
            <span style="color:#94a3b8;font-size:11px;">{gemeente}</span>
          </td>
          <td style="padding:10px 12px;font-size:13px;text-align:center;">
            <span style="background:{score_color}20;color:{score_color};padding:2px 8px;border-radius:99px;font-weight:600;font-size:12px;">{score_str}</span>
          </td>
          <td style="padding:10px 12px;font-size:13px;color:#64748b;">{opp_str}</td>
          <td style="padding:10px 12px;font-size:13px;color:#64748b;">{datum_str}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">

        <!-- Header -->
        <tr>
          <td style="background:#1e293b;padding:24px 32px;">
            <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Sloopradar</p>
            <h1 style="margin:4px 0 0;color:#f8fafc;font-size:20px;font-weight:600;">Nieuwe leads gevonden</h1>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:24px 32px 16px;">
            <p style="margin:0;color:#475569;font-size:14px;line-height:1.6;">
              Je alert <strong style="color:#1e293b;">"{alert_name}"</strong> heeft
              <strong style="color:#1e293b;">{len(leads)} nieuwe lead{'s' if len(leads) != 1 else ''}</strong>
              gevonden sinds {since_label}.
            </p>
          </td>
        </tr>

        <!-- Leads table -->
        <tr>
          <td style="padding:0 32px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
              <thead>
                <tr style="background:#f8fafc;">
                  <th style="padding:10px 12px;text-align:left;font-size:11px;color:#94a3b8;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Adres</th>
                  <th style="padding:10px 12px;text-align:center;font-size:11px;color:#94a3b8;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Score</th>
                  <th style="padding:10px 12px;font-size:11px;color:#94a3b8;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Opp.</th>
                  <th style="padding:10px 12px;font-size:11px;color:#94a3b8;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Datum</th>
                </tr>
              </thead>
              <tbody>{rows}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="padding:0 32px 32px;text-align:center;">
            <a href="{dashboard_url}"
               style="display:inline-block;background:#6366f1;color:#ffffff;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:500;text-decoration:none;">
              Bekijk alle leads in Sloopradar →
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;">
            <p style="margin:0;color:#94a3b8;font-size:11px;text-align:center;">
              Je ontvangt dit bericht omdat je een alert hebt ingesteld in Sloopradar.<br>
              <a href="{dashboard_url}/alerts" style="color:#6366f1;">Alerts beheren</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
