-- Voeg koop_url toe aan sloop_leads_api view als source_url
-- Klanten kunnen hiermee de originele publicatie/vergunning terugvinden

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
  sl.koop_url                         AS source_url
FROM public.sloop_leads sl
LEFT JOIN public.sloopmeldingen_raw sr ON sr.id = sl.sloopmelding_id;

ALTER VIEW public.sloop_leads_api SET (security_invoker = on);
