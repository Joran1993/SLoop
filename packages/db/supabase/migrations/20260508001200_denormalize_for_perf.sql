-- Performantie-optimalisatie: denormaliseer has_sloopvergunning en signal_count
-- naar sloop_leads als echte kolommen.
--
-- Probleem (EXPLAIN output):
--   1. Correlated subquery voor signal_count draait 5884x per query (N+1)
--   2. Disk sort omdat (has_sloopvergunning, score_total) niet gecombineerd geïndexeerd zijn
--   3. bag_panden JOIN alleen nodig voor has_sloopvergunning (nu weg)
--
-- Na deze migratie: view heeft geen subquery meer, één composite index dekt de default sort.

-- 1. Kolommen toevoegen
ALTER TABLE public.sloop_leads
  ADD COLUMN IF NOT EXISTS has_sloopvergunning boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS signal_count        int     NOT NULL DEFAULT 0;

-- 2. Backfill has_sloopvergunning vanuit bag_panden
UPDATE public.sloop_leads sl
SET has_sloopvergunning = true
FROM public.bag_panden bp
WHERE bp.pand_id = sl.pand_id
  AND bp.status = 'Sloopvergunning verleend';

-- 3. Backfill signal_count (exclusief sloopmelding-type signalen)
UPDATE public.sloop_leads sl
SET signal_count = (
  SELECT COUNT(*)::int
  FROM public.pipeline_signals ps
  WHERE ps.bag_pand_id = sl.pand_id
    AND ps.signal_type NOT IN ('sloopmelding')
)
WHERE sl.pand_id IS NOT NULL;

-- 4. Composite index voor default sort: has_sloopvergunning DESC, score_total DESC
CREATE INDEX IF NOT EXISTS sloop_leads_sort_idx
  ON public.sloop_leads (has_sloopvergunning DESC NULLS LAST, score_total DESC NULLS LAST);

-- 5. Trigram index voor gemeente ILIKE '%tekst%' (leading wildcard)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS sloop_leads_gemeente_trgm_idx
  ON public.sloop_leads USING gin (gemeente gin_trgm_ops);

-- 6. Rebuild view: geen subquery meer, geen bag_panden JOIN meer
DROP VIEW IF EXISTS public.sloop_leads_api;

CREATE VIEW public.sloop_leads_api AS
SELECT
  sl.id,
  COALESCE(sr.koop_id, sl.id::text)  AS publicatie_id,
  sl.address_full                     AS adres,
  sl.gemeente,
  sl.provincie,
  sl.postcode,
  sl.bouwjaar,
  sl.oppervlakte_m2,
  sl.energielabel,
  sl.score_total                      AS score_totaal,
  sl.asbest_risico_score              AS score_asbest,
  sl.omvang_score                     AS score_omvang,
  sl.bereikbaarheid_score             AS score_bereikbaarheid,
  sl.circulair_potentieel             AS score_circulair,
  sl.gebruiksdoelen                   AS gebruiksdoel,
  sl.eigenaar_type,
  sl.eigenaar_naam,
  CASE WHEN sl.geometry IS NOT NULL
    THEN ST_X(ST_Transform(sl.geometry, 4326))
  END                                 AS longitude,
  CASE WHEN sl.geometry IS NOT NULL
    THEN ST_Y(ST_Transform(sl.geometry, 4326))
  END                                 AS latitude,
  sl.datum_publicatie                 AS publicatiedatum,
  COALESCE(sr.titel, sl.address_full) AS titel,
  sl.created_at,
  sl.pand_id                          AS bag_pand_id,
  sl.source_type,
  sl.koop_url                         AS source_url,
  sl.tender_window_estimate_weeks,
  sl.materiaal_volume_estimate,
  sl.has_sloopvergunning,
  sl.signal_count
FROM public.sloop_leads sl
LEFT JOIN public.sloopmeldingen_raw sr ON sr.id = sl.sloopmelding_id;

ALTER VIEW public.sloop_leads_api SET (security_invoker = on);
