"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, Download, SlidersHorizontal, Radio, ShieldCheck, Bookmark } from "lucide-react";
import { leadsQueryOptions, favoritesQueryOptions } from "@/lib/queries";
import { leadsApi, type Lead, type LeadFilters } from "@/lib/api";
import { toggleFavorite } from "@/lib/supabase-queries";
import { ScoreBadge } from "@/components/score-badge";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { LeadMap } from "@/components/lead-map";
import { FilterBar } from "./filter-bar";

const columnHelper = createColumnHelper<Lead>();

const NIEUW_CUTOFF_MS = 48 * 60 * 60 * 1000;

function isNieuw(publicatiedatum: string | null): boolean {
  if (!publicatiedatum) return false;
  return Date.now() - new Date(publicatiedatum).getTime() < NIEUW_CUTOFF_MS;
}

function FavButton({ id, isFav, onToggle }: { id: string; isFav: boolean; onToggle: (id: string) => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onToggle(id); }}
      className={`rounded p-1 transition-colors ${isFav ? "text-amber-500 hover:text-amber-600" : "text-muted-foreground/40 hover:text-muted-foreground"}`}
      title={isFav ? "Verwijder uit favorieten" : "Sla op als favoriet"}
    >
      <Bookmark className={`h-3.5 w-3.5 ${isFav ? "fill-current" : ""}`} />
    </button>
  );
}

const columns = [
  columnHelper.accessor("adres", {
    header: "Adres",
    cell: (info) => (
      <span className="flex items-center gap-1.5">
        <span className="font-medium">{info.getValue() ?? "—"}</span>
        {info.row.original.has_sloopvergunning && (
          <span className="inline-flex items-center gap-0.5 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-700 dark:bg-red-900/30 dark:text-red-400">
            <ShieldCheck className="h-2.5 w-2.5" />
            Vergunning
          </span>
        )}
        {isNieuw(info.row.original.publicatiedatum) && (
          <span className="inline-flex items-center rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
            Nieuw
          </span>
        )}
      </span>
    ),
  }),
  columnHelper.accessor("gemeente", {
    header: "Gemeente",
    cell: (info) => info.getValue() ?? "—",
  }),
  columnHelper.accessor("provincie", {
    header: "Provincie",
    cell: (info) => info.getValue() ?? "—",
  }),
  columnHelper.accessor("bouwjaar", {
    header: "Bouwjaar",
    cell: (info) => info.getValue() ?? "—",
  }),
  columnHelper.accessor("oppervlakte_m2", {
    header: "Opp. (m²)",
    cell: (info) =>
      info.getValue() != null
        ? info.getValue()!.toLocaleString("nl-NL")
        : "—",
  }),
  columnHelper.accessor("energielabel", {
    header: "Label",
    cell: (info) => info.getValue() ?? "—",
  }),
  columnHelper.accessor("publicatiedatum", {
    header: "Gepubliceerd",
    cell: (info) => {
      const v = info.getValue();
      if (!v) return "—";
      return new Date(v).toLocaleDateString("nl-NL", { day: "numeric", month: "short", year: "numeric" });
    },
  }),
  columnHelper.accessor("score_totaal", {
    header: "Score",
    cell: (info) => (
      <span className="flex items-center gap-1.5">
        <ScoreBadge score={info.getValue()} />
        {(info.row.original.signal_count ?? 0) > 0 && (
          <span className="inline-flex items-center gap-0.5 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
            <Radio className="h-2.5 w-2.5" />
            {info.row.original.signal_count}
          </span>
        )}
      </span>
    ),
    sortingFn: "basic",
  }),
];

export function LeadsDashboard() {
  const [filters, setFilters] = useState<LeadFilters>({ limit: 200 });
  const [sorting, setSorting] = useState<SortingState>([
    { id: "score_totaal", desc: true },
  ]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, isFetching, error } = useQuery({
    ...leadsQueryOptions(filters),
    placeholderData: keepPreviousData,
  });
  const leads = data?.items ?? [];
  const qc = useQueryClient();
  const { data: favorites = [] } = useQuery(favoritesQueryOptions);
  const favoriteIds = useMemo(() => new Set(favorites.map((f) => f.lead_id)), [favorites]);
  const favMutation = useMutation({
    mutationFn: (id: string) => toggleFavorite(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["favorites"] }),
  });

  const stats = useMemo(() => {
    if (!leads.length) return null;
    const withScore = leads.filter((l) => l.score_totaal != null);
    const avgScore = withScore.length
      ? Math.round(withScore.reduce((s, l) => s + l.score_totaal!, 0) / withScore.length)
      : null;
    const withSignals = leads.filter((l) => (l.signal_count ?? 0) > 0).length;
    const withVergunning = leads.filter((l) => l.has_sloopvergunning).length;
    const provinceCounts: Record<string, number> = {};
    leads.forEach((l) => { if (l.provincie) provinceCounts[l.provincie] = (provinceCounts[l.provincie] ?? 0) + 1; });
    const topProvincie = Object.entries(provinceCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
    return { avgScore, withSignals, withVergunning, topProvincie };
  }, [leads]);

  const table = useReactTable({
    data: leads,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  async function handleExport() {
    try {
      const blob = await leadsApi.exportCsv(filters);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sloopradar-leads.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export niet beschikbaar op uw abonnement.");
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Topbar */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium flex items-center gap-1.5">
            {isLoading ? "Laden…" : `${data?.total ?? 0} leads`}
            {isFetching && !isLoading && (
              <span className="inline-block h-3 w-3 rounded-full border-2 border-muted-foreground border-t-transparent animate-spin" />
            )}
          </span>
          <button
            onClick={() => setShowFilters((v) => !v)}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filter
          </button>
          {favorites.length > 0 && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.favorite_ids
                    ? { limit: f.limit }
                    : { ...f, favorite_ids: [...favoriteIds] }
                )
              }
              className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
                filters.favorite_ids
                  ? "border-amber-400 bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              <Bookmark className={`h-3.5 w-3.5 ${filters.favorite_ids ? "fill-current" : ""}`} />
              {favorites.length}
            </button>
          )}
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </button>
      </div>

      {/* Filter bar (collapsible) */}
      {showFilters && (
        <FilterBar filters={filters} onChange={setFilters} />
      )}

      {/* Stats strip */}
      {stats && !isLoading && (
        <div className="flex items-center gap-6 border-b border-border bg-muted/30 px-4 py-1.5 text-xs text-muted-foreground shrink-0">
          {stats.avgScore != null && (
            <span>Gem. score: <span className="font-medium text-foreground">{stats.avgScore}</span></span>
          )}
          {stats.withVergunning > 0 && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.with_sloopvergunning
                    ? { ...f, with_sloopvergunning: undefined }
                    : { ...f, with_sloopvergunning: true }
                )
              }
              className={`flex items-center gap-1 transition-colors rounded px-1 -mx-1 ${
                filters.with_sloopvergunning
                  ? "text-red-600 dark:text-red-400 font-medium"
                  : "hover:text-foreground"
              }`}
            >
              <ShieldCheck className="h-3 w-3 text-red-500" />
              <span className="font-medium text-foreground">{stats.withVergunning}</span> met vergunning
            </button>
          )}
          {stats.withSignals > 0 && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.with_signals
                    ? { ...f, with_signals: undefined }
                    : { ...f, with_signals: true }
                )
              }
              className={`flex items-center gap-1 transition-colors rounded px-1 -mx-1 ${
                filters.with_signals
                  ? "text-indigo-600 dark:text-indigo-400 font-medium"
                  : "hover:text-foreground"
              }`}
            >
              <Radio className="h-3 w-3 text-indigo-500" />
              <span className="font-medium text-foreground">{stats.withSignals}</span> met signalen
            </button>
          )}
          {stats.topProvincie && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.provincies?.includes(stats.topProvincie!)
                    ? { ...f, provincies: undefined }
                    : { ...f, provincies: [stats.topProvincie!] }
                )
              }
              className={`transition-colors rounded px-1 -mx-1 ${
                filters.provincies?.includes(stats.topProvincie)
                  ? "text-foreground font-medium"
                  : "hover:text-foreground"
              }`}
            >
              Meeste in: <span className="font-medium text-foreground">{stats.topProvincie}</span>
            </button>
          )}
        </div>
      )}

      {/* Main content: map + table + detail panel */}
      <div className="flex flex-1 min-h-0">
        {/* Map (left half) */}
        <div className="relative w-1/2 shrink-0">
          {/* Map legend */}
          <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1 rounded-lg border border-border bg-card/90 backdrop-blur-sm px-2.5 py-2 text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#1c1c1c]" />
              <span className="text-muted-foreground">Sloopmelding</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#6366f1]" />
              <span className="text-muted-foreground">Met pipeline signalen</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#dc2626]" />
              <span className="text-muted-foreground">Vergunning verleend</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#d97706]" />
              <span className="text-muted-foreground">Geselecteerd</span>
            </div>
          </div>
          <LeadMap
            leads={leads}
            hoveredId={hoveredId}
            selectedId={selectedId}
            onLeadClick={(id) =>
              setSelectedId((prev) => (prev === id ? null : id))
            }
          />
        </div>

        {/* Table */}
        <div className={`flex flex-1 flex-col min-w-0 border-l border-border overflow-auto transition-opacity duration-150 ${isFetching && !isLoading ? "opacity-60" : "opacity-100"}`}>
          {error && (
            <div className="p-4 text-sm text-destructive">
              {error.message}
            </div>
          )}
          <table className="w-full text-sm border-collapse">
            <thead className="sticky top-0 bg-muted/60 backdrop-blur-sm z-10">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      className="text-left text-xs font-medium text-muted-foreground px-3 py-2 whitespace-nowrap cursor-pointer select-none hover:text-foreground border-b border-border"
                    >
                      <span className="flex items-center gap-1">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getIsSorted() === "asc" && (
                          <ChevronUp className="h-3 w-3" />
                        )}
                        {header.column.getIsSorted() === "desc" && (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </span>
                    </th>
                  ))}
                  <th className="border-b border-border px-1 py-2 w-8" />
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() =>
                    setSelectedId((prev) =>
                      prev === row.original.id ? null : row.original.id
                    )
                  }
                  onMouseEnter={() => setHoveredId(row.original.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`cursor-pointer border-b border-border/60 transition-colors ${
                    selectedId === row.original.id
                      ? "bg-accent/10"
                      : hoveredId === row.original.id
                      ? "bg-muted/60"
                      : "hover:bg-muted/30"
                  }`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2 whitespace-nowrap">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                  <td className="px-1 py-2">
                    <FavButton
                      id={row.original.id}
                      isFav={favoriteIds.has(row.original.id)}
                      onToggle={(id) => favMutation.mutate(id)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {leads.length === 0 && !isLoading && (
            <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
              Geen leads gevonden
            </div>
          )}
          {leads.length > 0 && (data?.total ?? 0) > leads.length && (
            <div className="flex justify-center py-3">
              <button
                onClick={() => setFilters((f) => ({ ...f, limit: (f.limit ?? 200) + 200 }))}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {leads.length} van {data?.total} — meer laden
              </button>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedId && (
          <LeadDetailPanel
            leadId={selectedId}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>
    </div>
  );
}
