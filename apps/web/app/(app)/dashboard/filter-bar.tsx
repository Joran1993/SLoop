"use client";

import { Radio, ShieldCheck } from "lucide-react";
import { useState, useEffect } from "react";
import { type LeadFilters } from "@/lib/api";

const PERIODE_OPTIONS = [
  { label: "7 dagen", days: 7 },
  { label: "30 dagen", days: 30 },
  { label: "90 dagen", days: 90 },
  { label: "Alles", days: null },
] as const;

const GEBRUIKSDOELEN = [
  { value: "woonfunctie", label: "Wonen" },
  { value: "kantoorfunctie", label: "Kantoor" },
  { value: "industriefunctie", label: "Industrie" },
  { value: "winkelfunctie", label: "Winkel" },
  { value: "onderwijsfunctie", label: "Onderwijs" },
  { value: "gezondheidszorgfunctie", label: "Zorg" },
] as const;

const EIGENAAR_TYPES = [
  { value: "corporatie_waarschijnlijk", label: "Corporatie" },
  { value: "bedrijf", label: "Bedrijf" },
  { value: "overheid_instelling", label: "Overheid" },
  { value: "particulier_of_corporatie", label: "Particulier" },
] as const;

const PROVINCIES = [
  "Drenthe",
  "Flevoland",
  "Friesland",
  "Gelderland",
  "Groningen",
  "Limburg",
  "Noord-Brabant",
  "Noord-Holland",
  "Overijssel",
  "Utrecht",
  "Zeeland",
  "Zuid-Holland",
];

interface FilterBarProps {
  filters: LeadFilters;
  onChange: (f: LeadFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  const [gemeenteInput, setGemeenteInput] = useState(filters.gemeente ?? "");

  useEffect(() => {
    setGemeenteInput(filters.gemeente ?? "");
  }, [filters.gemeente]);

  useEffect(() => {
    const t = setTimeout(() => {
      onChange({ ...filters, gemeente: gemeenteInput || undefined, offset: 0 });
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gemeenteInput]);

  function update(patch: Partial<LeadFilters>) {
    onChange({ ...filters, ...patch, offset: 0 });
  }

  function toggleProvincie(p: string) {
    const current = filters.provincies ?? [];
    const next = current.includes(p)
      ? current.filter((x) => x !== p)
      : [...current, p];
    update({ provincies: next.length ? next : undefined });
  }

  function setPeriode(days: number | null) {
    if (days === null) {
      update({ datum_van: undefined });
    } else {
      const d = new Date();
      d.setDate(d.getDate() - days);
      update({ datum_van: d.toISOString().slice(0, 10) });
    }
  }

  function activePeriodeDays(): number | null {
    if (!filters.datum_van) return null;
    const diffMs = Date.now() - new Date(filters.datum_van).getTime();
    const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
    return [7, 30, 90].includes(days) ? days : -1;
  }

  return (
    <div className="border-b border-border bg-muted/30 px-4 py-3 space-y-3 shrink-0">
      {/* Periode */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground mr-1">Periode</span>
        {PERIODE_OPTIONS.map(({ label, days }) => {
          const active = days === null
            ? !filters.datum_van
            : activePeriodeDays() === days;
          return (
            <button
              key={label}
              onClick={() => setPeriode(days)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Gemeente */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Gemeente</span>
        <input
          type="text"
          value={gemeenteInput}
          onChange={(e) => setGemeenteInput(e.target.value)}
          placeholder="bijv. Amsterdam"
          className="h-7 w-36 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </div>

      {/* Score range */}
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Min. score
          <input
            type="number"
            min={0}
            max={100}
            value={filters.min_score ?? ""}
            onChange={(e) =>
              update({
                min_score: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            className="w-16 h-7 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>

        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Min. opp. (m²)
          <input
            type="number"
            min={0}
            value={filters.min_oppervlakte ?? ""}
            onChange={(e) =>
              update({
                min_oppervlakte: e.target.value
                  ? Number(e.target.value)
                  : undefined,
              })
            }
            className="w-20 h-7 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>

        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Bouwjaar voor
          <input
            type="number"
            min={1800}
            max={2024}
            value={filters.bouwjaar_voor ?? ""}
            onChange={(e) =>
              update({
                bouwjaar_voor: e.target.value
                  ? Number(e.target.value)
                  : undefined,
              })
            }
            className="w-20 h-7 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
      </div>

      {/* Bron filter */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground mr-1">Bron</span>
        {[
          { value: "koop_sloopmelding", label: "KOOP sloopmelding" },
          { value: "eindhoven_vergunning", label: "Eindhoven vergunning" },
        ].map(({ value, label }) => {
          const active = filters.source_type === value;
          return (
            <button
              key={value}
              onClick={() => update({ source_type: active ? undefined : value })}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Signalen & vergunning filter */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => update({ with_sloopvergunning: filters.with_sloopvergunning ? undefined : true })}
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
            filters.with_sloopvergunning
              ? "bg-red-600 text-white"
              : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
          }`}
        >
          <ShieldCheck className="h-3 w-3" />
          Vergunning verleend
        </button>
        <button
          onClick={() => update({ with_signals: filters.with_signals ? undefined : true })}
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
            filters.with_signals
              ? "bg-indigo-600 text-white"
              : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
          }`}
        >
          <Radio className="h-3 w-3" />
          Met signalen
        </button>
      </div>

      {/* Gebruiksdoel */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground mr-1">Type pand</span>
        {GEBRUIKSDOELEN.map(({ value, label }) => {
          const active = filters.gebruiksdoel === value;
          return (
            <button
              key={value}
              onClick={() => update({ gebruiksdoel: active ? undefined : value })}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Eigenaar type */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground mr-1">Eigenaar</span>
        {EIGENAAR_TYPES.map(({ value, label }) => {
          const active = filters.eigenaar_type === value;
          return (
            <button
              key={value}
              onClick={() =>
                update({ eigenaar_type: active ? undefined : value })
              }
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Provincies */}
      <div className="flex flex-wrap gap-1.5">
        {PROVINCIES.map((p) => {
          const active = (filters.provincies ?? []).includes(p);
          return (
            <button
              key={p}
              onClick={() => toggleProvincie(p)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {p}
            </button>
          );
        })}
      </div>
    </div>
  );
}
