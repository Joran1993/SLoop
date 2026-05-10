-- Voeg 'pijplijn' tier toe als derde laag tussen vroeg en laat:
--
--   eindhoven_vergunning  = aanvraag < 5 weken, geen verleend/sloopmelding  (VROEG)
--   pijplijn              = concept vergunning, bestemmingswijziging, MER, etc.  (PIJPLIJN)
--   koop_sloopmelding     = verleend, sloopmelding, of oude aanvraag              (LAAT)
--
-- sort_tier (1/2/3) zorgt dat de tabel altijd in de juiste volgorde staat.

DROP VIEW IF EXISTS public.pipeline_projects_api;

CREATE VIEW public.pipeline_projects_api AS
WITH signal_dates AS (
  SELECT
    bag_pand_id,
    MIN(signal_time)                                                                    AS first_signal_at,
    (ARRAY_AGG(source_url ORDER BY signal_time DESC)
      FILTER (WHERE source_url IS NOT NULL))[1]                                        AS latest_source_url,
    BOOL_OR(signal_type IN (
      'verleende_sloopvergunning', 'sloopvergunning_verleend', 'sloopmelding'
    ))                                                                                  AS has_late_signal,
    BOOL_OR(signal_type = 'aangevraagde_sloopvergunning')                              AS has_aanvraag,
    MIN(signal_time) FILTER (WHERE signal_type = 'aangevraagde_sloopvergunning')       AS earliest_aanvraag,
    BOOL_OR(signal_type IN (
      'woningcorporatie_sloopplan',
      'concept_omgevingsvergunning',
      'bestemmingswijziging',
      'bestemmingswijziging_herziening',
      'omgevingsplan_mutatie',
      'ontwerp_omgevingsplan',
      'ontwerp_plan',
      'mer_aanmelding',
      'eigendomsoverdracht',
      'pand_buiten_gebruik'
    ))                                                                                  AS has_pipeline_signal
  FROM public.pipeline_signals
  WHERE bag_pand_id IS NOT NULL
  GROUP BY bag_pand_id
),
classified AS (
  SELECT
    pp.*,
    sd.first_signal_at,
    sd.latest_source_url,
    sd.has_late_signal,
    sd.has_aanvraag,
    sd.earliest_aanvraag,
    sd.has_pipeline_signal,
    CASE
      -- Sloopmelding of verleende vergunning → altijd laat
      WHEN pp.horizon_months_min < 3 OR COALESCE(sd.has_late_signal, false)
        THEN 'koop_sloopmelding'
      -- Aanvraag aanwezig: vroeg als < 5 weken oud, anders laat
      WHEN COALESCE(sd.has_aanvraag, false)
        THEN CASE
          WHEN (NOW() - sd.earliest_aanvraag) <= INTERVAL '5 weeks' THEN 'eindhoven_vergunning'
          ELSE 'koop_sloopmelding'
        END
      -- Geen aanvraag, wel vroeg pijplijn signaal
      WHEN COALESCE(sd.has_pipeline_signal, false) THEN 'pijplijn'
      ELSE 'koop_sloopmelding'
    END AS source_type
  FROM public.pipeline_projects pp
  LEFT JOIN signal_dates sd ON sd.bag_pand_id = pp.bag_pand_id
  WHERE pp.bag_pand_id IS NOT NULL OR pp.cluster_geometry IS NOT NULL
)
SELECT
  c.id,
  c.id::text                                                       AS publicatie_id,
  c.bag_pand_id,
  c.address_text                                                   AS adres,
  c.postcode,
  c.gemeente,
  c.provincie,
  c.bouwjaar,
  c.oppervlakte_m2,
  c.gebruiksdoelen                                                 AS gebruiksdoel,
  c.energielabel,
  c.eigenaar_type,
  c.eigenaar_naam,
  c.contact_naam,
  c.contact_website,
  c.contact_telefoon,
  c.contact_email,
  c.signal_count,
  (c.sloop_kans * 100)::int                                        AS score_totaal,
  c.source_type,
  CASE c.source_type
    WHEN 'eindhoven_vergunning' THEN 1
    WHEN 'pijplijn'             THEN 2
    ELSE                             3
  END                                                              AS sort_tier,
  GREATEST(0, ROUND((
    c.horizon_months_max
    - EXTRACT(EPOCH FROM (NOW() - COALESCE(c.first_signal_at, c.created_at))) / 2592000.0
  ) * 4))::int                                                     AS tender_window_estimate_weeks,
  NULL::text                                                       AS titel,
  COALESCE(c.first_signal_at, c.created_at)                       AS publicatiedatum,
  c.latest_source_url                                              AS source_url,
  NULL::boolean                                                    AS has_sloopvergunning,
  NULL::text                                                       AS bag_pand_status,
  NULL::jsonb                                                      AS materiaal_volume_estimate,
  NULL::numeric                                                    AS score_asbest,
  NULL::numeric                                                    AS score_omvang,
  NULL::numeric                                                    AS score_bereikbaarheid,
  NULL::numeric                                                    AS score_circulair,
  CASE WHEN c.cluster_geometry IS NOT NULL
    THEN ST_X(ST_Transform(c.cluster_geometry, 4326))
  END                                                              AS longitude,
  CASE WHEN c.cluster_geometry IS NOT NULL
    THEN ST_Y(ST_Transform(c.cluster_geometry, 4326))
  END                                                              AS latitude
FROM classified c;

ALTER VIEW public.pipeline_projects_api SET (security_invoker = on);
