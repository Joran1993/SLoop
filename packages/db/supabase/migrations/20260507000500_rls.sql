-- ── Row Level Security ────────────────────────────────────────────────────

-- Helper: geef organization_id van ingelogde user (eerste membership)
create or replace function auth_org_id()
returns uuid language sql security definer stable as $$
    select organization_id from org_members
    where user_id = auth.uid()
    limit 1;
$$;

-- Helper: geef plan_tier van ingelogde user
create or replace function auth_plan_tier()
returns plan_tier language sql security definer stable as $$
    select o.plan_tier from organizations o
    join org_members m on m.organization_id = o.id
    where m.user_id = auth.uid()
    limit 1;
$$;

-- Helper: is ingelogde user lid van een actieve (trial/active) org?
create or replace function auth_is_paying()
returns boolean language sql security definer stable as $$
    select exists(
        select 1 from organizations o
        join org_members m on m.organization_id = o.id
        where m.user_id = auth.uid()
        and o.plan_status in ('trialing', 'active')
    );
$$;


-- ── organizations ──────────────────────────────────────────────────────────
alter table organizations enable row level security;

-- Leden zien hun eigen org
create policy "org_members_select" on organizations
    for select using (
        id in (
            select organization_id from org_members where user_id = auth.uid()
        )
    );

-- Alleen owner/admin mag org updaten
create policy "org_owners_update" on organizations
    for update using (
        id in (
            select organization_id from org_members
            where user_id = auth.uid() and role in ('owner', 'admin')
        )
    );


-- ── org_members ────────────────────────────────────────────────────────────
alter table org_members enable row level security;

create policy "org_members_select" on org_members
    for select using (organization_id = auth_org_id());

create policy "org_owners_manage_members" on org_members
    for all using (
        organization_id in (
            select organization_id from org_members
            where user_id = auth.uid() and role in ('owner', 'admin')
        )
    );


-- ── user_preferences ───────────────────────────────────────────────────────
alter table user_preferences enable row level security;

create policy "own_preferences" on user_preferences
    for all using (user_id = auth.uid());


-- ── Brondata: leesbaar voor betalende klanten, schrijfbaar alleen via service-role ──

alter table sloopmeldingen_raw enable row level security;
create policy "paying_users_read_sloopmeldingen" on sloopmeldingen_raw
    for select using (auth_is_paying());

alter table bag_panden enable row level security;
create policy "paying_users_read_bag_panden" on bag_panden
    for select using (auth_is_paying());

alter table bag_verblijfsobjecten enable row level security;
create policy "paying_users_read_bag_vbo" on bag_verblijfsobjecten
    for select using (auth_is_paying());

alter table ep_online_labels enable row level security;
create policy "paying_users_read_ep" on ep_online_labels
    for select using (auth_is_paying());

alter table sloop_leads enable row level security;
create policy "paying_users_read_leads" on sloop_leads
    for select using (auth_is_paying());


-- ── Lead-views: per org ────────────────────────────────────────────────────
alter table lead_views enable row level security;

create policy "own_org_lead_views" on lead_views
    for all using (organization_id = auth_org_id());


-- ── Lead-exports: per org ─────────────────────────────────────────────────
alter table lead_exports enable row level security;

create policy "own_org_lead_exports" on lead_exports
    for all using (organization_id = auth_org_id());


-- ── Alert subscriptions: per org ──────────────────────────────────────────
alter table alert_subscriptions enable row level security;

create policy "own_org_alerts" on alert_subscriptions
    for all using (organization_id = auth_org_id());


-- ── Alert deliveries: via subscription-eigendom ───────────────────────────
alter table alert_deliveries enable row level security;

create policy "own_org_deliveries" on alert_deliveries
    for select using (
        alert_subscription_id in (
            select id from alert_subscriptions where organization_id = auth_org_id()
        )
    );
