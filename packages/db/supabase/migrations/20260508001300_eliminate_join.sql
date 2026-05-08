-- Elimineer de LEFT JOIN met sloopmeldingen_raw in de view.
--
-- Direct index scan op sloop_leads: ~1ms
-- Via view met JOIN:                ~286ms (disk sort, hash join)
--
-- Oplossing: sla titel en koop_publicatie_id op in sloop_leads zodat
-- de view geen JOIN meer nodig heeft.

-- 1. Kolommen toevoegen
ALTER TABLE public.sloop_leads
  ADD COLUMN IF NOT EXISTS titel                text,
  ADD COLUMN IF NOT EXISTS koop_publicatie_id   text;

-- 2. Backfill vanuit sloopmeldingen_raw
UPDATE public.sloop_leads sl
SET
  titel              = sr.titel,
  koop_publicatie_id = sr.koop_id
FROM public.sloopmeldingen_raw sr
WHERE sr.id = sl.sloopmelding_id;

-- 3. Rebuild view: geen JOIN meer nodig
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
  CASE WHEN sl.geometry IS NOT NULL
    THEN ST_X(ST_Transform(sl.geometry, 4326))
  END                                           AS longitude,
  CASE WHEN sl.geometry IS NOT NULL
    THEN ST_Y(ST_Transform(sl.geometry, 4326))
  END                                           AS latitude,
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
