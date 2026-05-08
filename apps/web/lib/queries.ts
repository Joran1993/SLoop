import { queryOptions } from "@tanstack/react-query";
import {
  fetchLeads,
  fetchLead,
  fetchAlerts,
  fetchPipelineSignals,
  fetchFavorites,
} from "./supabase-queries";
import type { LeadFilters } from "./api";

export const leadsQueryOptions = (filters: LeadFilters = {}) =>
  queryOptions({
    queryKey: ["leads", filters],
    queryFn: () => fetchLeads(filters),
    staleTime: 60_000,
  });

export const leadQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["lead", id],
    queryFn: () => fetchLead(id),
    staleTime: 5 * 60_000,
  });

export const alertsQueryOptions = queryOptions({
  queryKey: ["alerts"],
  queryFn: () => fetchAlerts(),
  staleTime: 30_000,
});

export const pipelineSignalsQueryOptions = (bagPandId: string | null) =>
  queryOptions({
    queryKey: ["pipeline-signals", bagPandId],
    queryFn: () => (bagPandId ? fetchPipelineSignals(bagPandId) : []),
    enabled: !!bagPandId,
    staleTime: 5 * 60_000,
  });

export const favoritesQueryOptions = queryOptions({
  queryKey: ["favorites"],
  queryFn: () => fetchFavorites(),
  staleTime: 30_000,
});
