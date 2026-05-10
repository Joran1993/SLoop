"use client";

import {
  X, Building2, Calendar, Ruler, Radio, User, ExternalLink,
  Phone, Globe, Search, Link2, Check, AlertTriangle, Clock, MapPin, Eye,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { leadQueryOptions, pipelineSignalsQueryOptions } from "@/lib/queries";
import { signalTypeLabel, eigenaarTypeLabel } from "@/lib/signal-labels";

interface LeadDetailPanelProps {
  leadId: string;
  onClose: () => void;
}

function grootte(m2: number | null | undefined) {
  if (!m2) return null;
  if (m2 < 500) return { label: "Klein", sub: `${m2.toLocaleString("nl-NL")} m²` };
  if (m2 < 2000) return { label: "Middel", sub: `${m2.toLocaleString("nl-NL")} m²` };
  return { label: "Groot", sub: `${m2.toLocaleString("nl-NL")} m²` };
}

function SignaalTiming({ sourceType, tenderWeeks, signals }: {
  sourceType?: string | null;
  tenderWeeks?: number | null;
  signals?: Array<{ signal_type: string }>;
}) {
  const hasVerleend = signals?.some(s =>
    s.signal_type === "verleende_sloopvergunning" || s.signal_type === "sloopvergunning_verleend"
  );
  const hasSloopmelding = signals?.some(s => s.signal_type === "sloopmelding");

  if (sourceType === "pijplijn") {
    const months = tenderWeeks ? Math.round(tenderWeeks / 4.33) : null;
    const hasAanvraag = signals?.some(s => s.signal_type === "aangevraagde_sloopvergunning");
    const tekst = hasAanvraag
      ? "Vergunning aangevraagd, nog niet verleend. Sloopbedrijf is waarschijnlijk nog niet geselecteerd — goed moment om contact te leggen."
      : "Vroeg planningsstadium — bestemmingsplan of vergelijkbare wijziging gedetecteerd. Zet dit pand in de gaten.";
    return (
      <div className="flex items-start gap-2 rounded-md bg-blue-50 border border-blue-200 px-3 py-2.5 dark:bg-blue-950/30 dark:border-blue-900">
        <Eye className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-xs font-semibold text-blue-800 dark:text-blue-300">
            Pijplijn{months ? ` — nog ±${months} maanden` : ""}
          </p>
          <p className="text-[11px] text-blue-700/80 dark:text-blue-500 mt-0.5">
            {tekst}
          </p>
        </div>
      </div>
    );
  }

  if (sourceType !== "eindhoven_vergunning") {
    let titel = "Laat signaal";
    let tekst = "De eigenaar belt waarschijnlijk al sloopbedrijven. Bel vandaag nog om te verifiëren.";
    if (hasSloopmelding) {
      tekst = "Sloopmelding ingediend — aannemer is hoogstwaarschijnlijk al geselecteerd.";
    } else if (hasVerleend) {
      tekst = "Vergunning verleend — eigenaar vraagt nu actief offertes op. Bel vandaag.";
    }
    return (
      <div className="flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2.5 dark:bg-amber-950/30 dark:border-amber-900">
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-xs font-semibold text-amber-800 dark:text-amber-300">{titel}</p>
          <p className="text-[11px] text-amber-700/80 dark:text-amber-500 mt-0.5">{tekst}</p>
        </div>
      </div>
    );
  }

  const weeks = tenderWeeks ?? 12;
  return (
    <div className="flex items-start gap-2 rounded-md bg-emerald-50 border border-emerald-200 px-3 py-2.5 dark:bg-emerald-950/30 dark:border-emerald-900">
      <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
      <div>
        <p className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
          Vroeg signaal — nog ±{weeks} weken
        </p>
        <p className="text-[11px] text-emerald-700/80 dark:text-emerald-500 mt-0.5">
          Aanvraag net gepubliceerd. Eigenaar belt nog geen sloopbedrijven — jij kunt de eerste zijn.
        </p>
      </div>
    </div>
  );
}

export function LeadDetailPanel({ leadId, onClose }: LeadDetailPanelProps) {
  const { data: lead, isLoading } = useQuery(leadQueryOptions(leadId));
  const { data: signals = [] } = useQuery(
    pipelineSignalsQueryOptions(lead?.bag_pand_id ?? null)
  );
  const [copied, setCopied] = useState(false);
  const [onderzoekTekst, setOnderzoekTekst] = useState<string | null>(null);
  const [onderzoekLoading, setOnderzoekLoading] = useState(false);

  async function startOnderzoek() {
    if (!lead || onderzoekLoading) return;
    setOnderzoekLoading(true);
    setOnderzoekTekst(null);
    try {
      const res = await fetch("/api/eigenaar-onderzoek", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          adres: lead.adres,
          gemeente: lead.gemeente,
          postcode: lead.postcode,
          bag_pand_id: lead.bag_pand_id,
        }),
      });
      const json = await res.json();
      setOnderzoekTekst(json.tekst ?? json.error ?? "Geen resultaat gevonden.");
    } catch {
      setOnderzoekTekst("Zoeken mislukt. Probeer het opnieuw.");
    } finally {
      setOnderzoekLoading(false);
    }
  }

  function copyLink() {
    navigator.clipboard.writeText(`${window.location.origin}/leads/${leadId}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const eigenaarNaam =
    signals.find((s) => s.eigenaar_naam)?.eigenaar_naam ??
    lead?.eigenaar_naam ??
    lead?.contact_naam ?? null;

  const [eigenaarZin, setEigenaarZin] = useState<string | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  async function fetchEigendomsinfo() {
    if (!lead?.bag_pand_id || lookupLoading) return;
    setLookupLoading(true);
    try {
      const res = await fetch(`/api/eigenaar-lookup?bag_pand_id=${encodeURIComponent(lead.bag_pand_id)}`);
      const json = await res.json();
      setEigenaarZin(json?.zin ?? "Geen eigendomsinformatie gevonden.");
    } catch {
      setEigenaarZin("Ophalen mislukt. Probeer het opnieuw.");
    } finally {
      setLookupLoading(false);
    }
  }

  const hasContactInfo = !!(lead?.contact_telefoon || lead?.contact_website || lead?.contact_email);
  const gr = grootte(lead?.oppervlakte_m2);

  return (
    <div className="flex h-full w-[340px] flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-semibold">Lead details</span>
        <div className="flex items-center gap-1">
          <button
            onClick={copyLink}
            title="Kopieer deelbare link"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Link2 className="h-4 w-4" />}
          </button>
          <button onClick={onClose} className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
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
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* Adres + grootte */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-base font-semibold leading-snug tracking-tight">{lead.adres ?? "Onbekend adres"}</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                {lead.gemeente}{lead.provincie ? ` · ${lead.provincie}` : ""}
              </p>
            </div>
            {gr && (
              <div className="text-right shrink-0">
                <div className="text-sm font-semibold">{gr.label}</div>
                <div className="text-xs text-muted-foreground">{gr.sub}</div>
              </div>
            )}
          </div>

          {/* Signaal timing */}
          <SignaalTiming
            sourceType={lead.source_type}
            tenderWeeks={lead.tender_window_estimate_weeks}
            signals={signals}
          />

          {/* Contact — primaire sectie */}
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-[11px] font-semibold text-muted-foreground">
              Eigenaar & Contact
            </p>

            <div className="flex items-start gap-2">
              <User className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div className="space-y-0.5 min-w-0">
                {eigenaarNaam ? (
                  <span className="text-sm font-medium block">{eigenaarNaam}</span>
                ) : (
                  <div className="space-y-1.5">
                    <span className="text-sm text-muted-foreground">Eigenaar onbekend</span>

                    {/* Eigendomsinformatie ophalen */}
                    {!eigenaarZin && lead?.bag_pand_id && (
                      <button
                        onClick={fetchEigendomsinfo}
                        disabled={lookupLoading}
                        className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted-foreground hover:border-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                      >
                        {lookupLoading ? (
                          <>
                            <span className="h-2.5 w-2.5 animate-spin rounded-full border border-current border-t-transparent" />
                            Ophalen…
                          </>
                        ) : (
                          <>
                            <Building2 className="h-2.5 w-2.5" />
                            Eigendomsinformatie ophalen
                          </>
                        )}
                      </button>
                    )}
                    {eigenaarZin && (
                      <span className="block text-[11px] text-muted-foreground leading-snug">
                        {eigenaarZin}
                      </span>
                    )}

                    {/* Dieper onderzoek */}
                    {!onderzoekTekst && (
                      <button
                        onClick={startOnderzoek}
                        disabled={onderzoekLoading}
                        className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted-foreground hover:border-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                      >
                        {onderzoekLoading ? (
                          <>
                            <span className="h-2.5 w-2.5 animate-spin rounded-full border border-current border-t-transparent" />
                            Aan het zoeken…
                          </>
                        ) : (
                          <>
                            <Search className="h-2.5 w-2.5" />
                            Eigenaar opzoeken
                          </>
                        )}
                      </button>
                    )}
                    {onderzoekTekst && (
                      <div className="rounded-md bg-muted/60 px-2.5 py-2 space-y-1">
                        {onderzoekTekst === "WOONHUIS" ? (
                          <p className="text-[11px] text-muted-foreground leading-snug">
                            Dit is een woonhuis — eigenaarsinformatie van particulieren is niet openbaar beschikbaar.
                          </p>
                        ) : (
                          <>
                            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Gevonden via web</p>
                            <p className="text-[11px] text-foreground leading-snug">{onderzoekTekst}</p>
                          </>
                        )}
                        <button
                          onClick={() => setOnderzoekTekst(null)}
                          className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                        >
                          Opnieuw zoeken
                        </button>
                      </div>
                    )}
                  </div>
                )}
                {lead.eigenaar_type && lead.eigenaar_type !== "onbekend" && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                    {eigenaarTypeLabel(lead.eigenaar_type)}
                  </span>
                )}
              </div>
            </div>

            {hasContactInfo && (
              <div className="rounded-lg bg-muted/50 px-3 py-2.5 space-y-2.5">
                {lead.contact_telefoon && (
                  <a
                    href={`tel:${lead.contact_telefoon.replace(/\s/g, "")}`}
                    className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-accent transition-colors"
                  >
                    <Phone className="h-4 w-4 shrink-0 text-accent" />
                    {lead.contact_telefoon}
                  </a>
                )}
                {lead.contact_website && (
                  <a
                    href={lead.contact_website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-accent hover:underline truncate"
                  >
                    <Globe className="h-4 w-4 shrink-0" />
                    {lead.contact_website.replace(/^https?:\/\//, "")}
                  </a>
                )}
                {lead.contact_email && (
                  <a
                    href={`mailto:${lead.contact_email}`}
                    className="flex items-center gap-2 text-sm text-accent hover:underline"
                  >
                    <ExternalLink className="h-4 w-4 shrink-0" />
                    {lead.contact_email}
                  </a>
                )}
              </div>
            )}

            {/* Eigenaar opzoeken */}
            <div className="space-y-1.5">
              {!hasContactInfo && (
                <p className="text-[10px] text-muted-foreground">Zelf eigenaar opzoeken:</p>
              )}
              {lead.bag_pand_id && (
                <button
                  onClick={() => navigator.clipboard.writeText(lead.bag_pand_id!)}
                  title="Kopieer pand-ID voor kadaster.nl"
                  className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Building2 className="h-3 w-3" />
                  <span className="font-mono">{lead.bag_pand_id}</span>
                </button>
              )}
              <div className="flex flex-wrap gap-1.5">
                {lead.adres && (
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(`eigenaar ${lead.adres} ${lead.gemeente}`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                  >
                    <Search className="h-2.5 w-2.5" />
                    Google
                  </a>
                )}
                {lead.longitude && lead.latitude && (
                  <a
                    href={`https://www.google.com/maps?q=${lead.latitude},${lead.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                  >
                    <MapPin className="h-2.5 w-2.5" />
                    Maps
                  </a>
                )}
                {lead.bag_pand_id && (
                  <a
                    href={`https://www.kadaster.nl/perceel-informatie?pandidentificatie=${lead.bag_pand_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                  >
                    <ExternalLink className="h-2.5 w-2.5" />
                    Kadaster
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Pand */}
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-[11px] font-semibold text-muted-foreground">Pand</p>
            <dl className="space-y-1.5">
              <Row icon={<Calendar className="h-3.5 w-3.5" />} label="Bouwjaar" value={lead.bouwjaar?.toString() ?? "—"} />
              <Row icon={<Ruler className="h-3.5 w-3.5" />} label="Oppervlakte" value={lead.oppervlakte_m2 != null ? `${lead.oppervlakte_m2.toLocaleString("nl-NL")} m²` : "—"} />
              <Row icon={<Building2 className="h-3.5 w-3.5" />} label="Gebruik" value={lead.gebruiksdoel?.join(", ") ?? "—"} />
            </dl>
          </div>

          {/* Publicatie */}
          <div className="space-y-1.5 border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold text-muted-foreground">Melding</p>
              {lead.source_type && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                  {lead.source_type === "eindhoven_vergunning" ? "Vergunning" :
                   lead.source_type === "pijplijn" ? "Pijplijn" : "Sloopmelding"}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {lead.publicatiedatum
                ? new Date(lead.publicatiedatum).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" })
                : "—"}
            </p>
            {lead.titel && <p className="text-xs text-muted-foreground line-clamp-3">{lead.titel}</p>}
            {lead.source_url && (
              <a href={lead.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-accent hover:underline">
                <ExternalLink className="h-3 w-3" />
                Originele publicatie
              </a>
            )}
          </div>

          {/* Pipeline signalen */}
          {signals.length > 0 && (
            <div className="space-y-2 border-t border-border pt-4">
              <div className="flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-accent" />
                <p className="text-[11px] font-semibold text-muted-foreground">
                  Vroege signalen ({signals.length})
                </p>
              </div>
              <div className="space-y-2">
                {signals.map((sig) => (
                  <div key={sig.id} className="rounded-md bg-muted/50 px-2.5 py-2 space-y-0.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium truncate">{signalTypeLabel(sig.signal_type)}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                        sig.signal_strength === "high"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                      }`}>
                        {sig.signal_strength === "high" ? "Sterk" : "Middel"}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      {sig.source} · {new Date(sig.signal_time).toLocaleDateString("nl-NL")}
                    </p>
                    {sig.title && <p className="text-[11px] text-muted-foreground line-clamp-2">{sig.title}</p>}
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

function Row({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="mt-0.5 text-muted-foreground shrink-0">{icon}</span>
      <span className="text-muted-foreground w-24 shrink-0">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
