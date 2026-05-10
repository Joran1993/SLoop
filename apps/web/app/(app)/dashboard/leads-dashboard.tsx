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
import { ChevronUp, ChevronDown, Download, SlidersHorizontal, Bookmark } from "lucide-react";
import { leadsQueryOptions, favoritesQueryOptions } from "@/lib/queries";
import { leadsApi, type Lead, type LeadFilters } from "@/lib/api";
import { toggleFavorite } from "@/lib/supabase-queries";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { LeadMap } from "@/components/lead-map";
import { FilterBar } from "./filter-bar";

const columnHelper = createColumnHelper<Lead>();

const NIEUW_CUTOFF_MS = 14 * 24 * 60 * 60 * 1000;

function isNieuw(publicatiedatum: string | null): boolean {
  if (!publicatiedatum) return false;
  return Date.now() - new Date(publicatiedatum).getTime() < NIEUW_CUTOFF_MS;
}

function relativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days <= 0) return "Vandaag";
  if (days === 1) return "Gisteren";
  if (days < 7) return `${days}d`;
  if (days < 30) return `${Math.floor(days / 7)}w`;
  if (days < 365) return `${Math.floor(days / 30)} mnd`;
  return `${Math.floor(days / 365)} jr`;
}

function TierBadge({ sourceType }: { sourceType: string | null | undefined }) {
  if (sourceType === "eindhoven_vergunning") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:ring-emerald-800">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
        Vroeg
      </span>
    );
  }
  if (sourceType === "pijplijn") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 ring-1 ring-inset ring-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:ring-blue-800">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
        Pijplijn
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-semibold text-stone-600 ring-1 ring-inset ring-stone-200 dark:bg-stone-800/40 dark:text-stone-400 dark:ring-stone-700">
      <span className="h-1.5 w-1.5 rounded-full bg-stone-400 shrink-0" />
      Laat
    </span>
  );
}

function FavButton({ id, isFav, onToggle }: { id: string; isFav: boolean; onToggle: (id: string) => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onToggle(id); }}
      className={`rounded p-1 transition-colors ${isFav ? "text-amber-500 hover:text-amber-600" : "text-muted-foreground/30 hover:text-muted-foreground"}`}
      title={isFav ? "Verwijder uit favorieten" : "Sla op als favoriet"}
    >
      <Bookmark className={`h-3.5 w-3.5 ${isFav ? "fill-current" : ""}`} />
    </button>
  );
}

const columns = [
  columnHelper.accessor("source_type", {
    id: "tier",
    header: "",
    cell: (info) => <TierBadge sourceType={info.getValue()} />,
    enableSorting: false,
  }),
  columnHelper.accessor("adres", {
    header: "Adres",
    cell: (info) => {
      const nieuw = isNieuw(info.row.original.publicatiedatum);
      const st = info.row.original.source_type;
      return (
        <span className="flex items-center gap-1.5">
          <span className="font-medium">{info.getValue() ?? "—"}</span>
          {nieuw && (
            <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
              st === "eindhoven_vergunning" ? "bg-emerald-100 text-emerald-700" :
              st === "pijplijn" ? "bg-blue-100 text-blue-700" :
              "bg-muted text-muted-foreground"
            }`}>
              Nieuw
            </span>
          )}
        </span>
      );
    },
  }),
  columnHelper.accessor("gemeente", {
    header: "Gemeente",
    cell: (info) => <span className="text-sm text-muted-foreground">{info.getValue() ?? "—"}</span>,
  }),
  columnHelper.accessor("oppervlakte_m2", {
    header: "Opp.",
    cell: (info) => {
      const v = info.getValue();
      return (
        <span className="text-sm text-muted-foreground tabular-nums">
          {v ? `${v.toLocaleString("nl-NL")} m²` : "—"}
        </span>
      );
    },
    sortingFn: "basic",
  }),
  columnHelper.accessor("bouwjaar", {
    header: "Bouwjaar",
    cell: (info) => (
      <span className="text-sm text-muted-foreground tabular-nums">{info.getValue() ?? "—"}</span>
    ),
  }),
  columnHelper.accessor("publicatiedatum", {
    header: "Signaal",
    cell: (info) => (
      <span className="text-sm text-muted-foreground tabular-nums">{relativeDate(info.getValue())}</span>
    ),
  }),
  columnHelper.accessor("eigenaar_naam", {
    header: "Eigenaar",
    cell: (info) => {
      const naam = info.getValue();
      const tel = info.row.original.contact_telefoon;
      return (
        <span className="flex items-center gap-1.5">
          {tel && (
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" title="Telefoonnummer beschikbaar" />
          )}
          <span className={`text-sm truncate max-w-[120px] ${naam ? "font-medium" : "text-muted-foreground"}`}>
            {naam ?? "—"}
          </span>
        </span>
      );
    },
  }),
  columnHelper.accessor("signal_count", {
    header: "Sig.",
    cell: (info) => {
      const v = info.getValue();
      if (!v || v === 0) return null;
      return (
        <span className="inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:ring-indigo-800">
          {v}
        </span>
      );
    },
    sortingFn: "basic",
  }),
];

export function LeadsDashboard() {
  const [filters, setFilters] = useState<LeadFilters>({ limit: 200 });
  const [sorting, setSorting] = useState<SortingState>([
    { id: "oppervlakte_m2", desc: true },
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
    const vroeg = leads.filter((l) => l.source_type === "eindhoven_vergunning").length;
    const pijplijn = leads.filter((l) => l.source_type === "pijplijn").length;
    const provinceCounts: Record<string, number> = {};
    leads.forEach((l) => { if (l.provincie) provinceCounts[l.provincie] = (provinceCounts[l.provincie] ?? 0) + 1; });
    const topProvincie = Object.entries(provinceCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
    return { avgScore, withSignals, vroeg, pijplijn, topProvincie };
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
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-semibold">
            {isLoading ? (
              <span className="text-muted-foreground font-normal">Laden…</span>
            ) : (
              <>
                {(data?.total ?? 0).toLocaleString("nl-NL")}
                <span className="ml-1 font-normal text-muted-foreground text-xs">leads</span>
              </>
            )}
            {isFetching && !isLoading && (
              <span className="ml-1.5 inline-block h-3 w-3 rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground animate-spin" />
            )}
          </span>
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
              showFilters
                ? "border-foreground/20 bg-foreground/5 text-foreground"
                : "border-border text-muted-foreground hover:border-foreground/20 hover:text-foreground"
            }`}
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
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:border-foreground/20 hover:text-foreground transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Export
        </button>
      </div>

      {/* Filter bar (collapsible) */}
      {showFilters && (
        <FilterBar filters={filters} onChange={setFilters} />
      )}

      {/* Stats strip */}
      {stats && !isLoading && (
        <div className="flex items-center gap-0.5 border-b border-border px-3 py-1 shrink-0">
          {stats.vroeg > 0 && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.source_type === "eindhoven_vergunning"
                    ? { ...f, source_type: undefined }
                    : { ...f, source_type: "eindhoven_vergunning" }
                )
              }
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                filters.source_type === "eindhoven_vergunning"
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
              <span className="font-semibold tabular-nums">{stats.vroeg}</span>
              <span>vroeg</span>
            </button>
          )}
          {stats.pijplijn > 0 && (
            <button
              onClick={() =>
                setFilters((f) =>
                  f.source_type === "pijplijn"
                    ? { ...f, source_type: undefined }
                    : { ...f, source_type: "pijplijn" }
                )
              }
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                filters.source_type === "pijplijn"
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
              <span className="font-semibold tabular-nums">{stats.pijplijn}</span>
              <span>pijplijn</span>
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
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                filters.with_signals
                  ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/30 dark:text-indigo-400"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 shrink-0" />
              <span className="font-semibold tabular-nums">{stats.withSignals}</span>
              <span>signalen</span>
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
              className={`rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                filters.provincies?.includes(stats.topProvincie)
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              {stats.topProvincie}
            </button>
          )}
          {stats.avgScore != null && (
            <span className="ml-auto text-xs text-muted-foreground pr-1">
              Ø <span className="font-medium text-foreground tabular-nums">{stats.avgScore}</span>
            </span>
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
              <span className="text-muted-foreground">Pipeline signalen</span>
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
            <div className="p-4 text-sm text-destructive">{error.message}</div>
          )}
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-background/95 backdrop-blur-sm z-10 border-b border-border">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      className="text-left text-[11px] font-medium tracking-wide text-muted-foreground px-4 py-3 whitespace-nowrap cursor-pointer select-none hover:text-foreground uppercase"
                    >
                      <span className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === "asc" && (
                          <ChevronUp className="h-3 w-3" />
                        )}
                        {header.column.getIsSorted() === "desc" && (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </span>
                    </th>
                  ))}
                  <th className="px-1 py-3 w-8" />
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => {
                const isSelected = selectedId === row.original.id;
                const isHovered = hoveredId === row.original.id;
                return (
                  <tr
                    key={row.id}
                    onClick={() =>
                      setSelectedId((prev) =>
                        prev === row.original.id ? null : row.original.id
                      )
                    }
                    onMouseEnter={() => setHoveredId(row.original.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    className={`cursor-pointer border-b border-border/50 transition-colors ${
                      isSelected
                        ? "bg-amber-50/60 dark:bg-amber-950/20"
                        : isHovered
                        ? "bg-muted/50"
                        : ""
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                    <td className="px-1 py-3">
                      <FavButton
                        id={row.original.id}
                        isFav={favoriteIds.has(row.original.id)}
                        onToggle={(id) => favMutation.mutate(id)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {leads.length === 0 && !isLoading && (
            <div className="flex-1 flex items-center justify-center py-16 text-sm text-muted-foreground">
              Geen leads gevonden
            </div>
          )}
          {leads.length > 0 && (data?.total ?? 0) > leads.length && (
            <div className="flex justify-center py-4">
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
