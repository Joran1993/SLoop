set search_path = public, extensions;

-- ── Auto-org aanmaken bij registratie ────────────────────────────────────────

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id uuid;
begin
  insert into public.organizations (naam, billing_email, plan_tier, plan_status)
  values (
    coalesce(new.email, 'Mijn organisatie'),
    coalesce(new.email, 'noreply@example.com'),
    'starter',
    'trialing'
  )
  returning id into v_org_id;

  insert into public.org_members (organization_id, user_id, role, accepted_at)
  values (v_org_id, new.id, 'owner', now());

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── Backfill: bestaande users zonder org alsnog koppelen ─────────────────────

do $$
declare
  u record;
  v_org_id uuid;
begin
  for u in
    select id, email from auth.users
    where not exists (select 1 from public.org_members where user_id = auth.users.id)
  loop
    insert into public.organizations (naam, billing_email, plan_tier, plan_status)
    values (
      coalesce(u.email, 'Mijn organisatie'),
      coalesce(u.email, 'noreply@example.com'),
      'starter',
      'trialing'
    )
    returning id into v_org_id;

    insert into public.org_members (organization_id, user_id, role, accepted_at)
    values (v_org_id, u.id, 'owner', now());
  end loop;
end;
$$;

-- ── View: leads met WGS84-coördinaten en API-compatibele veldnamen ────────────

create or replace view public.sloop_leads_api as
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
  case when sl.geometry is not null
    then st_x(st_transform(sl.geometry, 4326))
  end                                 as longitude,
  case when sl.geometry is not null
    then st_y(st_transform(sl.geometry, 4326))
  end                                 as latitude,
  sl.datum_publicatie                 as publicatiedatum,
  sr.titel,
  sl.created_at
from public.sloop_leads sl
join public.sloopmeldingen_raw sr on sr.id = sl.sloopmelding_id;

-- RLS van onderliggende tabellen (sloop_leads) van toepassing op de view
alter view public.sloop_leads_api set (security_invoker = on);

-- ── View: alerts met org_id zichtbaar ────────────────────────────────────────

create or replace view public.alert_subscriptions_api as
select
  a.id,
  a.organization_id,
  a.name,
  a.filter,
  a.frequency,
  a.active,
  a.created_at
from public.alert_subscriptions a;

alter view public.alert_subscriptions_api set (security_invoker = on);
