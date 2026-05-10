"use client";

import { createClient } from "@/lib/supabase/client";
import type { Lead, LeadFilters, Alert, AlertCreate, PipelineSignal, LeadFavorite } from "./api";

// ── Leads ────────────────────────────────────────────────────────────────────

export async function fetchLeads(
  filters: LeadFilters = {}
): Promise<{ items: Lead[]; total: number; limit: number; offset: number }> {
  const supabase = createClient();
  const limit = filters.limit ?? 200;
  const offset = filters.offset ?? 0;

  let q = supabase
    .from("pipeline_projects_api")
    .select("*", { count: "exact" })
    .order("sort_tier", { ascending: true })
    .order("publicatiedatum", { ascending: false })
    .range(offset, offset + limit - 1);

  if (filters.min_score != null) q = q.gte("score_totaal", filters.min_score);
  if (filters.max_score != null) q = q.lte("score_totaal", filters.max_score);
  if (filters.provincies?.length) q = q.in("provincie", filters.provincies);
  if (filters.gemeente) q = q.ilike("gemeente", `%${filters.gemeente}%`);
  if (filters.min_oppervlakte != null)
    q = q.gte("oppervlakte_m2", filters.min_oppervlakte);
  if (filters.bouwjaar_voor != null)
    q = q.lt("bouwjaar", filters.bouwjaar_voor);
  if (filters.eigenaar_type)
    q = q.eq("eigenaar_type", filters.eigenaar_type);
  if (filters.datum_van)
    q = q.gte("publicatiedatum", filters.datum_van);
  if (filters.with_signals)
    q = q.gt("signal_count", 0);
  // has_sloopvergunning not available in pipeline_projects_api
  if (filters.favorite_ids?.length)
    q = q.in("id", filters.favorite_ids);
  if (filters.gebruiksdoel)
    q = q.contains("gebruiksdoel", [filters.gebruiksdoel]);
  if (filters.source_type)
    q = q.eq("source_type", filters.source_type);

  const { data, error, count } = await q;
  if (error) throw new Error(error.message);

  return {
    items: (data ?? []) as Lead[],
    total: count ?? 0,
    limit,
    offset,
  };
}

export async function fetchLead(id: string): Promise<Lead> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("pipeline_projects_api")
    .select("*")
    .eq("id", id)
    .single();
  if (error) throw new Error(error.message);
  return data as Lead;
}

// ── Pipeline signalen ────────────────────────────────────────────────────────

export async function fetchPipelineSignals(
  bagPandId: string
): Promise<PipelineSignal[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("pipeline_signals")
    .select("id,source,signal_type,signal_strength,signal_time,title,source_url,eigenaar_naam,eigenaar_type")
    .eq("bag_pand_id", bagPandId)
    .order("signal_time", { ascending: false })
    .limit(10);
  if (error) return [];
  return (data ?? []) as PipelineSignal[];
}

// ── Favorieten ───────────────────────────────────────────────────────────────

export async function fetchFavorites(): Promise<LeadFavorite[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("lead_favorites")
    .select("id,lead_id,note,created_at")
    .order("created_at", { ascending: false });
  if (error) return [];
  return (data ?? []) as LeadFavorite[];
}

export async function toggleFavorite(leadId: string): Promise<boolean> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Niet ingelogd");

  const { data: existing } = await supabase
    .from("lead_favorites")
    .select("id")
    .eq("lead_id", leadId)
    .single();

  if (existing) {
    await supabase.from("lead_favorites").delete().eq("id", existing.id);
    return false;
  } else {
    await supabase.from("lead_favorites").insert({ lead_id: leadId, user_id: user.id });
    return true;
  }
}

// ── Alerts ───────────────────────────────────────────────────────────────────

async function getOrgId(): Promise<string> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("org_members")
    .select("organization_id")
    .limit(1)
    .single();
  if (error || !data) throw new Error("Geen organisatie gevonden");
  return data.organization_id as string;
}

async function getUserId(): Promise<string> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Niet ingelogd");
  return user.id;
}

export async function fetchAlerts(): Promise<Alert[]> {
  const supabase = createClient();
  const orgId = await getOrgId();
  const { data, error } = await supabase
    .from("alert_subscriptions")
    .select("*")
    .eq("organization_id", orgId)
    .order("created_at", { ascending: false });
  if (error) throw new Error(error.message);
  return (data ?? []).map((r) => ({
    id: r.id,
    name: r.name,
    filter: r.filter as Alert["filter"],
    frequency: r.frequency,
    active: r.active,
    created_at: r.created_at,
  }));
}

export async function createAlert(body: AlertCreate): Promise<Alert> {
  const supabase = createClient();
  const [orgId, userId] = await Promise.all([getOrgId(), getUserId()]);
  const { data, error } = await supabase
    .from("alert_subscriptions")
    .insert({
      organization_id: orgId,
      user_id: userId,
      name: body.name,
      filter: body.filter,
      frequency: body.frequency,
    })
    .select()
    .single();
  if (error) throw new Error(error.message);
  return {
    id: data.id,
    name: data.name,
    filter: data.filter,
    frequency: data.frequency,
    active: data.active,
    created_at: data.created_at,
  };
}

export async function updateAlert(
  id: string,
  body: Partial<AlertCreate & { active: boolean }>
): Promise<Alert> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("alert_subscriptions")
    .update(body)
    .eq("id", id)
    .select()
    .single();
  if (error) throw new Error(error.message);
  return {
    id: data.id,
    name: data.name,
    filter: data.filter,
    frequency: data.frequency,
    active: data.active,
    created_at: data.created_at,
  };
}

export async function deleteAlert(id: string): Promise<void> {
  const supabase = createClient();
  const { error } = await supabase
    .from("alert_subscriptions")
    .delete()
    .eq("id", id);
  if (error) throw new Error(error.message);
}
