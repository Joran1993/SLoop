-- Publiek preview-endpoint voor de landing page.
-- Geeft aantallen + 3 geanonimiseerde voorbeeldleads terug voor een gegeven
-- coördinaat + radius — zonder directe SELECT-rechten op de view.

CREATE OR REPLACE FUNCTION public.get_preview_leads(
  p_lat       double precision,
  p_lng       double precision,
  p_radius_km int DEFAULT 25
)
RETURNS jsonb
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  WITH nearby AS (
    SELECT
      source_type,
      adres,
      gemeente,
      oppervlakte_m2,
      publicatiedatum
    FROM public.pipeline_projects_api
    WHERE longitude IS NOT NULL
      AND latitude  IS NOT NULL
      AND ST_DWithin(
        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
        ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
        (p_radius_km * 1000)::double precision
      )
  ),
  counts AS (
    SELECT
      COUNT(*)::int AS totaal,
      COUNT(*) FILTER (WHERE source_type = 'eindhoven_vergunning')::int  AS vroeg,
      COUNT(*) FILTER (WHERE source_type = 'pijplijn')::int              AS pijplijn,
      COUNT(*) FILTER (
        WHERE source_type NOT IN ('eindhoven_vergunning', 'pijplijn')
      )::int AS kortermijn
    FROM nearby
  ),
  samples AS (
    SELECT
      source_type,
      adres,
      gemeente,
      oppervlakte_m2,
      GREATEST(0, EXTRACT(DAY FROM NOW() - publicatiedatum)::int) AS dagen_geleden
    FROM nearby
    WHERE adres    IS NOT NULL
      AND gemeente IS NOT NULL
    ORDER BY publicatiedatum DESC
    LIMIT 3
  )
  SELECT jsonb_build_object(
    'total',   (SELECT totaal FROM counts),
    'by_tier', jsonb_build_object(
      'vroeg',      (SELECT vroeg      FROM counts),
      'pijplijn',   (SELECT pijplijn   FROM counts),
      'kortermijn', (SELECT kortermijn FROM counts)
    ),
    'samples', COALESCE(
      (SELECT jsonb_agg(jsonb_build_object(
        'adres',  adres,
        'plaats', gemeente,
        'opp_m2', oppervlakte_m2,
        'dagen',  dagen_geleden,
        'tier',   source_type
      )) FROM samples),
      '[]'::jsonb
    )
  )
$$;

GRANT EXECUTE ON FUNCTION public.get_preview_leads(double precision, double precision, int) TO anon;
