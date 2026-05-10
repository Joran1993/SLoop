-- Fix timing bug: pipeline_projects_api gebruikte created_at (= backfill-datum)
-- als referentie voor resterende tijd. Nu gebruiken we MIN(signal_time) uit
-- pipeline_signals zodat een vergunning uit maart ook echt "7 weken geleden"
-- telt, niet "0 weken geleden" omdat het project gisteren in de DB is gekomen.
--
-- Bonus: source_url nu ook gevuld vanuit het nieuwste signaal met een URL.
-- Contact-kolommen toegevoegd aan pipeline_projects (toekomstige verrijking).

ALTER TABLE public.pipeline_projects
  ADD COLUMN IF NOT EXISTS contact_naam     text,
  ADD COLUMN IF NOT EXISTS contact_website  text,
  ADD COLUMN IF NOT EXISTS contact_telefoon text,
  ADD COLUMN IF NOT EXISTS contact_email    text;

DROP VIEW IF EXISTS public.pipeline_projects_api;

CREATE VIEW public.pipeline_projects_api AS
WITH signal_dates AS (
  SELECT
    bag_pand_id,
    MIN(signal_time) AS first_signal_at,
    (ARRAY_AGG(source_url ORDER BY signal_time DESC) FILTER (WHERE source_url IS NOT NULL))[1]
      AS latest_source_url
  FROM public.pipeline_signals
  WHERE bag_pand_id IS NOT NULL
  GROUP BY bag_pand_id
)
SELECT
  pp.id,
  pp.id::text                                         AS publicatie_id,
  pp.bag_pand_id,
  pp.address_text                                     AS adres,
  pp.postcode,
  pp.gemeente,
  pp.provincie,
  pp.bouwjaar,
  pp.oppervlakte_m2,
  pp.gebruiksdoelen                                   AS gebruiksdoel,
  pp.energielabel,
  pp.eigenaar_type,
  pp.eigenaar_naam,
  pp.contact_naam,
  pp.contact_website,
  pp.contact_telefoon,
  pp.contact_email,
  pp.signal_count,
  (pp.sloop_kans * 100)::int                          AS score_totaal,
  -- Timing: gebruik vroegste signaal-datum als referentie (niet DB-insert datum)
  CASE
    WHEN pp.horizon_months_min < 3
      THEN 'koop_sloopmelding'
    WHEN (
      pp.horizon_months_max
      - EXTRACT(EPOCH FROM (NOW() - COALESCE(sd.first_signal_at, pp.created_at))) / 2592000.0
    ) > 2
      THEN 'eindhoven_vergunning'
    ELSE 'koop_sloopmelding'
  END                                                 AS source_type,
  GREATEST(0, ROUND((
    pp.horizon_months_max
    - EXTRACT(EPOCH FROM (NOW() - COALESCE(sd.first_signal_at, pp.created_at))) / 2592000.0
  ) * 4))::int                                        AS tender_window_estimate_weeks,
  NULL::text                                          AS titel,
  COALESCE(sd.first_signal_at, pp.created_at)        AS publicatiedatum,
  sd.latest_source_url                                AS source_url,
  NULL::boolean                                       AS has_sloopvergunning,
  NULL::text                                          AS bag_pand_status,
  NULL::jsonb                                         AS materiaal_volume_estimate,
  NULL::numeric                                       AS score_asbest,
  NULL::numeric                                       AS score_omvang,
  NULL::numeric                                       AS score_bereikbaarheid,
  NULL::numeric                                       AS score_circulair,
  CASE WHEN pp.cluster_geometry IS NOT NULL
    THEN ST_X(ST_Transform(pp.cluster_geometry, 4326))
  END                                                 AS longitude,
  CASE WHEN pp.cluster_geometry IS NOT NULL
    THEN ST_Y(ST_Transform(pp.cluster_geometry, 4326))
  END                                                 AS latitude
FROM public.pipeline_projects pp
LEFT JOIN signal_dates sd ON sd.bag_pand_id = pp.bag_pand_id
WHERE pp.bag_pand_id IS NOT NULL OR pp.cluster_geometry IS NOT NULL;

ALTER VIEW public.pipeline_projects_api SET (security_invoker = on);
