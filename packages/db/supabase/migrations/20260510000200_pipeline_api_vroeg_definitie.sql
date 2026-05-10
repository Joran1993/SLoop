-- Herstel de definitie van "vroeg signaal" voor sloopbedrijven:
--
-- Een sloopbedrijf wil weten dat er gesloopt gaat worden VOORDAT de eigenaar
-- sloopbedrijven begint te bellen. Dat moment is vlak na de vergunningaanvraag:
--   - Aanvraag < 5 weken oud + geen verleend signaal  → VROEG
--   - Verleend/sloopmelding/oude aanvraag             → LAAT
--
-- Hierdoor verdwijnen 175 "vroeg" leads die al een verleende vergunning hebben,
-- plus alle aanvragen ouder dan 5 weken (~600 stuks). Overblijven: ~70 echte vroege.

DROP VIEW IF EXISTS public.pipeline_projects_api;

CREATE VIEW public.pipeline_projects_api AS
WITH signal_dates AS (
  SELECT
    bag_pand_id,
    MIN(signal_time)                                                               AS first_signal_at,
    (ARRAY_AGG(source_url ORDER BY signal_time DESC)
      FILTER (WHERE source_url IS NOT NULL))[1]                                   AS latest_source_url,
    -- Zodra er een verleend of sloopmelding signaal is: definitief laat
    BOOL_OR(signal_type IN (
      'verleende_sloopvergunning',
      'sloopvergunning_verleend',
      'sloopmelding'
    ))                                                                             AS has_late_signal
  FROM public.pipeline_signals
  WHERE bag_pand_id IS NOT NULL
  GROUP BY bag_pand_id
)
SELECT
  pp.id,
  pp.id::text                                                   AS publicatie_id,
  pp.bag_pand_id,
  pp.address_text                                               AS adres,
  pp.postcode,
  pp.gemeente,
  pp.provincie,
  pp.bouwjaar,
  pp.oppervlakte_m2,
  pp.gebruiksdoelen                                             AS gebruiksdoel,
  pp.energielabel,
  pp.eigenaar_type,
  pp.eigenaar_naam,
  pp.contact_naam,
  pp.contact_website,
  pp.contact_telefoon,
  pp.contact_email,
  pp.signal_count,
  (pp.sloop_kans * 100)::int                                    AS score_totaal,
  CASE
    -- Sloopmelding-projecten of projects met verleend signaal → altijd laat
    WHEN pp.horizon_months_min < 3 OR COALESCE(sd.has_late_signal, false)
      THEN 'koop_sloopmelding'
    -- Aanvraag < 5 weken oud → vroeg (eigenaar belt nog niemand)
    WHEN (NOW() - COALESCE(sd.first_signal_at, pp.created_at)) <= INTERVAL '5 weeks'
      THEN 'eindhoven_vergunning'
    -- Aanvraag ouder dan 5 weken → eigenaar is al in gesprek
    ELSE 'koop_sloopmelding'
  END                                                           AS source_type,
  GREATEST(0, ROUND((
    pp.horizon_months_max
    - EXTRACT(EPOCH FROM (NOW() - COALESCE(sd.first_signal_at, pp.created_at))) / 2592000.0
  ) * 4))::int                                                  AS tender_window_estimate_weeks,
  NULL::text                                                    AS titel,
  COALESCE(sd.first_signal_at, pp.created_at)                  AS publicatiedatum,
  sd.latest_source_url                                          AS source_url,
  NULL::boolean                                                 AS has_sloopvergunning,
  NULL::text                                                    AS bag_pand_status,
  NULL::jsonb                                                   AS materiaal_volume_estimate,
  NULL::numeric                                                 AS score_asbest,
  NULL::numeric                                                 AS score_omvang,
  NULL::numeric                                                 AS score_bereikbaarheid,
  NULL::numeric                                                 AS score_circulair,
  CASE WHEN pp.cluster_geometry IS NOT NULL
    THEN ST_X(ST_Transform(pp.cluster_geometry, 4326))
  END                                                           AS longitude,
  CASE WHEN pp.cluster_geometry IS NOT NULL
    THEN ST_Y(ST_Transform(pp.cluster_geometry, 4326))
  END                                                           AS latitude
FROM public.pipeline_projects pp
LEFT JOIN signal_dates sd ON sd.bag_pand_id = pp.bag_pand_id
WHERE pp.bag_pand_id IS NOT NULL OR pp.cluster_geometry IS NOT NULL;

ALTER VIEW public.pipeline_projects_api SET (security_invoker = on);
