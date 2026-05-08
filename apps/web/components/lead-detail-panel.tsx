"use client";

import { X, Building2, Calendar, Ruler, Zap, Radio, User, ExternalLink, Clock, Package, ShieldCheck, Link2, Check, Phone, Globe, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { leadQueryOptions, pipelineSignalsQueryOptions } from "@/lib/queries";
import { ScoreBadge } from "./score-badge";
import { signalTypeLabel, eigenaarTypeLabel } from "@/lib/signal-labels";
import type { SloopIndicatoren } from "@/lib/api";

interface LeadDetailPanelProps {
  leadId: string;
  onClose: () => void;
}

const scoreLabels = [
  { key: "score_asbest", label: "Asbestrisico", weight: "25%" },
  { key: "score_omvang", label: "Omvang pand", weight: "35%" },
  { key: "score_bereikbaarheid", label: "Bereikbaarheid", weight: "15%" },
  { key: "score_circulair", label: "Circulair potentieel", weight: "25%" },
] as const;

export function LeadDetailPanel({ leadId, onClose }: LeadDetailPanelProps) {
  const { data: lead, isLoading } = useQuery(leadQueryOptions(leadId));
  const { data: signals = [] } = useQuery(
    pipelineSignalsQueryOptions(lead?.bag_pand_id ?? null)
  );
  const [copied, setCopied] = useState(false);

  function copyLink() {
    const url = `${window.location.origin}/leads/${leadId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="flex h-full w-80 flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-medium">Lead details</span>
        <div className="flex items-center gap-1">
          <button
            onClick={copyLink}
            title="Kopieer deelbare link"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Link2 className="h-4 w-4" />}
          </button>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-sm text-muted-foreground">Laden…</span>
        </div>
      )}

      {lead && (
        <div className="flex-1 overflow-auto p-4 space-y-5">
          {/* Title */}
          <div>
            <h2 className="text-sm font-semibold leading-snug">
              {lead.adres ?? "Onbekend adres"}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {lead.gemeente}
              {lead.provincie ? ` · ${lead.provincie}` : ""}
            </p>
          </div>

          {/* Sloopvergunning verleend banner */}
          {lead.has_sloopvergunning && (
            <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2 dark:bg-red-950/30 dark:border-red-900">
              <ShieldCheck className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-red-700 dark:text-red-400">Sloopvergunning verleend</p>
                <p className="text-[11px] text-red-600/80 dark:text-red-500">BAG-status bevestigd — sloop aanstaande</p>
              </div>
            </div>
          )}

          {/* Score totaal */}
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold tabular-nums">
              {lead.score_totaal != null ? Math.round(lead.score_totaal) : "—"}
            </span>
            <div className="text-xs text-muted-foreground leading-tight">
              <div>Score</div>
              <div>/ 100</div>
            </div>
          </div>

          {/* Score breakdown */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Scorebreakdown
            </p>
            {scoreLabels.map(({ key, label, weight }) => {
              const val = lead[key] as number | null;
              const pct = val != null ? val : 0;
              return (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span>
                      {label}{" "}
                      <span className="text-muted-foreground">({weight})</span>
                    </span>
                    <ScoreBadge score={val} />
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pand details */}
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Pand
            </p>
            <dl className="space-y-1.5">
              <Row
                icon={<Calendar className="h-3.5 w-3.5" />}
                label="Bouwjaar"
                value={lead.bouwjaar?.toString() ?? "—"}
              />
              <Row
                icon={<Ruler className="h-3.5 w-3.5" />}
                label="Oppervlakte"
                value={
                  lead.oppervlakte_m2 != null
                    ? `${lead.oppervlakte_m2.toLocaleString("nl-NL")} m²`
                    : "—"
                }
              />
              <Row
                icon={<Zap className="h-3.5 w-3.5" />}
                label="Energielabel"
                value={lead.energielabel ?? "—"}
              />
              <Row
                icon={<Building2 className="h-3.5 w-3.5" />}
                label="Gebruiksdoel"
                value={lead.gebruiksdoel?.join(", ") ?? "—"}
              />
            </dl>
          </div>

          {/* Publicatie */}
          <div className="space-y-1.5 border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Melding
              </p>
              {lead.source_type && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                  {lead.source_type === "eindhoven_vergunning" ? "Vergunning" : "Sloopmelding"}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {lead.publicatiedatum
                ? new Date(lead.publicatiedatum).toLocaleDateString("nl-NL", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })
                : "—"}
            </p>
            {lead.titel && (
              <p className="text-xs text-muted-foreground line-clamp-3">
                {lead.titel}
              </p>
            )}
            {lead.tender_window_estimate_weeks != null && (
              <div className="flex items-center gap-1.5 text-xs mt-1">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-muted-foreground">Actievenster:</span>
                <span className="font-medium">±{lead.tender_window_estimate_weeks} weken</span>
              </div>
            )}
            {lead.source_url && (
              <a
                href={lead.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-accent hover:underline mt-1"
              >
                <ExternalLink className="h-3 w-3" />
                Originele publicatie bekijken
              </a>
            )}
          </div>

          {/* Eigenaar & Contact */}
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Eigenaar
            </p>

            {/* Naam */}
            {(() => {
              const naam =
                signals.find((s) => s.eigenaar_naam)?.eigenaar_naam ??
                lead.eigenaar_naam ??
                lead.contact_naam;
              const isProbabilistic = !signals.find((s) => s.eigenaar_naam) &&
                lead.eigenaar_naam &&
                lead.eigenaar_type &&
                ["corporatie_waarschijnlijk", "particulier_of_corporatie"].includes(lead.eigenaar_type);
              return (
                <div className="flex items-start gap-2 text-xs">
                  <User className="h-3.5 w-3.5 mt-0.5 text-muted-foreground shrink-0" />
                  <div className="space-y-0.5">
                    {naam ? (
                      <span className="font-medium block">{naam}</span>
                    ) : (
                      <span className="text-muted-foreground">Onbekend</span>
                    )}
                    {lead.eigenaar_type && lead.eigenaar_type !== "onbekend" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                        {eigenaarTypeLabel(lead.eigenaar_type)}
                      </span>
                    )}
                    {isProbabilistic && (
                      <p className="text-[10px] text-muted-foreground italic">Waarschijnlijke corporatie — gebaseerd op gemeente + bouwjaar</p>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Directe contactinfo (corporaties) */}
            {(lead.contact_telefoon || lead.contact_website || lead.contact_email) && (
              <div className="rounded-md bg-muted/40 px-2.5 py-2 space-y-1.5">
                {lead.contact_telefoon && (
                  <a
                    href={`tel:${lead.contact_telefoon.replace(/\s/g, "")}`}
                    className="flex items-center gap-2 text-xs hover:text-foreground text-muted-foreground"
                  >
                    <Phone className="h-3 w-3 shrink-0" />
                    {lead.contact_telefoon}
                  </a>
                )}
                {lead.contact_website && (
                  <a
                    href={lead.contact_website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-accent hover:underline truncate"
                  >
                    <Globe className="h-3 w-3 shrink-0" />
                    {lead.contact_website.replace(/^https?:\/\//, "")}
                  </a>
                )}
                {lead.contact_email && (
                  <a
                    href={`mailto:${lead.contact_email}`}
                    className="flex items-center gap-2 text-xs text-accent hover:underline"
                  >
                    <ExternalLink className="h-3 w-3 shrink-0" />
                    {lead.contact_email}
                  </a>
                )}
              </div>
            )}

            {/* Actielinks: eigenaar zelf opzoeken */}
            {lead.adres && (
              <div className="space-y-1.5">
                <p className="text-[10px] text-muted-foreground">Eigenaar opzoeken:</p>

                {/* Pand-ID kopieerbaar tonen voor gebruik op kadaster.nl */}
                {lead.bag_pand_id && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-muted-foreground">Pand-ID:</span>
                    <button
                      onClick={() => navigator.clipboard.writeText(lead.bag_pand_id!)}
                      title="Kopieer pand-ID — plak op kadaster.nl/perceel-informatie voor eigenaarsinformatie"
                      className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded hover:bg-muted/80 transition-colors"
                    >
                      {lead.bag_pand_id}
                    </button>
                  </div>
                )}

                <div className="flex flex-wrap gap-1.5">
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(`eigenaar ${lead.adres}`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                  >
                    <Search className="h-2.5 w-2.5" />
                    Google
                  </a>
                  {lead.longitude && lead.latitude && (
                    <a
                      href={`https://www.google.com/maps?q=${lead.latitude},${lead.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                    >
                      <ExternalLink className="h-2.5 w-2.5" />
                      Maps
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Sloopindicatoren */}
          {lead.materiaal_volume_estimate && (lead.materiaal_volume_estimate as SloopIndicatoren).totaal_ton > 0 && (
            <div className="space-y-2 border-t border-border pt-4">
              <div className="flex items-center gap-1.5">
                <Package className="h-3.5 w-3.5 text-muted-foreground" />
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Sloopindicatoren
                </p>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {(() => {
                  const ind = lead.materiaal_volume_estimate as SloopIndicatoren;
                  const items: { label: string; value: string; sub?: string }[] = [];

                  if (ind.totaal_ton) {
                    items.push({
                      label: "Sloopvolume",
                      value: `${ind.totaal_ton.toLocaleString("nl-NL")} ton`,
                    });
                  }
                  if (ind.residuwaarde_eur) {
                    items.push({
                      label: "Residuwaarde",
                      value: `€ ${ind.residuwaarde_eur.toLocaleString("nl-NL")}`,
                      sub: "schrootwaarde metaal",
                    });
                  }
                  if (ind.asbest_m2 != null) {
                    items.push({
                      label: "Asbestverdacht",
                      value: ind.asbest_m2 === 0 ? "Geen" : `${ind.asbest_m2.toLocaleString("nl-NL")} m²`,
                    });
                  }
                  if (ind.sloopkosten_min && ind.sloopkosten_max) {
                    items.push({
                      label: "Sloopkosten",
                      value: `€ ${(ind.sloopkosten_min / 1000).toFixed(0)}k – ${(ind.sloopkosten_max / 1000).toFixed(0)}k`,
                      sub: "excl. asbestsanering",
                    });
                  }

                  return items.map(({ label, value, sub }) => (
                    <div key={label} className="rounded bg-muted/50 px-2 py-1.5 text-xs">
                      <div className="text-muted-foreground">{label}</div>
                      <div className="font-medium tabular-nums">{value}</div>
                      {sub && <div className="text-[10px] text-muted-foreground/70 mt-0.5">{sub}</div>}
                    </div>
                  ));
                })()}
              </div>
            </div>
          )}

          {/* Pipeline signalen */}
          {signals.length > 0 && (
            <div className="space-y-2 border-t border-border pt-4">
              <div className="flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-accent" />
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Signalen ({signals.length})
                </p>
              </div>
              <div className="space-y-2">
                {signals.map((sig) => (
                  <div key={sig.id} className="rounded-md bg-muted/50 px-2.5 py-2 space-y-0.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium truncate">
                        {signalTypeLabel(sig.signal_type)}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                        sig.signal_strength === "high"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                      }`}>
                        {sig.signal_strength}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      {sig.source} · {new Date(sig.signal_time).toLocaleDateString("nl-NL")}
                    </p>
                    {sig.title && (
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {sig.title}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <span className="text-muted-foreground w-24 shrink-0">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
