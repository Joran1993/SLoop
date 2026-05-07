-- PostGIS voor ruimtelijke queries (pand-geometrieën, afstanden)
create extension if not exists postgis with schema extensions;
create extension if not exists postgis_topology with schema extensions;
-- unaccent voor Nederlandse adresmatching
create extension if not exists unaccent with schema extensions;
