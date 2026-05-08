-- Sla longitude/latitude op als plain float kolommen zodat ST_Transform
-- niet meer per query hoeft te draaien (was ~1ms per rij, 200ms per query).
--
-- ST_Transform is STABLE, niet IMMUTABLE, dus geen generated column mogelijk.
-- We berekenen eenmalig bij schrijven (pipeline) en slaan op als float.

ALTER TABLE public.sloop_leads
  ADD COLUMN IF NOT EXISTS longitude double precision,
  ADD COLUMN IF NOT EXISTS latitude  double precision;

-- Backfill vanuit bestaande geometry
UPDATE public.sloop_leads
SET
  longitude = ST_X(ST_Transform(geometry, 4326)),
  latitude  = ST_Y(ST_Transform(geometry, 4326))
WHERE geometry IS NOT NULL;

-- Index voor geo-queries (kaart: bbox lookup)
CREATE INDEX IF NOT EXISTS sloop_leads_lonlat_idx
  ON public.sloop_leads (longitude, latitude)
  WHERE longitude IS NOT NULL;

-- Rebuild view: geen runtime ST_Transform meer
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
