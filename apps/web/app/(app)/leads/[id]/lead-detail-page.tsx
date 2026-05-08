"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { leadQueryOptions, pipelineSignalsQueryOptions } from "@/lib/queries";
import { ScoreBadge } from "@/components/score-badge";
import { signalTypeLabel } from "@/lib/signal-labels";

export function LeadDetailPage({ id }: { id: string }) {
  const { data: lead, isLoading } = useQuery(leadQueryOptions(id));
  const { data: signals = [] } = useQuery(
    pipelineSignalsQueryOptions(lead?.bag_pand_id ?? null)
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Laden…
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm text-muted-foreground">Lead niet gevonden.</p>
        <Link href="/dashboard" className="text-xs text-accent hover:underline">
          ← Terug naar dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* Back */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Terug naar dashboard
      </Link>

      {/* Header */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        {lead.has_sloopvergunning && (
          <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2 dark:bg-red-950/30 dark:border-red-900">
            <ShieldCheck className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-red-700 dark:text-red-400">Sloopvergunning verleend</p>
              <p className="text-[11px] text-red-600/80 dark:text-red-500">BAG-status bevestigd — sloop aanstaande</p>
            </div>
          </div>
        )}

        <div>
          <h1 className="text-lg font-semibold">{lead.adres ?? "Onbekend adres"}</h1>
          <p className="text-sm text-muted-foreground">
            {lead.gemeente}{lead.provincie ? ` · ${lead.provincie}` : ""}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-3xl font-bold tabular-nums">
              {lead.score_totaal != null ? Math.round(lead.score_totaal) : "—"}
            </span>
            <span className="text-xs text-muted-foreground">/ 100</span>
          </div>
          <ScoreBadge score={lead.score_totaal} />
        </div>

        {/* Details */}
        <dl className="grid grid-cols-2 gap-3 text-sm">
          {lead.bouwjaar && (
            <div><dt className="text-xs text-muted-foreground">Bouwjaar</dt><dd className="font-medium">{lead.bouwjaar}</dd></div>
          )}
          {lead.oppervlakte_m2 && (
            <div><dt className="text-xs text-muted-foreground">Oppervlakte</dt><dd className="font-medium">{lead.oppervlakte_m2.toLocaleString("nl-NL")} m²</dd></div>
          )}
          {lead.energielabel && (
            <div><dt className="text-xs text-muted-foreground">Energielabel</dt><dd className="font-medium">{lead.energielabel}</dd></div>
          )}
          {lead.publicatiedatum && (
            <div>
              <dt className="text-xs text-muted-foreground">Publicatiedatum</dt>
              <dd className="font-medium">
                {new Date(lead.publicatiedatum).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" })}
              </dd>
            </div>
          )}
          {lead.tender_window_estimate_weeks != null && (
            <div><dt className="text-xs text-muted-foreground">Actievenster</dt><dd className="font-medium">±{lead.tender_window_estimate_weeks} weken</dd></div>
          )}
          {(lead.signal_count ?? 0) > 0 && (
            <div><dt className="text-xs text-muted-foreground">Pipeline signalen</dt><dd className="font-medium">{lead.signal_count}</dd></div>
          )}
        </dl>

        {lead.source_url && (
          <a
            href={lead.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Bekijk originele publicatie
          </a>
        )}
      </div>

      {/* Pipeline signalen */}
      {signals.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <h2 className="text-sm font-medium">Pipeline signalen ({signals.length})</h2>
          {signals.map((sig) => (
            <div key={sig.id} className="rounded-md bg-muted/50 px-3 py-2.5 space-y-0.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium">
                  {signalTypeLabel(sig.signal_type)}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  sig.signal_strength === "high"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-amber-100 text-amber-700"
                }`}>{sig.signal_strength}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {sig.source} · {new Date(sig.signal_time).toLocaleDateString("nl-NL")}
              </p>
              {sig.title && <p className="text-[11px] text-muted-foreground line-clamp-2">{sig.title}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
