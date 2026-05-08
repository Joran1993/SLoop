set search_path = public, extensions;

-- ── Brondata tabellen ──────────────────────────────────────────────────────

create type parse_status as enum ('ok', 'partial', 'failed');

-- Ruwe sloopmeldingen uit KOOP SRU API
create table sloopmeldingen_raw (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),

    koop_id             text not null unique,       -- bv. "gmb-2026-209810"
    preferred_url       text,                       -- https://zoek.officielebekendmakingen.nl/...
    gemeente            text,
    provincie           text,
    datum_publicatie    date,
    datum_indiening     date,
    publicatietype      text,                       -- "omgevingsmelding", "andere beschikking", etc.
    titel               text,
    raw_xml             text,                       -- originele XML-payload bewaren
    parsed              jsonb,                      -- gestructureerde velden na parsing
    address_text        text,                       -- geëxtraheerd adres (straat + nr + postcode)
    matched_keywords    text[],

    -- BAG-koppeling (null tot geocoding gelopen)
    bag_pand_id         text,
    geocode_attempts    int not null default 0,
    geocode_status      text,                       -- 'ok', 'not_found', 'ambiguous', 'error'

    -- geometry in RD New (EPSG:28992) — null tot geocoding
    geometry            geometry(Point, 28992),

    processed_at        timestamptz,
    parse_status        parse_status not null default 'ok'
);

create trigger sloopmeldingen_raw_updated_at before update on sloopmeldingen_raw
    for each row execute function set_updated_at();

create index on sloopmeldingen_raw(datum_publicatie desc);
create index on sloopmeldingen_raw(gemeente);
create index on sloopmeldingen_raw(bag_pand_id);
create index on sloopmeldingen_raw(parse_status);
create index on sloopmeldingen_raw using gist(geometry);


-- BAG panden (verrijkingslaag: bouwjaar, oppervlakte, gebruiksdoel)
create table bag_panden (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    pand_id         text not null unique,           -- BAG identificatienummer
    geometry        geometry(MultiPolygon, 28992),
    bouwjaar        int,
    oppervlakte_min int,
    oppervlakte_max int,
    gebruiksdoelen  text[],
    status          text,                           -- "Pand in gebruik", etc.
    last_synced_at  timestamptz
);

create trigger bag_panden_updated_at before update on bag_panden
    for each row execute function set_updated_at();

create index on bag_panden using gist(geometry);


-- BAG verblijfsobjecten (detailniveau per unit)
create table bag_verblijfsobjecten (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    vbo_id          text not null unique,
    pand_id         text not null references bag_panden(pand_id) on delete cascade,
    gebruiksdoel    text,
    oppervlakte     int,
    geometry        geometry(Point, 28992)
);

create trigger bag_verblijfsobjecten_updated_at before update on bag_verblijfsobjecten
    for each row execute function set_updated_at();

create index on bag_verblijfsobjecten(pand_id);
create index on bag_verblijfsobjecten using gist(geometry);


-- EP-Online energielabels
create table ep_online_labels (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),

    -- koppeling: of op pand- of VBO-niveau
    pand_id             text,
    vbo_id              text,
    postcode            text,
    huisnummer          text,
    huisnummertoevoeging text,

    energielabel        text,                       -- "A", "A+", "B", ..., "G"
    energieklasse       text,
    registratiedatum    date,
    geldig_tot          date,
    raw                 jsonb,

    unique(pand_id),
    unique(vbo_id)
);

create trigger ep_online_labels_updated_at before update on ep_online_labels
    for each row execute function set_updated_at();

create index on ep_online_labels(pand_id);
create index on ep_online_labels(postcode);
