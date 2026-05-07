-- ── Notificaties ───────────────────────────────────────────────────────────

create type delivery_channel as enum ('email', 'webhook');
create type delivery_status as enum ('pending', 'sent', 'failed');

create table alert_subscriptions (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    organization_id uuid not null references organizations(id) on delete cascade,
    user_id         uuid not null references auth.users(id) on delete cascade,

    name            text not null,
    -- Filter jsonb: {"provincies": ["Noord-Holland"], "min_oppervlakte": 500,
    --                "gebruiksdoelen": ["woonfunctie"], "min_score": 60}
    filter          jsonb not null default '{}',
    frequency       alert_frequency not null default 'daily',
    last_sent_at    timestamptz,
    active          boolean not null default true
);

create trigger alert_subscriptions_updated_at before update on alert_subscriptions
    for each row execute function set_updated_at();

create index on alert_subscriptions(organization_id);
create index on alert_subscriptions(user_id);
create index on alert_subscriptions(active, frequency);


create table alert_deliveries (
    id                      uuid primary key default gen_random_uuid(),
    created_at              timestamptz not null default now(),

    alert_subscription_id   uuid not null references alert_subscriptions(id) on delete cascade,
    lead_ids                uuid[] not null,
    sent_at                 timestamptz not null default now(),
    channel                 delivery_channel not null,
    status                  delivery_status not null default 'pending',
    error_message           text,
    retry_count             int not null default 0
);

create index on alert_deliveries(alert_subscription_id);
create index on alert_deliveries(status);
