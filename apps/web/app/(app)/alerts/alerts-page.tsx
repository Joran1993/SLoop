"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Bell, BellOff, ShieldCheck } from "lucide-react";
import { alertsQueryOptions } from "@/lib/queries";
import { createAlert, updateAlert, deleteAlert } from "@/lib/supabase-queries";
import type { AlertCreate } from "@/lib/api";

const PROVINCIES = [
  "Drenthe", "Flevoland", "Friesland", "Gelderland", "Groningen",
  "Limburg", "Noord-Brabant", "Noord-Holland", "Overijssel",
  "Utrecht", "Zeeland", "Zuid-Holland",
];

const GEBRUIKSDOELEN: { value: string; label: string }[] = [
  { value: "woonfunctie", label: "Wonen" },
  { value: "industriefunctie", label: "Industrie" },
  { value: "kantoorfunctie", label: "Kantoor" },
  { value: "winkelfunctie", label: "Retail" },
  { value: "onderwijsfunctie", label: "Onderwijs" },
  { value: "gezondheidszorgfunctie", label: "Zorg" },
  { value: "sportfunctie", label: "Sport" },
  { value: "logiesfunctie", label: "Horeca/Logies" },
];

export function AlertsPage() {
  const qc = useQueryClient();
  const { data: alerts = [], isLoading } = useQuery(alertsQueryOptions);
  const [showForm, setShowForm] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAlert(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      updateAlert(id, { active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="space-y-4">
      {/* Create button */}
      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nieuwe melding aanmaken
        </button>
      )}

      {/* Create form */}
      {showForm && (
        <AlertForm
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["alerts"] });
          }}
        />
      )}

      {/* Alert list */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">Laden…</p>
      )}
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="flex items-start gap-4 rounded-lg border border-border bg-card px-4 py-3"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{alert.name}</span>
                <span
                  className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${
                    alert.active
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {alert.active ? "Actief" : "Gepauzeerd"}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                {alert.filter.provincies?.length ? (
                  <span>{alert.filter.provincies.join(", ")}</span>
                ) : (
                  <span>Heel Nederland</span>
                )}
                {alert.filter.min_score != null && (
                  <span>Min. score: {alert.filter.min_score}</span>
                )}
                {alert.filter.min_oppervlakte != null && (
                  <span>Min. {alert.filter.min_oppervlakte} m²</span>
                )}
                {alert.filter.gebruiksdoelen?.length ? (
                  <span>{alert.filter.gebruiksdoelen.map((g) => GEBRUIKSDOELEN.find((x) => x.value === g)?.label ?? g).join(", ")}</span>
                ) : null}
                {alert.filter.only_with_vergunning && (
                  <span className="flex items-center gap-0.5 text-red-600 dark:text-red-400">
                    <ShieldCheck className="h-3 w-3" />
                    Vergunning
                  </span>
                )}
                <span className="capitalize">{alert.frequency}</span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() =>
                  toggleMutation.mutate({ id: alert.id, active: !alert.active })
                }
                className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                title={alert.active ? "Pauzeer" : "Activeer"}
              >
                {alert.active ? (
                  <BellOff className="h-4 w-4" />
                ) : (
                  <Bell className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={() => deleteMutation.mutate(alert.id)}
                className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                title="Verwijder"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
        {alerts.length === 0 && !isLoading && !showForm && (
          <p className="text-sm text-muted-foreground">
            Nog geen meldingen. Maak er een aan om op de hoogte te blijven.
          </p>
        )}
      </div>
    </div>
  );
}

function AlertForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [provincies, setProvincies] = useState<string[]>([]);
  const [minScore, setMinScore] = useState("");
  const [minOpp, setMinOpp] = useState("");
  const [onlyWithVergunning, setOnlyWithVergunning] = useState(false);
  const [gebruiksdoelen, setGebruiksdoelen] = useState<string[]>([]);
  const [frequency, setFrequency] = useState<"daily" | "weekly">("daily");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: AlertCreate) => createAlert(body),
    onSuccess: onCreated,
    onError: (e: Error) => setError(e.message),
  });

  function toggleProvincie(p: string) {
    setProvincies((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Geef de melding een naam.");
      return;
    }
    mutation.mutate({
      name: name.trim(),
      filter: {
        provincies: provincies.length ? provincies : undefined,
        min_score: minScore ? Number(minScore) : undefined,
        min_oppervlakte: minOpp ? Number(minOpp) : undefined,
        only_with_vergunning: onlyWithVergunning || undefined,
        gebruiksdoelen: gebruiksdoelen.length ? gebruiksdoelen : undefined,
      },
      frequency,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border bg-card p-4 space-y-4"
    >
      <p className="text-sm font-medium">Nieuwe melding</p>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">Naam</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="bijv. Grote panden Noord-Holland"
          className="flex h-8 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </div>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">
          Provincies (leeg = heel Nederland)
        </label>
        <div className="flex flex-wrap gap-1.5">
          {PROVINCIES.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => toggleProvincie(p)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                provincies.includes(p)
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">
          Type pand (leeg = alle types)
        </label>
        <div className="flex flex-wrap gap-1.5">
          {GEBRUIKSDOELEN.map((g) => (
            <button
              key={g.value}
              type="button"
              onClick={() =>
                setGebruiksdoelen((prev) =>
                  prev.includes(g.value)
                    ? prev.filter((x) => x !== g.value)
                    : [...prev, g.value]
                )
              }
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                gebruiksdoelen.includes(g.value)
                  ? "bg-foreground text-background"
                  : "border border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground">Min. score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="flex h-8 w-20 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground">Min. opp. (m²)</label>
          <input
            type="number"
            min={0}
            value={minOpp}
            onChange={(e) => setMinOpp(e.target.value)}
            className="flex h-8 w-24 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground">Frequentie</label>
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as "daily" | "weekly")}
            className="flex h-8 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="daily">Dagelijks</option>
            <option value="weekly">Wekelijks</option>
          </select>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setOnlyWithVergunning((v) => !v)}
        className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors ${
          onlyWithVergunning
            ? "border-red-400 bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400"
            : "border-border text-muted-foreground hover:text-foreground"
        }`}
      >
        <ShieldCheck className="h-3.5 w-3.5" />
        Alleen leads met sloopvergunning
      </button>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-md bg-primary px-4 h-8 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? "Opslaan…" : "Aanmaken"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-border px-4 h-8 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Annuleren
        </button>
      </div>
    </form>
  );
}
