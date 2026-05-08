"""Backfill eigenaar_type + eigenaar_naam voor leads met eigenaar_type = 'onbekend'."""
from __future__ import annotations

import logging
import sys

from supabase import create_client

from ..config import settings
from ..sources.kvk_lookup import infer_eigenaar_type_from_bag, infer_eigenaar_type_from_title
from ..sources.corporaties import get_primary_corporatie, get_corporatie_contact
from ..sources.duo_lookup import lookup_school_by_postcode

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

import re
_RE_HNR = re.compile(r"\b(\d{1,5}[a-zA-Z]?)\b")

def _extract_huisnummer(address: str) -> str | None:
    for part in (address or "").split():
        m = _RE_HNR.fullmatch(part)
        if m and not part.isalpha():
            return m.group(1)
    return None


def _process_row(row: dict, supabase) -> tuple[str, str, str]:
    """Verwerk één lead. Geeft ('type_set'|'skipped', naam_set, contact_set) terug."""
    gebruiksdoelen = row.get("gebruiksdoelen") or []
    bouwjaar = row.get("bouwjaar")
    gemeente = row.get("gemeente") or ""
    titel = row.get("titel") or ""
    postcode = row.get("postcode")
    address_full = row.get("address_full") or ""

    eigenaar_type = infer_eigenaar_type_from_bag(gebruiksdoelen, bouwjaar)
    if eigenaar_type == "onbekend":
        eigenaar_type = infer_eigenaar_type_from_title(titel)
    if eigenaar_type == "onbekend":
        return "skipped", False, False

    update: dict = {"eigenaar_type": eigenaar_type}
    naam_set = contact_set = False

    is_onderwijs = any("onderwijs" in (d or "").lower() for d in gebruiksdoelen)
    if is_onderwijs and postcode:
        duo = lookup_school_by_postcode(postcode, _extract_huisnummer(address_full))
        if duo:
            update["eigenaar_naam"] = duo.get("eigenaar_naam")
            update["contact_naam"] = duo.get("contact_naam")
            update["contact_website"] = duo.get("contact_website")
            update["contact_telefoon"] = duo.get("contact_telefoon")
            naam_set = contact_set = True

    elif eigenaar_type in ("corporatie_waarschijnlijk", "particulier_of_corporatie"):
        naam = get_primary_corporatie(gemeente)
        if naam:
            update["eigenaar_naam"] = naam
            naam_set = True
            contact = get_corporatie_contact(naam)
            if contact:
                update.update(contact)
                contact_set = True

    supabase.table("sloop_leads").update(update).eq("id", row["id"]).execute()
    return "type_set", naam_set, contact_set


def run() -> None:
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    stats = {"type_set": 0, "naam_set": 0, "contact_set": 0, "skipped": 0}

    # Haal alle onbekende leads op via paginatie (server cap = 1000/request)
    log.info("IDs ophalen van onbekende leads...")
    id_rows: list[dict] = []
    page = 0
    page_size = 1000
    while True:
        chunk = (
            supabase.table("sloop_leads")
            .select("id, gebruiksdoelen, bouwjaar, gemeente, titel, postcode, address_full")
            .eq("eigenaar_type", "onbekend")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        id_rows.extend(chunk)
        if len(chunk) < page_size:
            break
        page += 1

    log.info("%d leads te verwerken", len(id_rows))

    for i, row in enumerate(id_rows):
        status, naam_set, contact_set = _process_row(row, supabase)
        stats[status] += 1
        if naam_set:
            stats["naam_set"] += 1
        if contact_set:
            stats["contact_set"] += 1

        if (i + 1) % 500 == 0:
            log.info("Voortgang %d/%d — %s", i + 1, len(id_rows), stats)

    log.info("Klaar: %s", stats)


if __name__ == "__main__":
    run()
