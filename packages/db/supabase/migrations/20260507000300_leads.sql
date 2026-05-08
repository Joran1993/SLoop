set search_path = public, extensions;

-- ── Lead-laag ──────────────────────────────────────────────────────────────

create type eigenaar_type as enum (
    'particulier', 'woningcorporatie', 'gemeente', 'bedrijf', 'onbekend'
);

create table sloop_leads (
    id                          uuid primary key default gen_random_uuid(),
    created_at                  timestamptz not null default now(),
    updated_at                  timestamptz not null default now(),

    sloopmelding_id             uuid not null references sloopmeldingen_raw(id) on delete cascade unique,
    pand_id                     text references bag_panden(pand_id),

    -- Adres + locatie
    address_full                text,
    straat                      text,
    huisnummer                  text,
    postcode                    text,
    gemeente                    text not null,
    provincie                   text,
    geometry                    geometry(Point, 28992),

    -- Pandkenmerken (van BAG)
    bouwjaar                    int,
    oppervlakte_m2              int,
    gebruiksdoelen              text[],
    energielabel                text,               -- van EP-Online

    -- Scoring
    asbest_risico_score         int not null default 0,     -- 0-100
    omvang_score                int not null default 0,     -- 0-100
    bereikbaarheid_score        int not null default 50,    -- placeholder v1
    circulair_potentieel        int not null default 0,     -- 0-100
    score_total                 int not null default 0,     -- 0-100, gewogen
    score_breakdown             jsonb,

    -- Materiaalvolume-inschatting (kg)
    materiaal_volume_estimate   jsonb,
    -- bv. {"beton_kg": 450000, "hout_kg": 45000, "glas_kg": 3000}

    eigenaar_type               eigenaar_type not null default 'onbekend',
    tender_window_estimate_weeks int not null default 8,

    -- Meta
    koop_url                    text,
    datum_publicatie            date,
    is_stale                    boolean not null default false,
    last_scored_at              timestamptz
);

create trigger sloop_leads_updated_at before update on sloop_leads
    for each row execute function set_updated_at();

create index on sloop_leads(score_total desc);
create index on sloop_leads(gemeente);
create index on sloop_leads(provincie);
create index on sloop_leads(datum_publicatie desc);
create index on sloop_leads(bouwjaar);
create index on sloop_leads(oppervlakte_m2);
create index on sloop_leads using gist(geometry);


-- Lead-views: welke org heeft welke lead gezien
create table lead_views (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    organization_id uuid not null references organizations(id) on delete cascade,
    lead_id         uuid not null references sloop_leads(id) on delete cascade,
    viewed_at       timestamptz not null default now(),
    unique(organization_id, lead_id)
);

create index on lead_views(organization_id);
create index on lead_views(lead_id);


-- Lead-exports: audit trail
create table lead_exports (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    organization_id uuid not null references organizations(id) on delete cascade,
    exported_at     timestamptz not null default now(),
    format          export_format not null,
    filter_used     jsonb,
    lead_count      int not null default 0
);

create index on lead_exports(organization_id);
