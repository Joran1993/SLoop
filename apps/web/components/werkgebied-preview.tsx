"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { MapPin, ArrowRight, Loader2, AlertCircle } from "lucide-react";

interface Sample {
  adres: string;
  volledig: boolean;
  plaats: string;
  opp_m2: number | null;
  dagen: number;
  tier: string;
}

interface PreviewData {
  total: number;
  by_tier: { vroeg: number; pijplijn: number; kortermijn: number };
  samples: Sample[];
}

const RADIUS_OPTIONS = [10, 25, 50] as const;

function formatDagen(d: number): string {
  if (d <= 1) return "gisteren";
  if (d < 7) return `${d} dagen geleden`;
  if (d < 14) return "1 week geleden";
  if (d < 30) return `${Math.round(d / 7)} weken geleden`;
  const m = Math.round(d / 30);
  return `${m} ${m === 1 ? "maand" : "maanden"} geleden`;
}

function TierPill({ tier }: { tier: string }) {
  if (tier === "eindhoven_vergunning")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Vroeg
      </span>
    );
  if (tier === "pijplijn")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 ring-1 ring-inset ring-blue-200">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />Pijplijn
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />Korte termijn
    </span>
  );
}

export function WerkgebiedPreview() {
  const [q, setQ] = useState("");
  const [radius, setRadius] = useState(25);
  const [data, setData] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function doSearch(query: string, r: number) {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    fetch(`/api/preview?q=${encodeURIComponent(query.trim())}&radius=${r}`)
      .then((res) => res.json())
      .then((json) => {
        if (json.error) {
          setError(json.error);
          setData(null);
        } else {
          setData(json as PreviewData);
        }
      })
      .catch(() => setError("Verbinding mislukt. Probeer het opnieuw."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!q.trim() || q.trim().length < 4) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(q, radius), 600);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, radius]);

  const empty = data && data.total === 0;

  return (
    <div className="rounded-2xl border border-black/[0.08] bg-white p-8 shadow-sm">
      <h3 className="text-[17px] font-semibold tracking-tight">
        Hoeveel sloopkansen staan er nu in uw werkgebied?
      </h3>
      <p className="mt-1.5 text-[14px] text-black/45">
        Voer een postcode of plaatsnaam in en zie direct hoeveel leads er zijn.
      </p>

      {/* Input row */}
      <div className="mt-5 flex flex-wrap gap-2">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch(q, radius)}
          placeholder="Postcode of plaatsnaam"
          className="h-10 flex-1 min-w-[180px] rounded-lg border border-black/[0.12] bg-white px-3.5 text-[14px] placeholder:text-black/35 focus:outline-none focus:ring-2 focus:ring-black/20"
        />
        <select
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="h-10 rounded-lg border border-black/[0.12] bg-white px-3 text-[14px] text-black/70 focus:outline-none focus:ring-2 focus:ring-black/20"
        >
          {RADIUS_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r} km
            </option>
          ))}
        </select>
        <button
          onClick={() => doSearch(q, radius)}
          disabled={loading || !q.trim()}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-black px-4 text-[14px] font-semibold text-white hover:bg-black/80 disabled:opacity-40 transition-colors"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Toon leads"
          )}
        </button>
      </div>

      {/* Error */}
      {error && !loading && (
        <div className="mt-5 flex items-start gap-2.5 rounded-xl bg-red-50 px-4 py-3 text-[13px] text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Empty state */}
      {empty && !loading && (
        <div className="mt-5 rounded-xl bg-black/[0.03] px-5 py-4 text-[14px] text-black/50">
          Op dit moment 0 actieve leads in een straal van {radius} km.{" "}
          Probeer {radius < 50 ? "50 km" : "een andere locatie"} of{" "}
          <a href="mailto:hallo@sloopradar.nl" className="underline underline-offset-2">
            laat ons weten
          </a>{" "}
          dat u deze regio wilt monitoren — bij volume rollen we hier als eerste uit.
        </div>
      )}

      {/* Results */}
      {data && data.total > 0 && !loading && (
        <div className="mt-5 space-y-4">
          {/* Count banner */}
          <div className="flex items-center gap-2.5 rounded-xl bg-black/[0.03] px-4 py-3">
            <MapPin className="h-4 w-4 shrink-0 text-black/40" />
            <span className="text-[14px] font-semibold">
              {data.total} actieve sloopkansen binnen {radius} km
            </span>
          </div>

          {/* Tier breakdown */}
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 px-3 py-2.5 text-center">
              <div className="text-[22px] font-bold leading-none text-emerald-700">{data.by_tier.vroeg}</div>
              <div className="mt-1 text-[11px] text-emerald-600">Vroeg</div>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-3 py-2.5 text-center">
              <div className="text-[22px] font-bold leading-none text-blue-700">{data.by_tier.pijplijn}</div>
              <div className="mt-1 text-[11px] text-blue-600">Pijplijn</div>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/60 px-3 py-2.5 text-center">
              <div className="text-[22px] font-bold leading-none text-amber-700">{data.by_tier.kortermijn}</div>
              <div className="mt-1 text-[11px] text-amber-600">Korte termijn</div>
            </div>
          </div>

          {/* Sample leads */}
          {data.samples.length > 0 && (
            <div className="space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-black/30 mb-2">
                Recente voorbeelden
              </p>
              {data.samples.map((s, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-black/[0.02]"
                >
                  <TierPill tier={s.tier} />
                  <span className={`flex-1 text-[13px] truncate ${s.volledig ? "font-medium" : "font-mono text-black/60"}`}>
                    {s.adres}
                    {s.volledig && s.opp_m2 ? ` — ${s.opp_m2.toLocaleString("nl-NL")} m²` : ""}
                  </span>
                  <span className="shrink-0 text-[12px] text-black/35">{s.plaats}</span>
                  <span className="shrink-0 text-[12px] text-black/30 hidden sm:block">
                    {formatDagen(s.dagen)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* CTA */}
          <Link
            href={`/login?postcode=${encodeURIComponent(q.trim())}`}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-full bg-black py-3.5 text-[14px] font-semibold text-white hover:bg-black/80 transition-colors"
          >
            Zie alle {data.total} leads — 14 dagen gratis
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
