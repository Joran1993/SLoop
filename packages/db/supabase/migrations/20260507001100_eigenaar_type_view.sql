-- DROP + recreate is nodig bij toevoegen van kolom aan bestaande view
drop view if exists public.sloop_leads_api;

create view public.sloop_leads_api as
select
  sl.id,
  sr.koop_id                          as publicatie_id,
  sl.address_full                     as adres,
  sl.gemeente,
  sl.provincie,
  sl.postcode,
  sl.bouwjaar,
  sl.oppervlakte_m2,
  sl.energielabel,
  sl.score_total                      as score_totaal,
  sl.asbest_risico_score              as score_asbest,
  sl.omvang_score                     as score_omvang,
  sl.bereikbaarheid_score             as score_bereikbaarheid,
  sl.circulair_potentieel             as score_circulair,
  sl.gebruiksdoelen                   as gebruiksdoel,
  sl.eigenaar_type,
  case when sl.geometry is not null
    then st_x(st_transform(sl.geometry, 4326))
  end                                 as longitude,
  case when sl.geometry is not null
    then st_y(st_transform(sl.geometry, 4326))
  end                                 as latitude,
  sl.datum_publicatie                 as publicatiedatum,
  sr.titel,
  sl.created_at,
  sl.pand_id                          as bag_pand_id
from public.sloop_leads sl
join public.sloopmeldingen_raw sr on sr.id = sl.sloopmelding_id;

alter view public.sloop_leads_api set (security_invoker = on);
