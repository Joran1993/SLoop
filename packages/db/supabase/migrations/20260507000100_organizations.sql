-- ── Tenant / auth tabellen ─────────────────────────────────────────────────

create type plan_tier as enum ('starter', 'pro', 'enterprise');
create type plan_status as enum ('trialing', 'active', 'past_due', 'canceled');
create type org_role as enum ('owner', 'admin', 'member');
create type alert_frequency as enum ('realtime', 'daily', 'weekly');
create type export_format as enum ('csv', 'json', 'webhook');

create table organizations (
    id                      uuid primary key default gen_random_uuid(),
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    naam                    text not null,
    kvk_nummer              text,
    billing_email           text not null,
    plan_tier               plan_tier not null default 'starter',
    plan_status             plan_status not null default 'trialing',
    mollie_customer_id      text,
    mollie_subscription_id  text,
    trial_ends_at           timestamptz,
    current_period_end      timestamptz,
    -- Enterprise: eigen scoring-gewichten; null = systeem-defaults gebruiken
    scoring_weights         jsonb
);

create table org_members (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    organization_id uuid not null references organizations(id) on delete cascade,
    user_id         uuid not null references auth.users(id) on delete cascade,
    role            org_role not null default 'member',
    invited_at      timestamptz not null default now(),
    accepted_at     timestamptz,
    unique(organization_id, user_id)
);

create table user_preferences (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    user_id             uuid not null references auth.users(id) on delete cascade unique,
    notification_email  text,
    daily_digest        boolean not null default true,
    alert_filters       jsonb
);

-- updated_at trigger (herbruikbaar)
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger organizations_updated_at before update on organizations
    for each row execute function set_updated_at();
create trigger org_members_updated_at before update on org_members
    for each row execute function set_updated_at();
create trigger user_preferences_updated_at before update on user_preferences
    for each row execute function set_updated_at();

-- Index: snel zoeken op user → org
create index on org_members(user_id);
create index on org_members(organization_id);
