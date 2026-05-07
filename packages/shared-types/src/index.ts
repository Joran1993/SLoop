// Database types gegenereerd via `pnpm generate-types`
// Handmatig exporteer: plan tiers, filter types
export type PlanTier = "starter" | "pro" | "enterprise";
export type PlanStatus = "trialing" | "active" | "past_due" | "canceled";
export type OrgRole = "owner" | "admin" | "member";
export type AlertFrequency = "realtime" | "daily" | "weekly";
export type ExportFormat = "csv" | "json" | "webhook";
export type ParseStatus = "ok" | "partial" | "failed";
export type EigenaarType =
  | "particulier"
  | "woningcorporatie"
  | "gemeente"
  | "bedrijf"
  | "onbekend";

export interface LeadFilters {
  provincie?: string[];
  gemeente?: string[];
  min_score?: number;
  gebruiksdoelen?: string[];
  bouwjaar_min?: number;
  bouwjaar_max?: number;
  oppervlakte_min?: number;
  oppervlakte_max?: number;
  datum_van?: string;
  datum_tot?: string;
}

// Database types worden hier ook geëxporteerd nadat `pnpm generate-types` is gedraaid
export type { Database } from "./database";
