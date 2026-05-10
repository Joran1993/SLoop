-- Publieke stats RPC voor de landingspagina.
-- SECURITY DEFINER zodat anon de view kan lezen zonder directe SELECT-rechten.
-- Geeft alleen geaggregeerde tellingen terug — geen privédata.

CREATE OR REPLACE FUNCTION public.get_pipeline_stats()
RETURNS jsonb
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT jsonb_build_object(
    'totaal',   COUNT(*),
    'vroeg',    COUNT(*) FILTER (WHERE source_type = 'eindhoven_vergunning'),
    'pijplijn', COUNT(*) FILTER (WHERE source_type = 'pijplijn')
  )
  FROM public.pipeline_projects_api;
$$;

GRANT EXECUTE ON FUNCTION public.get_pipeline_stats() TO anon;
