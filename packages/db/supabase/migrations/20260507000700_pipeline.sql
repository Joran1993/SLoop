set search_path = public, extensions;

-- ── Pipeline: signalen, projecten, voorspellingen ────────────────────────────

-- Centrale signaal-tabel: alles wat we uit de 7 bronnen oogsten
create table pipeline_signals (
  id                              uuid primary key default gen_random_uuid(),
  source                          text not null,
  source_id                       text not null,
  signal_type                     text not null,
  signal_strength                 text not null check (signal_strength in ('high', 'medium', 'low')),
  signal_time                     timestamptz not null,
  ingested_at                     timestamptz not null default now(),

  -- Locatie
  geometry                        geometry(Point, 28992),
  address_text                    text,
  postcode                        text,
  gemeente                        text,
  bag_pand_id                     text,

  -- Inhoud
  title                           text,
  description                     text,
  raw_payload                     jsonb not null,
  source_url                      text,

  -- Horizon-schatting
  estimated_horizon_months_min    int,
  estimated_horizon_months_max    int,

  unique(source, source_id)
);

create index idx_pipeline_signals_pand   on pipeline_signals(bag_pand_id) where bag_pand_id is not null;
create index idx_pipeline_signals_geom   on pipeline_signals using gist(geometry);
create index idx_pipeline_signals_time   on pipeline_signals(signal_time desc);
create index idx_pipeline_signals_post   on pipeline_signals(postcode);
create index idx_pipeline_signals_src    on pipeline_signals(source, signal_type);


-- Gederiveerde voorspelde sloopprojecten — één per pand/cluster
create table pipeline_projects (
  id                    uuid primary key default gen_random_uuid(),

  bag_pand_id           text,
  cluster_geometry      geometry(Point, 28992),
  address_text          text,
  postcode              text,
  gemeente              text,
  provincie             text,

  -- Pand-info (denormalized)
  bouwjaar              int,
  oppervlakte_m2        numeric,
  gebruiksdoelen        text[],
  energielabel          text,

  -- Voorspelling
  sloop_kans            numeric not null check (sloop_kans between 0 and 1),
  horizon_months_min    int not null,
  horizon_months_max    int not null,
  signal_count          int not null default 0,
  signal_diversity      int not null default 0,

  prediction_explanation  jsonb not null default '{}',
  prediction_version      text not null default 'rules-v1',

  -- Eigenaar/keten
  eigenaar_type         text check (eigenaar_type in ('corporatie','overheid','ontwikkelaar','particulier','onbekend')),
  eigenaar_naam         text,
  betrokken_partijen    jsonb,

  status                text not null default 'actief'
                          check (status in ('actief','gerealiseerd','verlopen','afgewezen')),
  realised_at           timestamptz,

  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index idx_pipeline_projects_pand      on pipeline_projects(bag_pand_id);
create index idx_pipeline_projects_geom      on pipeline_projects using gist(cluster_geometry);
create index idx_pipeline_projects_score     on pipeline_projects(sloop_kans desc);
create index idx_pipeline_projects_horizon   on pipeline_projects(horizon_months_min);
create index idx_pipeline_projects_status    on pipeline_projects(status);
create index idx_pipeline_projects_gemeente  on pipeline_projects(gemeente);

create trigger pipeline_projects_updated_at before update on pipeline_projects
  for each row execute function set_updated_at();


-- Koppeltabel: welke signalen onderbouwen welk project
create table pipeline_project_signals (
  project_id  uuid not null references pipeline_projects(id) on delete cascade,
  signal_id   uuid not null references pipeline_signals(id) on delete cascade,
  weight      numeric not null default 1.0,
  primary key (project_id, signal_id)
);

create index idx_pps_project on pipeline_project_signals(project_id);
create index idx_pps_signal  on pipeline_project_signals(signal_id);


-- Voorspellings-log: trainingdata voor toekomstig ML-model
create table pipeline_predictions_log (
  id                          uuid primary key default gen_random_uuid(),
  project_id                  uuid references pipeline_projects(id),
  bag_pand_id                 text,
  predicted_kans              numeric not null,
  predicted_horizon_months_min int,
  predicted_horizon_months_max int,
  features_snapshot           jsonb not null,
  model_version               text not null,
  predicted_at                timestamptz not null default now(),
  outcome                     text check (outcome in ('sloop_gerealiseerd','geen_sloop','nog_open')),
  outcome_at                  timestamptz,
  outcome_source              text
);

create index idx_pred_log_project on pipeline_predictions_log(project_id);
create index idx_pred_log_time    on pipeline_predictions_log(predicted_at desc);


-- Klantfeedback: voor zowel v1-leads als pijplijn-projecten
create table customer_feedback (
  id                    uuid primary key default gen_random_uuid(),
  organization_id       uuid not null,
  user_id               uuid,
  lead_id               uuid,
  pipeline_project_id   uuid references pipeline_projects(id),
  status                text not null
                          check (status in ('opgevolgd','gewonnen','verloren','genegeerd','irrelevant')),
  contact_made          boolean,
  contact_outcome       text,
  notes                 text,
  created_at            timestamptz not null default now()
);

create index idx_feedback_org     on customer_feedback(organization_id);
create index idx_feedback_project on customer_feedback(pipeline_project_id);


-- ── RLS ──────────────────────────────────────────────────────────────────────

alter table pipeline_signals enable row level security;
create policy "paying_read_pipeline_signals" on pipeline_signals
  for select using (auth_is_paying());

alter table pipeline_projects enable row level security;
create policy "paying_read_pipeline_projects" on pipeline_projects
  for select using (auth_is_paying());

alter table pipeline_project_signals enable row level security;
create policy "paying_read_pipeline_project_signals" on pipeline_project_signals
  for select using (auth_is_paying());

alter table pipeline_predictions_log enable row level security;
create policy "paying_read_pipeline_predictions" on pipeline_predictions_log
  for select using (auth_is_paying());

alter table customer_feedback enable row level security;
create policy "own_org_customer_feedback" on customer_feedback
  for all using (organization_id = auth_org_id());


-- ── API-view voor pipeline projects ──────────────────────────────────────────

create or replace view public.pipeline_projects_api as
select
  p.id,
  p.bag_pand_id,
  p.address_text,
  p.postcode,
  p.gemeente,
  p.provincie,
  p.bouwjaar,
  p.oppervlakte_m2,
  p.gebruiksdoelen,
  p.energielabel,
  p.sloop_kans,
  p.horizon_months_min,
  p.horizon_months_max,
  p.signal_count,
  p.signal_diversity,
  p.prediction_explanation,
  p.eigenaar_type,
  p.eigenaar_naam,
  p.betrokken_partijen,
  p.status,
  p.created_at,
  p.updated_at,
  case when p.cluster_geometry is not null
    then st_x(st_transform(p.cluster_geometry, 4326))
  end as longitude,
  case when p.cluster_geometry is not null
    then st_y(st_transform(p.cluster_geometry, 4326))
  end as latitude
from public.pipeline_projects p
where p.status = 'actief';

alter view public.pipeline_projects_api set (security_invoker = on);
