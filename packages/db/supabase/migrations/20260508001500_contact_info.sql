-- Voeg contactvelden toe aan sloop_leads.
-- contact_naam: bedrijfs/instellingsnaam (OSM of corporatie)
-- contact_website: website URL
-- contact_telefoon: telefoonnummer
-- contact_email: emailadres (zelden beschikbaar)

ALTER TABLE public.sloop_leads
  ADD COLUMN IF NOT EXISTS contact_naam     text,
  ADD COLUMN IF NOT EXISTS contact_website  text,
  ADD COLUMN IF NOT EXISTS contact_telefoon text,
  ADD COLUMN IF NOT EXISTS contact_email    text;

-- Rebuild view met contact kolommen
DROP VIEW IF EXISTS public.sloop_leads_api;

CREATE VIEW public.sloop_leads_api AS
SELECT
  sl.id,
  COALESCE(sl.koop_publicatie_id, sl.id::text) AS publicatie_id,
  sl.address_full                               AS adres,
  sl.gemeente,
  sl.provincie,
  sl.postcode,
  sl.bouwjaar,
  sl.oppervlakte_m2,
  sl.energielabel,
  sl.score_total                                AS score_totaal,
  sl.asbest_risico_score                        AS score_asbest,
  sl.omvang_score                               AS score_omvang,
  sl.bereikbaarheid_score                       AS score_bereikbaarheid,
  sl.circulair_potentieel                       AS score_circulair,
  sl.gebruiksdoelen                             AS gebruiksdoel,
  sl.eigenaar_type,
  sl.eigenaar_naam,
  sl.contact_naam,
  sl.contact_website,
  sl.contact_telefoon,
  sl.contact_email,
  sl.longitude,
  sl.latitude,
  sl.datum_publicatie                           AS publicatiedatum,
  COALESCE(sl.titel, sl.address_full)           AS titel,
  sl.created_at,
  sl.pand_id                                    AS bag_pand_id,
  sl.source_type,
  sl.koop_url                                   AS source_url,
  sl.tender_window_estimate_weeks,
  sl.materiaal_volume_estimate,
  sl.has_sloopvergunning,
  sl.signal_count
FROM public.sloop_leads sl;

ALTER VIEW public.sloop_leads_api SET (security_invoker = on);
