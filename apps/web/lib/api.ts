import { createClient } from "@/lib/supabase/client";

export interface SloopIndicatoren {
  totaal_ton: number;
  residuwaarde_eur: number;
  asbest_m2?: number;
  sloopkosten_min: number;
  sloopkosten_max: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getAuthHeader(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const authHeaders = await getAuthHeader();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(init.headers as Record<string, string> | undefined),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---- Leads ----

export interface LeadFilters {
  provincies?: string[];
  gemeente?: string;
  min_score?: number;
  max_score?: number;
  min_oppervlakte?: number;
  bouwjaar_voor?: number;
  gebruiksdoel?: string;
  eigenaar_type?: string;
  datum_van?: string;
  with_signals?: boolean;
  with_sloopvergunning?: boolean;
  favorite_ids?: string[];
  source_type?: string;
  limit?: number;
  offset?: number;
}

export interface Lead {
  id: string;
  publicatie_id: string;
  eigenaar_type: string | null;
  eigenaar_naam: string | null;
  adres: string | null;
  gemeente: string | null;
  provincie: string | null;
  postcode: string | null;
  bouwjaar: number | null;
  oppervlakte_m2: number | null;
  energielabel: string | null;
  score_totaal: number | null;
  score_asbest: number | null;
  score_omvang: number | null;
  score_bereikbaarheid: number | null;
  score_circulair: number | null;
  gebruiksdoel: string[] | null;
  longitude: number | null;
  latitude: number | null;
  publicatiedatum: string | null;
  titel: string | null;
  bag_pand_id: string | null;
  source_url: string | null;
  source_type: string | null;
  sort_tier: number | null;
  tender_window_estimate_weeks: number | null;
  signal_count: number | null;
  has_sloopvergunning: boolean | null;
  bag_pand_status: string | null;
  contact_naam: string | null;
  contact_website: string | null;
  contact_telefoon: string | null;
  contact_email: string | null;
  materiaal_volume_estimate: SloopIndicatoren | null;
}

export interface PipelineSignal {
  id: string;
  source: string;
  signal_type: string;
  signal_strength: "high" | "medium" | "low";
  signal_time: string;
  title: string | null;
  source_url: string | null;
  eigenaar_naam: string | null;
  eigenaar_type: string | null;
}

export interface LeadsResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export function buildLeadsQuery(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.provincies?.length)
    filters.provincies.forEach((p) => params.append("provincies", p));
  if (filters.min_score != null)
    params.set("min_score", String(filters.min_score));
  if (filters.max_score != null)
    params.set("max_score", String(filters.max_score));
  if (filters.min_oppervlakte != null)
    params.set("min_oppervlakte", String(filters.min_oppervlakte));
  if (filters.bouwjaar_voor != null)
    params.set("bouwjaar_voor", String(filters.bouwjaar_voor));
  if (filters.gebruiksdoel)
    params.set("gebruiksdoel", filters.gebruiksdoel);
  if (filters.eigenaar_type)
    params.set("eigenaar_type", filters.eigenaar_type);
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const leadsApi = {
  list: (filters: LeadFilters = {}) =>
    apiFetch<LeadsResponse>(`/api/leads${buildLeadsQuery(filters)}`),
  get: (id: string) => apiFetch<Lead>(`/api/leads/${id}`),
  exportCsv: async (filters: LeadFilters = {}) => {
    const authHeaders = await getAuthHeader();
    const params = new URLSearchParams({ format: "csv" });
    if (filters.min_score != null) params.set("min_score", String(filters.min_score));
    if (filters.gemeente) params.set("gemeente", filters.gemeente);
    if (filters.provincies?.length) filters.provincies.forEach((p) => params.append("provincie", p));
    if (filters.with_sloopvergunning) params.set("with_sloopvergunning", "true");
    if (filters.with_signals) params.set("with_signals", "true");
    if (filters.eigenaar_type) params.set("eigenaar_type", filters.eigenaar_type);
    if (filters.gebruiksdoel) params.set("gebruiksdoel", filters.gebruiksdoel);
    if (filters.datum_van) params.set("datum_van", filters.datum_van);
    const res = await fetch(
      `${API_BASE}/api/leads/export?${params.toString()}`,
      { headers: authHeaders }
    );
    if (!res.ok) throw new Error(`${res.status}`);
    return res.blob();
  },
};

// ---- Alerts ----

export interface AlertFilter {
  provincies?: string[];
  min_oppervlakte?: number;
  min_score?: number;
  only_with_vergunning?: boolean;
  gebruiksdoelen?: string[];
}

export interface Alert {
  id: string;
  name: string;
  filter: AlertFilter;
  frequency: "daily" | "weekly";
  active: boolean;
  created_at: string;
}

export interface AlertCreate {
  name: string;
  filter: AlertFilter;
  frequency: "daily" | "weekly";
}

export const alertsApi = {
  list: () => apiFetch<Alert[]>("/api/alerts"),
  create: (body: AlertCreate) =>
    apiFetch<Alert>("/api/alerts", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: Partial<AlertCreate & { active: boolean }>) =>
    apiFetch<Alert>(`/api/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    apiFetch<void>(`/api/alerts/${id}`, { method: "DELETE" }),
};

// ---- Favorites ----

export interface LeadFavorite {
  id: string;
  lead_id: string;
  note: string | null;
  created_at: string;
}

// ---- Billing ----

export interface CheckoutBody {
  plan_tier: "pro" | "enterprise";
  redirect_url: string;
}

export const billingApi = {
  checkout: (body: CheckoutBody) =>
    apiFetch<{ checkout_url: string }>("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  portal: () => apiFetch<{ portal_url: string }>("/api/billing/portal"),
};
